from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import settings
from backend.database import init_db, load_state, save_state
from backend.planner import (
    initialize_journey,
    plan_next_step,
    submit_journey_application,
    PlannerStepResult,
)
from backend.rules.emi import calculate_emi, EmiCalculationResult
from backend.rules.foir import calculate_foir, FoirCalculationResult
from backend.rules.parser import parse_amount, extract_all_amounts
from backend.rules.product_specs import PRODUCT_SPECS, get_product_spec
from backend.rules.sip import calculate_sip, SipCalculationResult
from backend.sarvam import sarvam_service, SttResponse, TtsResponse
from backend.state import JourneyState, JourneyStatus


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite
    init_db()
    yield
    # Shutdown


app = FastAPI(
    title="BhashaFinance AI",
    description="Voice-first multilingual journey assistant for Paytm lending and fintech.",
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Health and Info
# ==============================================================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version,
        "llm_model": settings.llm_model,
        "sarvam_configured": sarvam_service.is_configured,
        "sample_mode": True,
    }


@app.get("/api/products")
def list_products():
    """Returns catalog of all supported ProductSpec journeys."""
    return [
        {
            "journey_id": spec.journey_id,
            "title": spec.title,
            "description": spec.description,
            "category": spec.category,
            "required_fields": spec.required_fields,
            "sample_label": spec.sample_label,
            "disclosures": spec.disclosures,
        }
        for spec in PRODUCT_SPECS.values()
    ]


# ==============================================================================
# Journey Management & Generic Planner Endpoints
# ==============================================================================

class StartJourneyRequest(BaseModel):
    session_id: str
    journey_id: str


class MessageRequest(BaseModel):
    session_id: str
    text: str


class ConsentRequest(BaseModel):
    session_id: str
    consent_granted: bool
    consent_text: Optional[str] = None
    method: str = "user_input"


@app.post("/api/journey/start")
def start_journey(req: StartJourneyRequest):
    spec = get_product_spec(req.journey_id)
    if not spec:
        raise HTTPException(status_code=400, detail=f"Invalid journey_id: {req.journey_id}")

    state = initialize_journey(session_id=req.session_id, journey_id=req.journey_id)
    # Plan first step (which will ask for the first missing required field)
    step_result = plan_next_step(state=state, user_input=None, spec=spec)
    save_state(step_result.state)

    return {
        "session_id": req.session_id,
        "journey_id": req.journey_id,
        "status": step_result.state.status.value,
        "next_action": step_result.next_action,
        "target_field": step_result.target_field,
        "prompt_message": step_result.prompt_message,
        "state": step_result.state.model_dump(),
    }


@app.post("/api/journey/message")
def handle_message(req: MessageRequest):
    state = load_state(req.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found. Please start a journey first.")

    step_result = plan_next_step(state=state, user_input=req.text)
    save_state(step_result.state)

    return {
        "session_id": req.session_id,
        "journey_id": step_result.state.journey_id,
        "status": step_result.state.status.value,
        "next_action": step_result.next_action,
        "target_field": step_result.target_field,
        "prompt_message": step_result.prompt_message,
        "calculation": step_result.calculation.model_dump() if step_result.calculation else None,
        "state": step_result.state.model_dump(),
    }


@app.post("/api/journey/consent")
def handle_consent(req: ConsentRequest):
    state = load_state(req.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found.")

    if req.consent_granted:
        state.consent.grant(
            text=req.consent_text or "Explicit consent granted by user",
            method=req.method,
        )
        state.status = JourneyStatus.SUBMITTED
    else:
        state.consent.revoke()
        state.status = JourneyStatus.COLLECTING

    save_state(state)
    return {
        "session_id": state.session_id,
        "status": state.status.value,
        "consent": state.consent.model_dump(),
    }


@app.post("/api/journey/submit")
def submit_journey(session_id: str):
    state = load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found.")

    try:
        result = submit_journey_application(state)
        save_state(state)
        return result
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe),
        )


@app.get("/api/journey/state/{session_id}")
def get_state(session_id: str):
    state = load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found.")
    return state.model_dump()


# ==============================================================================
# Speech Endpoints (Backend Proxy - Keys Never Exposed to Frontend)
# ==============================================================================

@app.post("/api/voice/stt", response_model=SttResponse)
async def voice_stt(
    file: UploadFile = File(...),
    language_code: str = Form("unknown"),
):
    """
    Accepts speech audio from frontend, calls Sarvam STT server-side,
    returns text transcript.
    """
    audio_bytes = await file.read()
    return await sarvam_service.speech_to_text(
        audio_bytes=audio_bytes,
        filename=file.filename or "speech.wav",
        language_code=language_code,
    )


class TtsRequest(BaseModel):
    text: str
    target_language_code: str = "hi-IN"
    speaker: str = "meera"


@app.post("/api/voice/tts", response_model=TtsResponse)
async def voice_tts(req: TtsRequest):
    """
    Accepts text, calls Sarvam TTS server-side, returns base64 audio.
    """
    return await sarvam_service.text_to_speech(
        text=req.text,
        target_language_code=req.target_language_code,
        speaker=req.speaker,
    )


# ==============================================================================
# Deterministic Rules Endpoints (Direct Verifiers)
# ==============================================================================

class EmiRequest(BaseModel):
    principal: float
    annual_interest_rate: float
    tenure_months: int
    generate_schedule: bool = False


@app.post("/api/rules/emi", response_model=EmiCalculationResult)
def calculate_emi_endpoint(req: EmiRequest):
    return calculate_emi(
        principal=req.principal,
        annual_interest_rate=req.annual_interest_rate,
        tenure_months=req.tenure_months,
        generate_schedule=req.generate_schedule,
    )


class SipRequest(BaseModel):
    monthly_investment: float
    expected_annual_return: float
    duration_years: float
    generate_yearly_breakdown: bool = False


@app.post("/api/rules/sip", response_model=SipCalculationResult)
def calculate_sip_endpoint(req: SipRequest):
    return calculate_sip(
        monthly_investment=req.monthly_investment,
        expected_annual_return=req.expected_annual_return,
        duration_years=req.duration_years,
        generate_yearly_breakdown=req.generate_yearly_breakdown,
    )


class FoirRequest(BaseModel):
    monthly_income: float
    existing_obligations: float = 0.0
    proposed_emi: float = 0.0
    max_foir_threshold_pct: float = 50.0
    annual_interest_rate: Optional[float] = None
    tenure_months: Optional[int] = None


@app.post("/api/rules/foir", response_model=FoirCalculationResult)
def calculate_foir_endpoint(req: FoirRequest):
    return calculate_foir(
        monthly_income=req.monthly_income,
        existing_obligations=req.existing_obligations,
        proposed_emi=req.proposed_emi,
        max_foir_threshold_pct=req.max_foir_threshold_pct,
        annual_interest_rate=req.annual_interest_rate,
        tenure_months=req.tenure_months,
    )


class ParseRequest(BaseModel):
    text: str


@app.post("/api/rules/parse")
def parse_text_endpoint(req: ParseRequest):
    return {
        "text": req.text,
        "single_amount": parse_amount(req.text),
        "all_amounts": extract_all_amounts(req.text),
    }
