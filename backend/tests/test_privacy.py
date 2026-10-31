import json

import httpx
import pytest

from backend.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_redacts_pan_aadhaar_mobile_dob_bank_and_account_identifiers():
    from backend.privacy import redact_sensitive_text

    raw = (
        "PAN ABCDE1234F, Aadhaar 1234 5678 9012, mobile +91 9876543210, "
        "DOB 01/02/1990, account 123456789012 and PAYTM-LN-8812"
    )

    result = redact_sensitive_text(raw)

    for value in ("ABCDE1234F", "1234 5678 9012", "9876543210", "01/02/1990", "123456789012", "PAYTM-LN-8812"):
        assert value not in result.text
    assert result.previews["pan"] == "ABCDE****F"
    assert result.previews["aadhaar"] == "XXXX XXXX 9012"
    assert result.previews["mobile"] == "+91 ******3210"
    assert result.previews["dob"] == "**/**/1990"
    assert result.previews["bank_account"] == "••••9012"
    assert "[ACCOUNT_REDACTED]" in result.text


@pytest.mark.anyio
async def test_turn_sends_and_persists_redacted_identifier_text_only(monkeypatch):
    import backend.main as main

    received_by_llm: list[str] = []

    async def capture_extract(*, transcript, schema, language):
        received_by_llm.append(transcript)
        from backend.llm.base import ExtractionResult
        return ExtractionResult()

    monkeypatch.setattr(main.llm_service, "extract_with_fallback", capture_extract)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/sessions", json={"journey_id": "personal_loan"})
        session_id = created.json()["session_id"]
        raw = "I earn 80000. My PAN is ABCDE1234F and Aadhaar is 1234 5678 9012."
        turn = await client.post(f"/sessions/{session_id}/turns", json={"text": raw})

    assert turn.status_code == 200
    body = turn.json()
    persisted = json.dumps(body["state"])
    for raw_value in ("ABCDE1234F", "1234 5678 9012"):
        assert raw_value not in received_by_llm[0]
        assert raw_value not in persisted
        assert raw_value not in (body["transcript"] or "")
    assert "[PAN_REDACTED]" in received_by_llm[0]
    assert "[AADHAAR_REDACTED]" in persisted
    assert body["state"]["masked_previews"] == {"pan": "ABCDE****F", "aadhaar": "XXXX XXXX 9012"}

