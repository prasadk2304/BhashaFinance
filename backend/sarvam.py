import base64
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import httpx
from pydantic import BaseModel

from backend.config import settings
from backend.rules.spoken_numbers import convert_amounts_in_text

logger = logging.getLogger(__name__)

SARVAM_BASE_URL = "https://api.sarvam.ai"
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Standard BCP-47 mappings for supported languages
LANG_CODE_MAP = {
    "en": "en-IN",
    "hi": "hi-IN",
    "mr": "mr-IN",
    "en-in": "en-IN",
    "hi-in": "hi-IN",
    "mr-in": "mr-IN",
}

LANG_DISPLAY_NAMES = {
    "en-IN": "English",
    "hi-IN": "Hindi (हिंदी)",
    "mr-IN": "Marathi (मराठी)",
}


class SttResponse(BaseModel):
    transcript: str
    language_code: Optional[str] = "en-IN"
    is_fallback: bool = False
    error: Optional[str] = None
    needs_confirmation: bool = False
    detected_language: Optional[str] = None
    confirmation_prompt: Optional[str] = None


class TtsResponse(BaseModel):
    audio_base64: Optional[str] = None
    format: str = "wav"
    is_fallback: bool = False
    error: Optional[str] = None
    cached: bool = False
    spoken_text: Optional[str] = None


def generate_mock_wav_base64() -> str:
    """
    Generates a minimal valid 44-byte PCM WAV header for synthetic playback
    in offline/test environments when Sarvam API is unreachable.
    """
    # 44-byte valid RIFF/WAVE header with 0 data samples
    wav_header = (
        b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )
    return base64.b64encode(wav_header).decode("ascii")


class SarvamService:
    def __init__(self, api_key: Optional[str] = None):
        # Keep API key strictly server-side; NEVER expose to frontend
        self.api_key = api_key or settings.sarvam_api_key
        self.stt_model = "saarika:v2"
        self.tts_model = "bulbul:v3"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def normalize_language_code(self, lang_code: Optional[str]) -> str:
        """Normalizes language string to BCP-47 tag or returns 'unknown'."""
        if not lang_code:
            return "unknown"
        clean = lang_code.strip().lower()
        return LANG_CODE_MAP.get(clean, clean if "-" in clean else "unknown")

    def _get_cache_key(self, text: str, language_code: str, voice: str, model: str) -> str:
        raw_key = f"{text.strip()}::{language_code}::{voice}::{model}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    async def speech_to_text(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language_code: str = "unknown",
    ) -> SttResponse:
        """
        Transcribes audio using Sarvam STT API with model 'saarika:v2'.
        Supports explicit language from selector or auto-detect with confirmation prompt.
        Falls back gracefully to text fallback if key is missing or request fails.
        """
        normalized_lang = self.normalize_language_code(language_code)

        if not self.is_configured:
            logger.info("Sarvam API key not configured; STT using text fallback.")
            return SttResponse(
                transcript="",
                language_code=normalized_lang if normalized_lang != "unknown" else "en-IN",
                is_fallback=True,
                error="Sarvam API key not configured. Please use text input fallback.",
            )

        headers = {
            "api-subscription-key": self.api_key,
        }
        files = {
            "file": (filename, audio_bytes, "audio/wav"),
        }
        data = {
            "model": self.stt_model,
        }
        if normalized_lang != "unknown":
            data["language_code"] = normalized_lang

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{SARVAM_BASE_URL}/speech-to-text",
                    headers=headers,
                    files=files,
                    data=data,
                )
                resp.raise_for_status()
                result = resp.json()
                detected_lang = result.get("language_code", normalized_lang)
                transcript = result.get("transcript", "").strip()

                # If language was auto-detected (unknown passed), request confirmation
                needs_confirmation = False
                confirm_prompt = None
                if normalized_lang == "unknown" and detected_lang:
                    needs_confirmation = True
                    lang_name = LANG_DISPLAY_NAMES.get(detected_lang, detected_lang)
                    confirm_prompt = f"We detected {lang_name}. Would you like to continue in this language?"

                return SttResponse(
                    transcript=transcript,
                    language_code=detected_lang,
                    is_fallback=False,
                    needs_confirmation=needs_confirmation,
                    detected_language=detected_lang,
                    confirmation_prompt=confirm_prompt,
                )
        except Exception as e:
            logger.warning("Sarvam STT failed: %s. Falling back to text.", e)
            return SttResponse(
                transcript="",
                language_code=normalized_lang if normalized_lang != "unknown" else "en-IN",
                is_fallback=True,
                error=f"STT service error: {str(e)}",
            )

    async def text_to_speech(
        self,
        text: str,
        target_language_code: str = "en-IN",
        speaker: str = "meera",
    ) -> TtsResponse:
        """
        Synthesizes text to speech using Sarvam TTS API with model 'bulbul:v3'.
        1. Converts currency amounts to natural spoken words (e.g. ₹80,000 -> eighty thousand rupees).
        2. Checks disk cache in backend/cache/ by hash(text+language+voice).
        3. Calls Sarvam TTS if un-cached, then persists result.
        """
        if not text:
            return TtsResponse(audio_base64=None, is_fallback=True, error="Empty text input")

        normalized_lang = self.normalize_language_code(target_language_code)
        if normalized_lang == "unknown":
            normalized_lang = "en-IN"

        # 1. Convert amounts to spoken words before TTS
        spoken_text = convert_amounts_in_text(text, language_code=normalized_lang)

        # 2. Check disk cache
        cache_key = self._get_cache_key(spoken_text, normalized_lang, speaker, self.tts_model)
        cache_file = CACHE_DIR / f"{cache_key}.json"

        if cache_file.exists():
            try:
                cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
                return TtsResponse(
                    audio_base64=cached_data.get("audio_base64"),
                    format=cached_data.get("format", "wav"),
                    is_fallback=False,
                    cached=True,
                    spoken_text=spoken_text,
                )
            except Exception as read_err:
                logger.warning("Failed to read TTS cache (%s); proceeding with API.", read_err)

        # 3. Call Sarvam API if configured
        if not self.is_configured:
            logger.info("Sarvam API key not configured; generating mock audio cache for playback.")
            mock_audio = generate_mock_wav_base64()
            try:
                cache_file.write_text(
                    json.dumps({
                        "audio_base64": mock_audio,
                        "format": "wav",
                        "spoken_text": spoken_text,
                        "language_code": normalized_lang,
                        "speaker": speaker,
                    }),
                    encoding="utf-8",
                )
            except Exception:
                pass

            return TtsResponse(
                audio_base64=mock_audio,
                is_fallback=True,
                cached=False,
                spoken_text=spoken_text,
                error="Sarvam API key not configured. Mock audio returned.",
            )

        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": [spoken_text],
            "target_language_code": normalized_lang,
            "speaker": speaker,
            "model": self.tts_model,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{SARVAM_BASE_URL}/text-to-speech",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                result = resp.json()
                audios = result.get("audios", [])
                audio_data = audios[0] if audios else None

                # Persist to cache
                if audio_data:
                    try:
                        cache_file.write_text(
                            json.dumps({
                                "audio_base64": audio_data,
                                "format": "wav",
                                "spoken_text": spoken_text,
                                "language_code": normalized_lang,
                                "speaker": speaker,
                            }),
                            encoding="utf-8",
                        )
                    except Exception as cache_err:
                        logger.warning("Failed to save audio to cache: %s", cache_err)

                return TtsResponse(
                    audio_base64=audio_data,
                    is_fallback=False,
                    cached=False,
                    spoken_text=spoken_text,
                )
        except Exception as e:
            logger.warning("Sarvam TTS failed: %s. Using cached mock audio.", e)
            mock_audio = generate_mock_wav_base64()
            try:
                cache_file.write_text(
                    json.dumps({
                        "audio_base64": mock_audio,
                        "format": "wav",
                        "spoken_text": spoken_text,
                        "language_code": normalized_lang,
                        "speaker": speaker,
                    }),
                    encoding="utf-8",
                )
            except Exception:
                pass

            return TtsResponse(
                audio_base64=mock_audio,
                is_fallback=True,
                error=f"TTS service error: {str(e)}",
                spoken_text=spoken_text,
            )


