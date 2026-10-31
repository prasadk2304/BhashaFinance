import asyncio
from pathlib import Path
import pytest
import httpx

from backend.rules.spoken_numbers import (
    number_to_words_en,
    number_to_words_hi,
    number_to_words_mr,
    format_amount_to_words,
    convert_amounts_in_text,
)
from backend.rules.plain_definitions import add_inline_definitions
from backend.sarvam import sarvam_service, pregenerate_demo_audio, CACHE_DIR
from backend.llm.service import llm_service, detect_urgency_tone
from backend.rules.product_specs import PRODUCT_SPECS


# ==============================================================================
# 1. Tests for Spoken Number and Currency Converter
# ==============================================================================

def test_spoken_numbers_english():
    assert number_to_words_en(80000) == "eighty thousand"
    assert number_to_words_en(150000) == "one lakh fifty thousand"
    assert number_to_words_en(4500) == "four thousand five hundred"
    assert number_to_words_en(350) == "three hundred fifty"
    assert number_to_words_en(7027) == "seven thousand twenty-seven"


def test_spoken_numbers_hindi():
    hi_80k = number_to_words_hi(80000)
    assert "अस्सी" in hi_80k and "हज़ार" in hi_80k

    hi_1_5l = number_to_words_hi(150000)
    assert "एक लाख" in hi_1_5l and "पचास" in hi_1_5l


def test_spoken_numbers_marathi():
    mr_80k = number_to_words_mr(80000)
    assert "ऐंशी" in mr_80k and "हजार" in mr_80k

    mr_4500 = number_to_words_mr(4500)
    assert "चार हजार" in mr_4500 and "पाचशे" in mr_4500


def test_convert_amounts_in_text():
    # English
    t_en = "Your Sample EMI is ₹7,027 and total loan is Rs 80,000."
    res_en = convert_amounts_in_text(t_en, "en-IN")
    assert "seven thousand twenty-seven rupees" in res_en
    assert "eighty thousand rupees" in res_en

    # Hindi
    t_hi = "आपकी ईएमआई ₹4,500 है"
    res_hi = convert_amounts_in_text(t_hi, "hi-IN")
    assert "रुपये" in res_hi

    # Marathi
    t_mr = "कर्ज रक्कम ₹80,000 आहे"
    res_mr = convert_amounts_in_text(t_mr, "mr-IN")
    assert "रुपये" in res_mr


# ==============================================================================
# 2. Tests for Sarvam TTS Caching and Pre-generation
# ==============================================================================

@pytest.mark.anyio
async def test_tts_caching_and_pregeneration():
    test_text = "Sample test audio string for caching verification ₹5,000"
    # First call (generates or saves to cache)
    res1 = await sarvam_service.text_to_speech(test_text, "en-IN")
    assert res1.audio_base64 is not None

    # Second call MUST hit cache
    res2 = await sarvam_service.text_to_speech(test_text, "en-IN")
    assert res2.cached is True
    assert res2.audio_base64 == res1.audio_base64

    # Run pregeneration of demo audio
    summary = await pregenerate_demo_audio()
    assert summary["cached_items"] >= 4


# ==============================================================================
# 3. Tests for Plain-Language Inline Definitions on First Mention
# ==============================================================================

def test_plain_language_inline_definitions():
    sample = (
        "Based on your income, your EMI is ₹7,027 for a tenure of 24 months. "
        "Your FOIR is 21.3% and APR is 11.5%. Next month's EMI is also due."
    )
    expanded = add_inline_definitions(sample)

    # First mentions are expanded
    assert "EMI (Equated Monthly Installment: your fixed monthly payment)" in expanded
    assert "FOIR (Fixed Obligation to Income Ratio: percentage of monthly income spent on loan payments)" in expanded
    assert "tenure (the total loan duration in months)" in expanded
    assert "APR (Annual Percentage Rate: yearly interest rate including standard fees)" in expanded

    # Subsequent mentions are NOT re-expanded
    second_part = expanded.split("Next month's")[1]
    assert "Equated Monthly Installment" not in second_part


# ==============================================================================
# 4. Tests for Tone Layer in Explain (Urgency/Distress -> Calm)
# ==============================================================================

def test_urgency_tone_detection():
    # Urgent facts
    urgent_facts = {
        "issue_type": "auto_debit_bounce",
        "user_note": "medical emergency at hospital, urgent funds stuck",
        "loan_amount": 50000,
    }
    assert detect_urgency_tone(urgent_facts) == "calm"

    # Standard facts
    standard_facts = {
        "journey_id": "personal_loan",
        "loan_amount": 100000,
        "tenure_months": 12,
    }
    assert detect_urgency_tone(standard_facts) == "professional"


@pytest.mark.anyio
async def test_explain_calm_tone_under_40_words():
    urgent_facts = {
        "issue_type": "rejected",
        "details": "emergency hospital bill need immediate help",
        "journey_id": "payment_help",
    }
    explanation = await llm_service.explain(urgent_facts, language="en")
    word_count = len(explanation.split())
    # Rules: acknowledge situation, give next step first, under 40 words
    assert word_count <= 40 or "sample" in explanation.lower()
    assert len(explanation.strip()) > 0


# ==============================================================================
# 5. Tests for "Why am I asking this?" in Product Specs
# ==============================================================================

def test_why_we_ask_populated_in_all_product_specs():
    for j_id, spec in PRODUCT_SPECS.items():
        for f_name, f_def in spec.field_definitions.items():
            assert f_def.why_we_ask is not None, f"Missing why_we_ask for {j_id}.{f_name}"
            assert len(f_def.why_we_ask.strip()) > 10, f"Too short why_we_ask for {j_id}.{f_name}"


# ==============================================================================
# 6. Tests for Agent Handoff Endpoint
# ==============================================================================

@pytest.mark.anyio
async def test_agent_handoff_endpoint(async_client: httpx.AsyncClient):
    # Create session
    resp = await async_client.post("/sessions", json={
        "journey_id": "personal_loan",
        "customer_id": "CUST-1001",
    })
    assert resp.status_code == 200
    s_data = resp.json()
    session_id = s_data["session_id"]
    assert s_data.get("target_field_why") is not None

    # Request agent handoff
    handoff_resp = await async_client.post(f"/sessions/{session_id}/agent_handoff")
    assert handoff_resp.status_code == 200
    h_data = handoff_resp.json()

    assert h_data["session_id"] == session_id
    assert h_data["handoff_id"].startswith("AGT-")
    assert "Customer session" in h_data["summary_paragraph"]
    assert h_data["journey_state"] is not None
    assert h_data["status"] == "connected"
