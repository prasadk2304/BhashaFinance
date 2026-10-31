import pytest
import httpx
from backend.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def async_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.anyio
async def test_health_endpoint(async_client: httpx.AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["sample_mode"] is True


@pytest.mark.anyio
async def test_list_products(async_client: httpx.AsyncClient):
    response = await async_client.get("/api/products")
    assert response.status_code == 200
    products = response.json()
    assert len(products) == 4
    journey_ids = [p["journey_id"] for p in products]
    assert "personal_loan" in journey_ids
    assert "sip" in journey_ids
    assert "payment_help" in journey_ids
    assert "loan_rejection" in journey_ids


@pytest.mark.anyio
async def test_api_rules_emi(async_client: httpx.AsyncClient):
    payload = {
        "principal": 100000,
        "annual_interest_rate": 12.0,
        "tenure_months": 12,
        "generate_schedule": True,
    }
    response = await async_client.post("/api/rules/emi", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["monthly_emi_rounded"] == 8885
    assert data["sample_label"] == "Sample"
    assert data["is_synthetic"] is True
    assert len(data["amortization_sample"]) == 12


@pytest.mark.anyio
async def test_api_rules_sip(async_client: httpx.AsyncClient):
    payload = {
        "monthly_investment": 5000,
        "expected_annual_return": 12.0,
        "duration_years": 3,
        "generate_yearly_breakdown": True,
    }
    response = await async_client.post("/api/rules/sip", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["future_value_rounded"] == 217538
    assert data["sample_label"] == "Sample"


@pytest.mark.anyio
async def test_api_rules_foir(async_client: httpx.AsyncClient):
    payload = {
        "monthly_income": 80000,
        "existing_obligations": 10000,
        "proposed_emi": 15000,
        "max_foir_threshold_pct": 50.0,
    }
    response = await async_client.post("/api/rules/foir", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_eligible"] is True
    assert data["foir_percentage"] == 31.25


@pytest.mark.anyio
async def test_api_rules_parse(async_client: httpx.AsyncClient):
    payload = {"text": "I want a loan of 1.5 lakh with 80k income"}
    response = await async_client.post("/api/rules/parse", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["single_amount"] == 150000.0
    extracted_vals = [item[1] for item in data["all_amounts"]]
    assert 150000.0 in extracted_vals
    assert 80000.0 in extracted_vals


@pytest.mark.anyio
async def test_end_to_end_journey_flow_with_consent(async_client: httpx.AsyncClient):
    sess_id = "test_api_flow_99"

    # 1. Start journey
    start_resp = await async_client.post("/api/journey/start", json={
        "session_id": sess_id,
        "journey_id": "personal_loan",
    })
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["target_field"] == "monthly_income"

    # 2. Provide monthly income: 80k
    m1 = await async_client.post("/api/journey/message", json={"session_id": sess_id, "text": "80k"})
    assert m1.json()["target_field"] == "loan_amount"

    # 3. Provide loan amount: 1.5 lakh
    m2 = await async_client.post("/api/journey/message", json={"session_id": sess_id, "text": "1.5 lakh"})
    assert m2.json()["target_field"] == "tenure_months"

    # 4. Provide tenure: 12 months
    m3 = await async_client.post("/api/journey/message", json={"session_id": sess_id, "text": "12 months"})
    assert m3.json()["target_field"] == "existing_emis"

    # 5. Provide existing EMIs: zero
    m4 = await async_client.post("/api/journey/message", json={"session_id": sess_id, "text": "zero"})
    m4_data = m4.json()
    assert m4_data["next_action"] == "request_consent"
    assert m4_data["calculation"] is not None
    assert m4_data["calculation"]["sample_label"] == "Sample"

    # 6. Attempt submission before consent -> MUST FAIL with 403 Forbidden
    sub_fail = await async_client.post(f"/api/journey/submit?session_id={sess_id}")
    assert sub_fail.status_code == 403

    # 7. Personal-loan consent opens the least-data document-readiness check.
    m5 = await async_client.post("/api/journey/message", json={"session_id": sess_id, "text": "Yes, I agree"})
    assert m5.json()["next_action"] == "document_review"

    # 8. Confirm synthetic availability only; no document content is submitted.
    for _ in range(5):
        doc_step = await async_client.post("/api/journey/message", json={"session_id": sess_id, "text": "yes"})
        assert doc_step.status_code == 200
    assert doc_step.json()["next_action"] == "request_review_consent"

    # 9. A separate affirmative creates the masked human-review handoff.
    handoff = await async_client.post("/api/journey/message", json={"session_id": sess_id, "text": "I agree"})
    assert handoff.json()["next_action"] == "review_submitted"

    # 10. Submit now succeeds
    sub_success = await async_client.post(f"/api/journey/submit?session_id={sess_id}")
    assert sub_success.status_code == 200
    assert sub_success.json()["status"] == "success"
    assert sub_success.json()["is_sample"] is True
