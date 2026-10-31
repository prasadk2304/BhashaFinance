import backend.database as database
import httpx
import pytest
from backend.main import app
from backend.planner import initialize_journey, plan_next_step
from backend.rules.product_specs import get_product_spec
from backend.state import JourneyStatus


def complete_required_fields(state, values):
    spec = get_product_spec(state.journey_id)
    step = None
    for value in values:
        step = plan_next_step(state, value, spec=spec)
    return step


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_personal_loan_consent_moves_to_document_review_with_masked_checklist():
    state = initialize_journey("document-review-personal", "personal_loan")
    complete_required_fields(state, ["80000", "150000", "24 months", "zero"])

    step = plan_next_step(state, "I agree", spec=get_product_spec("personal_loan"))

    assert step.next_action == "document_review"
    assert state.status == JourneyStatus.DOCUMENT_REVIEW
    assert {item.key for item in state.document_checklist} >= {"pan", "dob", "bank_statement_6_months"}
    assert all(item.status == "needed" for item in state.document_checklist)
    assert "human review" in step.prompt_message.lower()


def test_sip_has_kyc_and_mandate_checklist_but_payment_help_has_no_kyc_documents():
    sip = initialize_journey("document-review-sip", "sip")
    complete_required_fields(sip, ["5000", "5 years"])
    sip_step = plan_next_step(sip, "I agree", spec=get_product_spec("sip"))

    assert sip_step.next_action == "document_review"
    assert {item.key for item in sip.document_checklist} == {"pan", "kyc_status", "bank_mandate"}

    payment = initialize_journey("document-review-payment", "payment_help")
    complete_required_fields(payment, ["PAYTM-LN-8812", "auto debit bounce", "4500"])
    payment_step = plan_next_step(payment, "I agree", spec=get_product_spec("payment_help"))

    assert payment_step.next_action == "submitted"
    assert payment.document_checklist == []


def test_review_case_requires_explicit_handoff_consent_and_stores_masked_packet_only(tmp_path, monkeypatch):
    monkeypatch.setattr(database.settings, "db_path", str(tmp_path / "review.db"))
    database._db_initialized = False

    state = initialize_journey("document-review-handoff", "personal_loan")
    complete_required_fields(state, ["80000", "150000", "24 months", "zero"])
    plan_next_step(state, "I agree", spec=get_product_spec("personal_loan"))

    assert state.review_consent.granted is False
    for _ in state.document_checklist:
        plan_next_step(state, "yes", spec=get_product_spec("personal_loan"))
    assert state.status == JourneyStatus.AWAITING_REVIEW_CONSENT

    step = plan_next_step(state, "I agree", spec=get_product_spec("personal_loan"))
    assert step.next_action == "review_submitted"
    assert state.review_consent.granted is True

    state.masked_previews = {"pan": "ABCDE****F"}
    state.messages.append(type(state.messages[0])(sender="user", text="PAN [PAN_REDACTED]"))
    case = database.create_review_case(state)
    assert case["status"] == "pending"
    assert "ABCDE1234F" not in str(case["packet"])
    assert case["packet"]["masked_previews"] == {"pan": "ABCDE****F"}
    assert case["readiness"]["outcome"] in {"Ready for human review", "Affordability needs human review"}


def test_reviewer_material_request_becomes_customer_action(tmp_path, monkeypatch):
    monkeypatch.setattr(database.settings, "db_path", str(tmp_path / "review-request.db"))
    database._db_initialized = False
    state = initialize_journey("document-review-request", "personal_loan")
    state.document_checklist = []
    state.review_consent.grant("I agree", "voice")
    state.status = JourneyStatus.SUBMITTED

    case = database.create_review_case(state)
    database.request_review_material(case["review_case_id"], "bank_statement_6_months", "Please mark the six-month statement as ready.")
    saved = database.get_review_case(case["review_case_id"])

    assert saved["status"] == "material_requested"
    assert saved["material_requests"][0]["material_key"] == "bank_statement_6_months"
    assert "ABCDE1234F" not in str(saved)


@pytest.mark.anyio
async def test_review_handoff_endpoint_returns_only_a_masked_pending_case(monkeypatch):
    import backend.main as main
    from backend.llm.base import ExtractionResult

    async def no_llm_extraction(**_):
        return ExtractionResult()

    monkeypatch.setattr(main.llm_service, "extract_with_fallback", no_llm_extraction)
    monkeypatch.setattr(main.sarvam_service, "tts", lambda **_: (_ for _ in ()).throw(RuntimeError("disabled in test")))
    monkeypatch.setattr(main.sarvam_service, "translate", lambda text, src, tgt: text)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/sessions", json={"journey_id": "personal_loan"})
        session_id = created.json()["session_id"]
        for value in ("80000", "150000", "24 months", "zero", "I agree"):
            response = await client.post(f"/sessions/{session_id}/turns", json={"text": value})
            assert response.status_code == 200
        for _ in range(5):
            response = await client.post(f"/sessions/{session_id}/turns", json={"text": "yes"})
            assert response.status_code == 200
        submitted = await client.post(f"/sessions/{session_id}/turns", json={"text": "I agree"})
        review = await client.get(f"/sessions/{session_id}/review")

    assert submitted.json()["next_action"] == "review_submitted"
    assert submitted.json()["review_case"]["status"] == "pending"
    assert review.status_code == 200
    assert review.json()["review_case"]["readiness"]["outcome"] == "Ready for human review"
    assert "ABCDE1234F" not in str(review.json())


@pytest.mark.anyio
async def test_confirm_decline_returns_no_review_case(monkeypatch):
    import backend.main as main

    monkeypatch.setattr(main.sarvam_service, "tts", lambda **_: (_ for _ in ()).throw(RuntimeError("disabled in test")))
    monkeypatch.setattr(main.sarvam_service, "translate", lambda text, src, tgt: text)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/sessions", json={"journey_id": "payment_help"})
        response = await client.post(
            f"/sessions/{created.json()['session_id']}/confirm",
            json={"consent_granted": False},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "collecting"
    assert response.json()["review_case"] is None

