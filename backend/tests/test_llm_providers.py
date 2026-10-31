import json
import logging
import pytest
from unittest.mock import AsyncMock, patch
import httpx

from backend.llm.base import LLMProvider
from backend.llm.sarvam import SarvamProvider
from backend.llm.ollama import OllamaProvider
from backend.llm.service import LLMService


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ==============================================================================
# 1. SarvamProvider Tests
# ==============================================================================

@pytest.mark.anyio
async def test_sarvam_provider_extract_success():
    provider = SarvamProvider(api_key="sk-test-key-12345", base_url="https://api.sarvam.ai/v1")

    mock_resp_json = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"monthly_income": 80000.0, "loan_amount": 150000.0})
                }
            }
        ]
    }

    mock_client = AsyncMock()
    mock_post = AsyncMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.raise_for_status = lambda: None
    mock_post.return_value.json = lambda: mock_resp_json
    mock_client.post = mock_post
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        res = await provider.extract(
            transcript="I earn 80k and need 1.5 lakh loan",
            schema={"monthly_income": "float", "loan_amount": "float"},
        )
        assert res["monthly_income"] == 80000.0
        assert res["loan_amount"] == 150000.0
        assert mock_post.await_args.kwargs["json"]["reasoning_effort"] is None


@pytest.mark.anyio
async def test_sarvam_provider_timeout_and_retry():
    provider = SarvamProvider(api_key="sk-test-key-12345")

    mock_client = AsyncMock()
    # First attempt raises Timeout, second attempt succeeds
    success_resp = AsyncMock()
    success_resp.status_code = 200
    success_resp.raise_for_status = lambda: None
    success_resp.json = lambda: {
        "choices": [{"message": {"content": json.dumps({"tenure_months": 24})}}]
    }

    mock_client.post = AsyncMock(side_effect=[httpx.TimeoutException("Timeout"), success_resp])
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        res = await provider.extract(
            transcript="for 2 years",
            schema={"tenure_months": "int"},
        )
        assert res["tenure_months"] == 24
        assert mock_client.post.call_count == 2


# ==============================================================================
# 2. OllamaProvider Tests
# ==============================================================================

@pytest.mark.anyio
async def test_ollama_provider_extract_success():
    provider = OllamaProvider(base_url="http://localhost:11434", model="qwen2.5:3b")

    mock_resp_json = {
        "response": json.dumps({"monthly_investment": 5000.0, "duration_years": 3.0})
    }

    mock_client = AsyncMock()
    mock_post = AsyncMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.raise_for_status = lambda: None
    mock_post.return_value.json = lambda: mock_resp_json
    mock_client.post = mock_post
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        res = await provider.extract(
            transcript="invest 5000 every month for 3 years",
            schema={"monthly_investment": "float", "duration_years": "float"},
        )
        assert res["monthly_investment"] == 5000.0
        assert res["duration_years"] == 3.0


# ==============================================================================
# 3. Automatic Fallback Chain: Sarvam -> Ollama -> Regex Alone
# ==============================================================================

@pytest.mark.anyio
async def test_fallback_sarvam_error_to_ollama():
    sarvam_mock = AsyncMock(spec=SarvamProvider)
    sarvam_mock.extract.side_effect = RuntimeError("Sarvam error after retry")

    ollama_mock = AsyncMock(spec=OllamaProvider)
    ollama_mock.extract.return_value = {"monthly_income": 80000.0}

    service = LLMService(
        provider_name="sarvam",
        sarvam_provider=sarvam_mock,
        ollama_provider=ollama_mock,
    )

    result = await service.extract_with_fallback(
        transcript="My monthly income is 80k",
        schema={"monthly_income": "float"},
    )

    assert result.source_provider == "ollama"
    assert result.extracted_fields["monthly_income"] == 80000.0
    assert result.field_metadata["monthly_income"].status == "confirmed"


@pytest.mark.anyio
async def test_fallback_all_fail_to_regex_alone():
    sarvam_mock = AsyncMock(spec=SarvamProvider)
    sarvam_mock.extract.side_effect = RuntimeError("Sarvam down")

    ollama_mock = AsyncMock(spec=OllamaProvider)
    ollama_mock.extract.side_effect = RuntimeError("Ollama down")

    service = LLMService(
        provider_name="sarvam",
        sarvam_provider=sarvam_mock,
        ollama_provider=ollama_mock,
    )

    # Transcript contains 1.5 lakh
    result = await service.extract_with_fallback(
        transcript="I am seeking a loan of 1.5 lakh",
        schema={"loan_amount": "float"},
    )

    # Must fall back to regex parser alone and flag source="regex_parser"
    assert result.source_provider == "regex_parser"
    assert result.extracted_fields["loan_amount"] == 150000.0
    assert result.field_metadata["loan_amount"].source == "regex_parser"
    assert result.field_metadata["loan_amount"].status == "confirmed"


