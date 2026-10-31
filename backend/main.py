import base64
import logging
import os
from pathlib import Path
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import uuid
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from backend.audio import convert_to_16k_mono_wav, verify_ffmpeg_on_startup
from backend.config import settings, SUPPORTED_LANGUAGES
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
from backend.rules.plain_definitions import add_inline_definitions
from backend.rules.product_specs import PRODUCT_SPECS, get_product_spec
from backend.rules.sip import calculate_sip, SipCalculationResult
from backend.rules.spoken_numbers import convert_amounts_in_text
from backend.sarvam import sarvam_service, SarvamUnavailable, CACHE_DIR
from backend.state import JourneyState, JourneyStatus, MessageEntry


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite, verify ffmpeg, and load RAG embeddings
    init_db()
    verify_ffmpeg_on_startup()
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
    target_field_why: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    calculation: Optional[Dict[str, Any]] = None
    citations: List[str] = Field(default_factory=list)
    audio_base64: Optional[str] = None
    reply_audio_url: Optional[str] = None
    transcript: Optional[str] = None


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

    reply = add_inline_definitions(step_result.prompt_message)
    reply_audio_url = None
    try:
        spoken = convert_amounts_in_text(reply, language_code=settings.default_language)
        mp3 = sarvam_service.tts(text=spoken, lang=settings.default_language)
        reply_audio_url = f"/api/voice/audio/{mp3.name}"
    except Exception:
        reply_audio_url = None

    calc_dump = step_result.calculation.model_dump() if step_result.calculation else None
    return TurnResponse(
        session_id=session_id,
        journey_id=req.journey_id,
        reply_text=reply,
        state=step_result.state.model_dump(),
        next_action=step_result.next_action,
        target_field=step_result.target_field,
        target_field_why=step_result.target_field_why,
        results=calc_dump,
        calculation=calc_dump,
        citations=[],
        reply_audio_url=reply_audio_url,
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


def validate_language_code(code: Optional[str]) -> str:
    """
    Validates that language code is supported.
    Accepts BCP-47 codes (mr-IN, hi-IN, en-IN) or short codes (mr, hi, en).
    Rejects other codes with 400.
    """
    if not code or code in ("unknown", ""):
        return settings.default_language
    code = code.strip()
    if code in SUPPORTED_LANGUAGES:
        return code
    # Allow short codes (mr -> mr-IN)
    for bcp in SUPPORTED_LANGUAGES:
        if bcp.lower().startswith(f"{code.lower()}-") or bcp.lower() == code.lower():
            return bcp
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported language code '{code}'. Supported: {list(SUPPORTED_LANGUAGES.keys())}",
    )


# ==============================================================================
# Voice & Language Endpoints (Sarvam SDK Integration)
# ==============================================================================

@app.get("/api/languages")
def get_supported_languages():
    """Returns supported languages configuration map."""
    return SUPPORTED_LANGUAGES


