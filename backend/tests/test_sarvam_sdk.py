from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock
import pytest
import httpx

from backend.config import SUPPORTED_LANGUAGES, settings
from backend.main import app
from backend.rules.parser import normalize_devanagari_digits, parse_amount
from backend.rules.spoken_numbers import convert_amounts_in_text, format_amount_to_words
from backend.sarvam import SarvamService, SarvamUnavailable, CACHE_DIR


# ==============================================================================
# 1. Devanagari Parsing Tests
# ==============================================================================

def test_devanagari_digit_normalization():
    assert normalize_devanagari_digits("८०,००० रुपये") == "80,000 रुपये"
    assert normalize_devanagari_digits("८० हजार") == "80 हजार"
    assert normalize_devanagari_digits("१.५ लाख") == "1.5 लाख"


def test_devanagari_amount_parsing():
    assert parse_amount("८०,००० रुपये") == 80000.0
    assert parse_amount("८० हजार") == 80000.0
    assert parse_amount("80k") == 80000.0
    assert parse_amount("1.5 lakh") == 150000.0
    assert parse_amount("१.५ लाख") == 150000.0


# ==============================================================================
# 2. Spoken Amount Helper Tests
# ==============================================================================

def test_spoken_amounts_helper_marathi():
    # 80000 -> eighty thousand in Marathi (ऐंशी हजार रुपये)
    assert format_amount_to_words(80000, "mr-IN") == "ऐंशी हजार रुपये"
    assert format_amount_to_words(150000, "mr-IN") == "एक लाख पन्नास हजार रुपये"

    text = "तुमची रक्कम 80000 आहे"
    converted = convert_amounts_in_text(text, "mr-IN")
    assert "ऐंशी हजार रुपये" in converted


def test_spoken_amounts_helper_english_and_hindi():
    assert format_amount_to_words(80000, "en-IN") == "eighty thousand rupees"
    assert "अस्सी" in format_amount_to_words(80000, "hi-IN")
    assert "हज़ार" in format_amount_to_words(80000, "hi-IN")


# ==============================================================================
# 3. Mocked Sarvam SDK Tests (STT, TTS, Cache Hit, Bytes vs Iterator)
# ==============================================================================

def test_sarvam_stt_wrapper_mocked(tmp_path):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.transcript = "माझे उत्पन्न ऐंशी हजार आहे"
    mock_client.speech_to_text.transcribe.return_value = mock_response

    service = SarvamService(api_key="test-api-key")
    service.set_client(mock_client)

    dummy_audio = tmp_path / "test.wav"
    dummy_audio.write_bytes(b"RIFF dummy wav data")

    transcript = service.stt(path=dummy_audio, lang="mr-IN")
    assert transcript == "माझे उत्पन्न ऐंशी हजार आहे"
    mock_client.speech_to_text.transcribe.assert_called_once()


def test_sarvam_tts_bytes_response(tmp_path, monkeypatch):
    import backend.sarvam as bs
    monkeypatch.setattr(bs, "CACHE_DIR", tmp_path)

    mock_client = MagicMock()
    mock_audio_bytes = b"ID3FakeMp3AudioDataForTesting"
    mock_client.text_to_speech.convert_stream.return_value = mock_audio_bytes

    service = SarvamService(api_key="test-api-key")
    service.set_client(mock_client)

    unique_text = f"Unique speech text for bytes test {tmp_path.name}"
    mp3_path = service.tts(text=unique_text, lang="mr-IN")

    assert mp3_path.exists()
    assert mp3_path.read_bytes() == mock_audio_bytes
    assert mock_client.text_to_speech.convert_stream.call_count == 1


def test_sarvam_tts_iterator_response(tmp_path, monkeypatch):
    import backend.sarvam as bs
    monkeypatch.setattr(bs, "CACHE_DIR", tmp_path)

    mock_client = MagicMock()
    chunk1 = b"ID3ChunkOne"
    chunk2 = b"ChunkTwoAudioData"
    # Returns an iterator of byte chunks
    mock_client.text_to_speech.convert_stream.return_value = iter([chunk1, chunk2])

    service = SarvamService(api_key="test-api-key")
    service.set_client(mock_client)

    unique_text = f"Unique speech text for iterator test {tmp_path.name}"
    mp3_path = service.tts(text=unique_text, lang="mr-IN")

    assert mp3_path.exists()
    assert mp3_path.read_bytes() == chunk1 + chunk2