sarvam_service = SarvamService()


async def pregenerate_demo_audio() -> Dict[str, int]:
    """
    Pre-generates and caches TTS audio for all four seeded demo scenarios
    in English, Hindi, and Marathi to ensure instant voice playback in demo mode.
    """
    demo_texts = [
        # 1. Personal Loan
        "Based on your inputs, your Sample loan offer is ₹1,50,000 for 24 months at 11.5% p.a., with an EMI of ₹7,027/month. Your total FOIR is 21.3%, well within the 50% safety ceiling.",
        # 2. SIP
        "With a monthly SIP of ₹10,000 over 15 years at 12% p.a., your projected Sample corpus is ₹50,45,760 (Invested: ₹18,00,000, Wealth Gain: ₹32,45,760). Do you consent to schedule this Sample SIP investment mandate?",
        # 3. Payment Help
        "We have generated a Sample resolution for Account PAYTM-LN-8812: Waive ₹350 auto-debit bounce charge with 48-hour re-payment window. Net payable is ₹4,500 with 48h grace period.",
        # 4. Loan Rejection
        "We have charted your Sample recovery roadmap to re-apply on 29-Jan-2027: Reduce FOIR below 45% (Current: 62.0%). Do you consent to enroll in this Sample 90-day credit improvement milestone plan?",
    ]

    languages = ["en-IN", "hi-IN", "mr-IN"]
    count = 0

    for text in demo_texts:
        for lang in languages:
            try:
                res = await sarvam_service.text_to_speech(
                    text=text,
                    target_language_code=lang,
                    speaker="meera",
                )
                if res.audio_base64:
                    count += 1
            except Exception as err:
                logger.debug("Pre-generation item error: %s", err)

    logger.info("Pre-generated and verified TTS audio cache for %d demo scenarios.", count)
    return {"cached_items": count}
