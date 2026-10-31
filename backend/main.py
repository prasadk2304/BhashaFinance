from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import uuid
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config import settings
from backend.customers import get_mock_transactions, MOCK_CUSTOMERS
from backend.database import (
    get_tickets_for_session,
    init_db,
    load_state,
    save_state,
    save_ticket,
)
from backend.planner import (
    initialize_journey,
    plan_next_step,
    submit_journey_application,
    PlannerStepResult,
)
from backend.llm import llm_service
from backend.rag import rag_service
from backend.rules.emi import calculate_emi, EmiCalculationResult
from backend.rules.foir import calculate_foir, FoirCalculationResult
from backend.rules.parser import parse_amount, extract_all_amounts
from backend.rules.product_specs import PRODUCT_SPECS, get_product_spec
from backend.rules.sip import calculate_sip, SipCalculationResult
from backend.sarvam import sarvam_service, SttResponse, TtsResponse
from backend.state import JourneyState, JourneyStatus, MessageEntry


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite and load RAG embeddings
    init_db()
    try:
        await rag_service.load_and_index()
    except Exception as e:
        print(f"Warning: RAG indexing encountered non-fatal error: {e}")
    yield


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
        "rag_chunks_indexed": len(rag_service.chunks),
        "sample_mode": True,
    }


@app.get("/api/products")
def list_products():
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
# Sessions & Conversation Turns (Main Journey Flow)
# ==============================================================================

class CreateSessionRequest(BaseModel):
    journey_id: str
    customer_id: Optional[str] = "CUST-1001"
    session_id: Optional[str] = None


class TurnResponse(BaseModel):
    session_id: str
    journey_id: str
    reply_text: str
    state: Dict[str, Any]
    next_action: str
    target_field: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    calculation: Optional[Dict[str, Any]] = None
    citations: List[str] = Field(default_factory=list)
    audio_base64: Optional[str] = None