@pytest.mark.anyio
async def test_identifier_fallback_keeps_the_redacted_account_placeholder():
    sarvam_mock = AsyncMock(spec=SarvamProvider)
    sarvam_mock.extract.side_effect = RuntimeError("Sarvam down")
    ollama_mock = AsyncMock(spec=OllamaProvider)
    ollama_mock.extract.side_effect = RuntimeError("Ollama down")
    service = LLMService(
        provider_name="sarvam",
        sarvam_provider=sarvam_mock,
        ollama_provider=ollama_mock,
    )

    result = await service.extract_with_fallback(
        transcript="PAYTM-LN-8812",
        schema={"account_id": "str"},
    )

    assert result.extracted_fields["account_id"] == "[ACCOUNT_REDACTED]"


# ==============================================================================
# 4. Mismatch Rule: Extracted number must match regex parser
# ==============================================================================

@pytest.mark.anyio
async def test_number_mismatch_marks_inferred_and_requests_readback():
    sarvam_mock = AsyncMock(spec=SarvamProvider)
    # LLM hallucinates 90000 when user transcript clearly says 80k
    sarvam_mock.extract.return_value = {"monthly_income": 90000.0}

    service = LLMService(
        provider_name="sarvam",
        sarvam_provider=sarvam_mock,
    )

    result = await service.extract_with_fallback(
        transcript="I make 80k monthly",
        schema={"monthly_income": "float"},
    )

    # Rule: On mismatch mark status="inferred" and ask for read-back
    meta = result.field_metadata["monthly_income"]
    assert meta.status == "inferred"
    assert meta.readback_required is True
    assert "confirm" in meta.readback_message.lower()


@pytest.mark.anyio
async def test_number_match_marks_confirmed():
    sarvam_mock = AsyncMock(spec=SarvamProvider)
    # LLM correctly extracts 80000 matching regex parser for '80k'
    sarvam_mock.extract.return_value = {"monthly_income": 80000.0}

    service = LLMService(
        provider_name="sarvam",
        sarvam_provider=sarvam_mock,
    )

    result = await service.extract_with_fallback(
        transcript="My salary is 80k",
        schema={"monthly_income": "float"},
    )

    meta = result.field_metadata["monthly_income"]
    assert meta.status == "confirmed"
    assert meta.readback_required is False


# ==============================================================================
# 5. Security Test: Never Log Transcripts or Keys
# ==============================================================================

@pytest.mark.anyio
async def test_security_never_logs_transcripts_or_keys(caplog):
    secret_key = "sk-super-secret-key-999"
    secret_transcript = "My secret salary is 999999 and account is SECRET-ACC-111"

    provider = SarvamProvider(api_key=secret_key)

    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("Network offline")
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with caplog.at_level(logging.DEBUG):
        with patch("httpx.AsyncClient", return_value=mock_client):
            try:
                await provider.extract(
                    transcript=secret_transcript,
                    schema={"salary": "float"},
                )
            except Exception:
                pass

    log_text = caplog.text
    # Transcripts and keys must NEVER appear in logs
    assert secret_key not in log_text
    assert secret_transcript not in log_text
    assert "SECRET-ACC-111" not in log_text


# ==============================================================================
# 6. Explain Rule: Receives only backend facts and forbids hallucinations
# ==============================================================================

@pytest.mark.anyio
async def test_explain_receives_only_facts():
    sarvam_mock = AsyncMock(spec=SarvamProvider)
    sarvam_mock.explain.return_value = "Sample offer: Monthly EMI is ₹8,885."

    service = LLMService(
        provider_name="sarvam",
        sarvam_provider=sarvam_mock,
    )

    facts = {
        "journey_id": "personal_loan",
        "monthly_emi": 8884.88,
        "is_eligible": True,
        "sample_label": "Sample",
    }

    result = await service.explain(facts=facts)
    assert "8,885" in result
    sarvam_mock.explain.assert_called_once_with(facts, "en", "professional")