def test_sarvam_tts_cache_hit_skips_api_call(tmp_path, monkeypatch):
    import backend.sarvam as bs
    monkeypatch.setattr(bs, "CACHE_DIR", tmp_path)

    mock_client = MagicMock()
    mock_audio_bytes = b"CachedAudioData"
    mock_client.text_to_speech.convert_stream.return_value = mock_audio_bytes

    service = SarvamService(api_key="test-api-key")
    service.set_client(mock_client)

    unique_text = f"Unique caching text {tmp_path.name}"
    # First call: hits API
    path1 = service.tts(text=unique_text, lang="mr-IN")
    assert mock_client.text_to_speech.convert_stream.call_count == 1

    # Second call: must hit cache and NOT call convert_stream again
    path2 = service.tts(text=unique_text, lang="mr-IN")
    assert path1 == path2
    assert mock_client.text_to_speech.convert_stream.call_count == 1


def test_sarvam_translate_wrapper_mocked():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.translated_text = "तुमचा कर्ज अर्ज मंजूर झाला आहे."
    mock_client.text.translate.return_value = mock_response

    service = SarvamService(api_key="test-api-key")
    service.set_client(mock_client)

    res = service.translate(text="Your loan application has been approved.", src="en-IN", tgt="mr-IN")
    assert res == "तुमचा कर्ज अर्ज मंजूर झाला आहे."
    mock_client.text.translate.assert_called_once()


def test_sarvam_unavailable_after_retries(tmp_path):
    mock_client = MagicMock()
    mock_client.speech_to_text.transcribe.side_effect = RuntimeError("Sarvam 500 Server Error")

    service = SarvamService(api_key="test-api-key")
    service.set_client(mock_client)

    dummy_audio = tmp_path / "test_err.wav"
    dummy_audio.write_bytes(b"dummy wav data")

    with pytest.raises(SarvamUnavailable):
        service.stt(path=dummy_audio, lang="mr-IN")

    # Verified 1 retry occurred (2 calls total)
    assert mock_client.speech_to_text.transcribe.call_count == 2


# ==============================================================================
# 4. Languages and Endpoint Verification Tests
# ==============================================================================

@pytest.mark.anyio
async def test_get_languages_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/languages")
        assert resp.status_code == 200
        data = resp.json()
        assert "mr-IN" in data
        assert "hi-IN" in data
        assert "en-IN" in data
        assert data["mr-IN"] == "मराठी"


@pytest.mark.anyio
async def test_unsupported_language_code_rejected_with_400():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # TTS with unsupported language code
        resp = await ac.post("/api/voice/tts", json={"text": "Hello", "language_code": "es-ES"})
        assert resp.status_code == 400
        assert "Unsupported language code" in resp.json()["detail"]


@pytest.mark.anyio
async def test_stt_failure_returns_503_fallback_text(monkeypatch):
    from backend.sarvam import sarvam_service

    # Force sarvam_service.stt to raise SarvamUnavailable
    def mock_fail_stt(*args, **kwargs):
        raise SarvamUnavailable("Voice engine offline")

    monkeypatch.setattr(sarvam_service, "stt", mock_fail_stt)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # Create session
        s_resp = await ac.post("/sessions", json={"journey_id": "personal_loan"})
        session_id = s_resp.json()["session_id"]

        # Send turn with audio
        files = {"audio": ("test.wav", b"RIFF dummy wav audio", "audio/wav")}
        data = {"language_code": "mr-IN"}
        turn_resp = await ac.post(f"/sessions/{session_id}/turns", files=files, data=data)

        # Must return 503 with fallback="text"
        assert turn_resp.status_code == 503
        body = turn_resp.json()
        assert body.get("fallback") == "text"