@app.post("/sessions", response_model=TurnResponse)
def create_session(req: CreateSessionRequest):
    """
    Creates a new journey session and returns the initial turn prompt.
    Persists state to SQLite immediately.
    """
    spec = get_product_spec(req.journey_id)
    if not spec:
        raise HTTPException(status_code=400, detail=f"Invalid journey_id: {req.journey_id}")

    session_id = req.session_id or f"sess_{uuid.uuid4().hex[:12]}"
    state = initialize_journey(session_id=session_id, journey_id=req.journey_id)

    # Initial planner step asks for the first missing required field
    step_result = plan_next_step(state=state, user_input=None, spec=spec)
    save_state(step_result.state)

    calc_dump = step_result.calculation.model_dump() if step_result.calculation else None
    return TurnResponse(
        session_id=session_id,
        journey_id=req.journey_id,
        reply_text=step_result.prompt_message,
        state=step_result.state.model_dump(),
        next_action=step_result.next_action,
        target_field=step_result.target_field,
        results=calc_dump,
        calculation=calc_dump,
        citations=[],
    )


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Retrieves current session state and audit history."""
    state = load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found.")
    tickets = get_tickets_for_session(session_id)
    return {
        "state": state.model_dump(),
        "tickets": tickets,
    }


@app.post("/sessions/{session_id}/turns", response_model=TurnResponse)
async def handle_session_turn(
    session_id: str,
    request: Request,
    text: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None),
    language_code: Optional[str] = Form("unknown"),
    synthesize_speech: bool = Form(False),
):
    """
    Accepts text or audio (voice). Persists state after every turn.
    Returns: reply_text, state, next_action, results, citations[].
    Grounds payment_help and loan_rejection in retrieved chunks + mock data.
    """
    state = load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Check if request was sent as JSON
    content_type = request.headers.get("content-type", "")
    user_utterance = ""

    if "application/json" in content_type:
        body = await request.json()
        user_utterance = body.get("text", "").strip()
        synthesize_speech = body.get("synthesize_speech", False)
    else:
        # Multipart form data
        if audio is not None:
            audio_bytes = await audio.read()
            stt_res = await sarvam_service.speech_to_text(
                audio_bytes=audio_bytes,
                filename=audio.filename or "audio.wav",
                language_code=language_code or "unknown",
            )
            user_utterance = stt_res.transcript.strip()
            if not user_utterance and stt_res.error:
                # If STT failed or wasn't configured, fall back to text if provided
                user_utterance = (text or "").strip()
        elif text:
            user_utterance = text.strip()

    spec = get_product_spec(state.journey_id)
    if not spec:
        raise HTTPException(status_code=400, detail=f"Product spec missing for {state.journey_id}")

    # RAG Grounding for payment_help and loan_rejection
    citations: List[str] = []
    rag_context_text = ""

    if state.journey_id in ("payment_help", "loan_rejection"):
        rag_query = user_utterance if user_utterance else spec.title
        rag_results = await rag_service.search(query=rag_query, top_k=3, category=state.journey_id)
        citations = [r.chunk.id for r in rag_results]
        if rag_results:
            rag_context_text = "\n\nPolicy Grounding (" + ", ".join(citations) + "):\n"
            for r in rag_results:
                rag_context_text += f"- [{r.chunk.id}] {r.chunk.heading}: {r.chunk.content[:160]}...\n"

    # Field extraction with LLM Service (Sarvam -> Ollama -> Regex fallback)
    extracted_fields_meta = None
    missing_fields = state.get_missing_required_fields(spec.required_fields)
    if user_utterance and missing_fields and state.status == JourneyStatus.COLLECTING:
        target_name = missing_fields[0]
        f_def = spec.field_definitions.get(target_name)
        schema = {target_name: f_def.data_type if f_def else "str"}
        try:
            ext_res = await llm_service.extract_with_fallback(
                transcript=user_utterance,
                schema=schema,
                language=language_code or "en",
            )
            extracted_fields_meta = ext_res.field_metadata
        except Exception:
            extracted_fields_meta = None

    # Step the deterministic planner
    step_result = plan_next_step(
        state=state,
        user_input=user_utterance if user_utterance else None,
        spec=spec,
        extracted_fields=extracted_fields_meta,
    )

    reply = step_result.prompt_message
    if rag_context_text and step_result.next_action in ("request_consent", "submitted"):
        reply += f"\n{rag_context_text}"

    # Persist state after EVERY turn!
    save_state(step_result.state)

    # Optional TTS synthesis
    audio_base64 = None
    if synthesize_speech and reply:
        tts_res = await sarvam_service.text_to_speech(text=reply)
        audio_base64 = tts_res.audio_base64

    calc_dump = step_result.calculation.model_dump() if step_result.calculation else None
    return TurnResponse(
        session_id=session_id,
        journey_id=step_result.state.journey_id,
        reply_text=reply,
        state=step_result.state.model_dump(),
        next_action=step_result.next_action,
        target_field=step_result.target_field,
        results=calc_dump,
        calculation=calc_dump,
        citations=citations,
        audio_base64=audio_base64,
    )


class ConfirmRequest(BaseModel):
    consent_granted: bool
    consent_text: Optional[str] = "Explicit consent confirmed by user"
    method: str = "button_click"


@app.post("/sessions/{session_id}/confirm")
def confirm_session(session_id: str, req: ConfirmRequest):
    """
    Submits explicit consent. No submission without explicit consent!
    Persists state after confirmation.
    """
    state = load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found.")

    if req.consent_granted:
        state.consent.grant(text=req.consent_text or "User confirmed consent", method=req.method)
        state.status = JourneyStatus.SUBMITTED
    else:
        state.consent.revoke()
        state.status = JourneyStatus.COLLECTING

    save_state(state)
    return {
        "session_id": session_id,
        "status": state.status.value,
        "consent": state.consent.model_dump(),
        "is_sample": True,
        "reference_id": f"SAMPLE-PAYTM-{abs(hash(session_id)) % 1000000:06d}",
    }


class CreateTicketRequest(BaseModel):
    category: str = "payment_support"
    issue_description: str
    resolution_plan: Optional[str] = None


@app.post("/sessions/{session_id}/tickets")
def create_ticket(session_id: str, req: CreateTicketRequest):
    """
    Creates and records a support ticket for loan dispute, auto-debit bounce, or restructuring.
    """
    state = load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found.")

    ticket_id = f"TCK-{uuid.uuid4().hex[:8].upper()}"
    ticket = {
        "ticket_id": ticket_id,
        "session_id": session_id,
        "category": req.category,
        "issue_description": req.issue_description,
        "resolution_plan": req.resolution_plan or "Pending agent review / automated 48-hour waiver applied",
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sample_label": "Sample",
    }
    save_ticket(ticket)
    return ticket


@app.get("/customers/{customer_id}/transactions")
def get_customer_transactions(customer_id: str):
    """Returns mock transactions for customer."""
    txns = get_mock_transactions(customer_id)
    customer_info = MOCK_CUSTOMERS.get(customer_id, {
        "customer_id": customer_id,
        "name": "Valued Customer",
        "sample_label": "Sample",
    })
    return {
        "customer": customer_info,
        "transactions": [t.model_dump() for t in txns],
        "sample_label": "Sample",
    }


# ==============================================================================
# Legacy API Compatibility Endpoints
# ==============================================================================

class StartJourneyRequest(BaseModel):
    session_id: str
    journey_id: str


@app.post("/api/journey/start")
def start_journey(req: StartJourneyRequest):
    return create_session(CreateSessionRequest(journey_id=req.journey_id, session_id=req.session_id))


class MessageRequest(BaseModel):
    session_id: str
    text: str


@app.post("/api/journey/message")
async def handle_message(req: MessageRequest, request: Request):
    return await handle_session_turn(session_id=req.session_id, request=request, text=req.text)


@app.post("/api/journey/submit")
def submit_journey(session_id: str):
    state = load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found.")
    try:
        res = submit_journey_application(state)
        save_state(state)
        return res
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


# ==============================================================================
# Deterministic Rules Direct Testing Endpoints
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
