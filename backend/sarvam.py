import base64
import logging
from typing import Optional
import httpx
from pydantic import BaseModel

from backend.config import settings

logger = logging.getLogger(__name__)

SARVAM_BASE_URL = "https://api.sarvam.ai"


class SttResponse(BaseModel):
    transcript: str
    language_code: Optional[str] = "en-IN"
    is_fallback: bool = False
    error: Optional[str] = None


class TtsResponse(BaseModel):
    audio_base64: Optional[str] = None
    format: str = "wav"
    is_fallback: bool = False
    error: Optional[str] = None


class SarvamService:
    def __init__(self, api_key: Optional[str] = None):
        # Keep API key strictly server-side; NEVER expose to frontend
        self.api_key = api_key or settings.sarvam_api_key

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    async def speech_to_text(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language_code: str = "unknown",
    ) -> SttResponse:
        """
        Transcribes audio using Sarvam STT API.
        Falls back gracefully to text fallback if key is missing or request fails.
        """
        if not self.is_configured:
            logger.info("Sarvam API key not configured; STT using text fallback.")
            return SttResponse(
                transcript="",
                language_code=language_code,
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
            "model": "saaras:v1",
            "language_code": language_code,
        }

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
                return SttResponse(
                    transcript=result.get("transcript", ""),
                    language_code=result.get("language_code", language_code),
                    is_fallback=False,
                )
        except Exception as e:
            logger.warning("Sarvam STT failed: %s. Falling back to text.", e)
            return SttResponse(
                transcript="",
                language_code=language_code,
                is_fallback=True,
                error=f"STT service error: {str(e)}",
            )

    async def text_to_speech(
        self,
        text: str,
        target_language_code: str = "hi-IN",
        speaker: str = "meera",
    ) -> TtsResponse:
        """
        Synthesizes text to speech using Sarvam TTS API.
        Falls back gracefully if key is missing or request fails.
        """
        if not self.is_configured:
            logger.info("Sarvam API key not configured; TTS audio skipped.")
            return TtsResponse(
                audio_base64=None,
                is_fallback=True,
                error="Sarvam API key not configured. Audio playback disabled.",
            )

        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": [text],
            "target_language_code": target_language_code,
            "speaker": speaker,
            "model": "bulbul:v1",
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
                return TtsResponse(
                    audio_base64=audio_data,
                    is_fallback=False,
                )
        except Exception as e:
            logger.warning("Sarvam TTS failed: %s.", e)
            return TtsResponse(
                audio_base64=None,
                is_fallback=True,
                error=f"TTS service error: {str(e)}",
            )


sarvam_service = SarvamService()