@app.post("/api/voice/stt")
async def voice_stt(
    audio: UploadFile = File(...),
    language_code: Optional[str] = Form(None),
):
    """
    Transcribes uploaded audio (webm/ogg/mp4/wav) using Sarvam STT.
    Converts to 16 kHz mono WAV, checks 10 MB limit and 30s max duration.
    On failure, returns 503 with {fallback: "text"}.
    """
    target_lang = validate_language_code(language_code)

    content = await audio.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio file exceeds 10 MB limit.")

    suffix = Path(audio.filename or "upload.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_in:
        tmp_in.write(content)
        tmp_in_path = Path(tmp_in.name)

    converted_wav = None
    try:
        converted_wav = convert_to_16k_mono_wav(tmp_in_path)
        transcript = sarvam_service.stt(path=converted_wav, lang=target_lang)
        return {"transcript": transcript, "language_code": target_lang}
    except (SarvamUnavailable, Exception) as err:
        logger.warning("Voice STT endpoint failed: %s", type(err).__name__)
        return JSONResponse(
            status_code=503,
            content={"fallback": "text", "detail": f"STT failed: {str(err)}"},
        )
    finally:
        try:
            if tmp_in_path.exists():
                tmp_in_path.unlink()
            if converted_wav and converted_wav.exists() and converted_wav != tmp_in_path:
                converted_wav.unlink()
        except Exception:
            pass


class TtsRequest(BaseModel):
    text: str
    language_code: Optional[str] = None


@app.post("/api/voice/tts")
def voice_tts(req: TtsRequest):
    """
    Synthesizes speech using Sarvam TTS.
    Converts numeric amounts to spoken words before synthesis.
    Returns audio/mpeg FileResponse.
    """
    target_lang = validate_language_code(req.language_code)

    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    spoken_text = convert_amounts_in_text(req.text, language_code=target_lang)
    try:
        mp3_path = sarvam_service.tts(text=spoken_text, lang=target_lang)
        return FileResponse(
            path=str(mp3_path),
            media_type="audio/mpeg",
            filename=mp3_path.name,
        )
    except (SarvamUnavailable, Exception) as err:
        logger.warning("Voice TTS endpoint failed: %s", type(err).__name__)
        raise HTTPException(status_code=503, detail=f"TTS service unavailable: {str(err)}")


@app.get("/api/voice/audio/{filename}")
def get_cached_audio_file(filename: str):
    """Serves cached MP3 audio file."""
    safe_name = Path(filename).name
    file_path = CACHE_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return FileResponse(path=str(file_path), media_type="audio/mpeg")


@app.post("/sessions/{session_id}/turns", response_model=TurnResponse)
async def handle_session_turn(
    session_id: str,
    request: Request,
    text: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None),
    language_code: Optional[str] = Form(None),
    synthesize_speech: bool = Form(False),
):
    """
    Accepts text or audio (voice). Persists state after every turn.
    Returns: reply_text, state, next_action, results, citations[], reply_audio_url, transcript.
    Grounds payment_help and loan_rejection in retrieved chunks + mock data.
    Graceful degradation:
      - If Sarvam STT fails, return 503 with {fallback: "text"}.
      - If TTS fails, return reply_text without audio.
      - No exception may crash a turn.
    """
    state = load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found.")

    target_lang = settings.default_language
    user_utterance = ""
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        body = await request.json()
        user_utterance = (body.get("text") or "").strip()
        synthesize_speech = body.get("synthesize_speech", False)
        req_lang = body.get("language_code")
        if req_lang:
            target_lang = validate_language_code(req_lang)
    else:
        # Multipart form data
        if language_code:
            target_lang = validate_language_code(language_code)

        if audio is not None:
            audio_bytes = await audio.read()
            if len(audio_bytes) > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Audio file exceeds 10 MB limit.")

            suffix = Path(audio.filename or "upload.wav").suffix or ".wav"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_in:
                tmp_in.write(audio_bytes)
                tmp_in_path = Path(tmp_in.name)

            converted_wav = None
            try:
                converted_wav = convert_to_16k_mono_wav(tmp_in_path)
                user_utterance = sarvam_service.stt(path=converted_wav, lang=target_lang).strip()
            except (SarvamUnavailable, Exception) as err:
                logger.warning("Sarvam STT failed during turn: %s", type(err).__name__)
                # Graceful degradation: return 503 with {fallback: "text"}
                return JSONResponse(
                    status_code=503,
                    content={"fallback": "text", "detail": f"STT failed: {str(err)}"},
                )
            finally:
                try:
                    if tmp_in_path.exists():
                        tmp_in_path.unlink()
                    if converted_wav and converted_wav.exists() and converted_wav != tmp_in_path:
                        converted_wav.unlink()
                except Exception:
                    pass
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

    # Field extraction: run existing regex parser first -> then LLM extractor -> planner
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
                language=target_lang,
            )
            extracted_fields_meta = ext_res.field_metadata
        except Exception as e:
            logger.warning("Extraction encountered non-fatal error: %s", type(e).__name__)
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

    # Plain-language inline definitions on first mention
    reply = add_inline_definitions(reply)

    # Persist state after EVERY turn!
    save_state(step_result.state)

    # TTS synthesis with graceful degradation (never crash a turn)
    reply_audio_url = None
    audio_base64 = None

    try:
        spoken_reply = convert_amounts_in_text(reply, language_code=target_lang)
        mp3_path = sarvam_service.tts(text=spoken_reply, lang=target_lang)
        reply_audio_url = f"/api/voice/audio/{mp3_path.name}"
        if synthesize_speech and mp3_path.exists():
            audio_base64 = base64.b64encode(mp3_path.read_bytes()).decode("ascii")
    except Exception as e:
        logger.warning("Turn TTS synthesis degraded gracefully: %s", type(e).__name__)
        reply_audio_url = None

    calc_dump = step_result.calculation.model_dump() if step_result.calculation else None
    return TurnResponse(
        session_id=session_id,
        journey_id=step_result.state.journey_id,
        reply_text=reply,
        state=step_result.state.model_dump(),
        next_action=step_result.next_action,
        target_field=step_result.target_field,
        target_field_why=step_result.target_field_why,
        results=calc_dump,
        calculation=calc_dump,
        citations=citations,
        audio_base64=audio_base64,
        reply_audio_url=reply_audio_url,
        transcript=user_utterance if user_utterance else None,
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


class AgentHandoffResponse(BaseModel):
    handoff_id: str
    session_id: str
    journey_id: str
    journey_title: str
    summary_paragraph: str
    journey_state: Dict[str, Any]
    status: str = "connected"
    estimated_wait_seconds: int = 30


@app.post("/sessions/{session_id}/agent_handoff", response_model=AgentHandoffResponse)
def handoff_to_agent(session_id: str):
    """
    Hands off the customer session to a live human agent.
    Provides full journey state and a 1-paragraph summary so the customer NEVER repeats themselves.
    """
    state = load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found.")

    spec = get_product_spec(state.journey_id)
    title = spec.title if spec else state.journey_id.replace("_", " ").title()

    field_summaries = []
    for fname, f in state.fields.items():
        if f.value is not None:
            unit = f.unit or ""
            field_summaries.append(f"{f.label or fname}: {f.value}{unit} [{f.status.value}]")

    fields_text = ", ".join(field_summaries) if field_summaries else "No inputs gathered yet"

    all_user_msgs = " ".join([m.text for m in state.messages if m.sender == "user"]).lower()
    is_urgent = any(kw in all_user_msgs for kw in ["emergency", "hospital", "medical", "urgent", "stuck", "rejected", "declined"])
    urgency_tag = "Urgent" if is_urgent else "Standard"

    calc_str = ""
    if state.calculation and state.calculation.metrics:
        m = state.calculation.metrics
        if "monthly_emi" in m:
            calc_str = f" Computed Sample EMI is ₹{m.get('monthly_emi_rounded', m.get('monthly_emi', 0)):,}."
        elif "late_fee_waiver" in m:
            calc_str = f" Late fee waiver of ₹{m.get('late_fee_waiver', 0):.0f} was applied."

    summary = (
        f"Customer session {session_id} on {title} [{urgency_tag} priority]. "
        f"Current status is '{state.status.value}'. Captured fields: {fields_text}.{calc_str} "
        f"Pending action: '{state.status.value}'. "
        "All verified information is transferred; specialist can assist immediately without requesting re-explanation."
    )

    handoff_id = f"AGT-{abs(hash(session_id)) % 1000000:06d}"
    return AgentHandoffResponse(
        handoff_id=handoff_id,
        session_id=session_id,
        journey_id=state.journey_id,
        journey_title=title,
        summary_paragraph=summary,
        journey_state=state.model_dump(),
        status="connected",
        estimated_wait_seconds=30,
    )


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
