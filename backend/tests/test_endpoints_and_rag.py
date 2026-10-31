import pytest
import httpx
from backend.main import app
from backend.rag import rag_service


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def async_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.anyio
async def test_rag_chunking_and_search():
    await rag_service.load_and_index()
    assert len(rag_service.chunks) > 0

    # Search payment help
    results = await rag_service.search("auto debit bounce fee waiver", top_k=3, category="payment_help")
    assert len(results) > 0
    assert any("waiver" in r.chunk.heading.lower() or "auto-debit" in r.chunk.heading.lower() for r in results)
    assert results[0].chunk.id.startswith("kb-payment_help-")

    # Search loan rejection
    rej_results = await rag_service.search("high foir debt ratio cooling off period", top_k=3, category="loan_rejection")
    assert len(rej_results) > 0
    assert any("foir" in r.chunk.heading.lower() or "cooling" in r.chunk.heading.lower() for r in rej_results)
    assert rej_results[0].chunk.id.startswith("kb-loan_rejection-")


@pytest.mark.anyio
async def test_new_session_and_turns_lifecycle(async_client: httpx.AsyncClient):
    # 1. Create session
    resp = await async_client.post("/sessions", json={
        "journey_id": "payment_help",
        "customer_id": "CUST-1001",
    })
    assert resp.status_code == 200
    data = resp.json()
    session_id = data["session_id"]
    assert data["journey_id"] == "payment_help"
    assert data["next_action"] == "ask_field"

    # 2. Turn 1: Provide account id
    t1 = await async_client.post(f"/sessions/{session_id}/turns", json={"text": "PAYTM-LN-8812"})
    assert t1.status_code == 200
    t1_data = t1.json()
    assert t1_data["state"]["fields"]["account_id"]["value"] == "[ACCOUNT_REDACTED]"
    assert "PAYTM-LN-8812" not in str(t1_data["state"])

    # 3. Turn 2: Provide issue category (bounce)
    t2 = await async_client.post(f"/sessions/{session_id}/turns", json={"text": "auto debit bounce fee"})
    assert t2.status_code == 200
    t2_data = t2.json()
    assert len(t2_data["citations"]) > 0
    assert any("kb-payment_help" in c for c in t2_data["citations"])

    # 4. Turn 3: Provide amount due
    t3 = await async_client.post(f"/sessions/{session_id}/turns", json={"text": "4,500"})
    assert t3.status_code == 200
    t3_data = t3.json()
    assert t3_data["next_action"] == "request_consent"
    assert t3_data["results"] is not None
    assert t3_data["results"]["metrics"]["late_fee_waiver"] == 350.0

    # 5. Confirm session (explicit consent)
    conf = await async_client.post(f"/sessions/{session_id}/confirm", json={
        "consent_granted": True,
        "consent_text": "I agree to the sample waiver resolution",
    })
    assert conf.status_code == 200
    assert conf.json()["status"] == "submitted"

    # 6. Create support ticket
    tck = await async_client.post(f"/sessions/{session_id}/tickets", json={
        "category": "auto_debit_waiver",
        "issue_description": "Auto-debit bounce on PAYTM-LN-8812 with instant waiver applied.",
    })
    assert tck.status_code == 200
    assert tck.json()["ticket_id"].startswith("TCK-")

    # 7. Get session
    sess_get = await async_client.get(f"/sessions/{session_id}")
    assert sess_get.status_code == 200
    sess_data = sess_get.json()
    assert sess_data["state"]["status"] == "submitted"
    assert len(sess_data["tickets"]) >= 1


@pytest.mark.anyio
async def test_customer_transactions(async_client: httpx.AsyncClient):
    resp = await async_client.get("/customers/CUST-1001/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["customer"]["name"] == "Prasad Sharma"
    assert len(data["transactions"]) >= 3
    assert data["transactions"][0]["sample_label"] == "Sample"

