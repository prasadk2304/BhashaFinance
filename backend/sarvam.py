"""
Sarvam AI voice and language service for BhashaFinance AI.
Uses the official `sarvamai` SDK:
- STT (speech_to_text.transcribe) with model from SARVAM_STT_MODEL (default saaras:v4)
- TTS (text_to_speech.convert_stream) with model from SARVAM_TTS_MODEL (default bulbul:v4-flash)
- Translation (text.translate) with model from SARVAM_TRANSLATE_MODEL (default mayura:v1)
- Disk caching in backend/cache/ by sha256(text|lang|speaker|model)
- Strict security: Never logs audio, transcripts, or API keys.
"""

import base64
import hashlib
import json
import logging
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Dict, Iterator, Optional, Union
from pydantic import BaseModel

try:
    from sarvamai import SarvamAI
except ImportError:
    SarvamAI = None

from backend.config import settings
from backend.rules.spoken_numbers import convert_amounts_in_text

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class SarvamUnavailable(Exception):
    """Raised when Sarvam AI service fails, times out, or is unavailable after retries."""
    pass


class SttResponse(BaseModel):
    transcript: str
    language_code: Optional[str] = "en-IN"
    is_fallback: bool = False
    error: Optional[str] = None
    needs_confirmation: bool = False
    detected_language: Optional[str] = None
    confirmation_prompt: Optional[str] = None

    def __getitem__(self, item: str):
        return getattr(self, item)


class TtsResponse(BaseModel):
    audio_base64: Optional[str] = None
    file_path: Optional[str] = None
    format: str = "mp3"
    is_fallback: bool = False
    error: Optional[str] = None
    cached: bool = False
    spoken_text: Optional[str] = None

    def __getitem__(self, item: str):
        return getattr(self, item)


def generate_mock_wav_base64() -> str:
    """
    Generates a minimal valid 44-byte PCM WAV header for synthetic playback
    in offline/test environments when Sarvam API is unreachable.
    """
    wav_header = (
        b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )
    return base64.b64encode(wav_header).decode("ascii")


class SarvamService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        stt_model: Optional[str] = None,
        tts_model: Optional[str] = None,
        translate_model: Optional[str] = None,
        speaker: Optional[str] = None,
        default_language: Optional[str] = None,
    ):
        self.api_key = api_key or settings.sarvam_api_key
        self.stt_model = stt_model or settings.sarvam_stt_model
        self.tts_model = tts_model or settings.sarvam_tts_model
        self.translate_model = translate_model or settings.sarvam_translate_model
        self.speaker = speaker or settings.sarvam_tts_speaker
        self.default_language = default_language or settings.default_language
        self._client = None

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def get_client(self):
        """Returns initialized SarvamAI client or raises SarvamUnavailable."""
        if not self.is_configured:
            raise SarvamUnavailable("Sarvam API key is not configured.")
        if self._client is None:
            if SarvamAI is None:
                raise SarvamUnavailable("sarvamai SDK is not installed.")
            self._client = SarvamAI(api_subscription_key=self.api_key)
        return self._client

    def set_client(self, client: Any):
        """Allows injecting a mocked client for testing."""
        self._client = client

    def get_tts_cache_key(self, text: str, lang: str, speaker: str, model: str) -> str:
        raw_key = f"{text.strip()}|{lang.strip()}|{speaker.strip()}|{model.strip()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def stt(self, path: Union[str, Path], lang: Optional[str] = None) -> str:
        """
        Transcribes audio file at path using Sarvam Speech-to-Text SDK.
        client.speech_to_text.transcribe(file=f, model=STT_MODEL, language_code=lang, mode="transcribe", sample_rate=16000)
        Returns response.transcript.
        Rule: Timeout, one retry, then raise SarvamUnavailable. Never log audio, transcripts, or keys.
        """
        target_lang = lang or self.default_language
        client = self.get_client()

        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        last_err = None
        for attempt in range(2):
            try:
                with open(file_path, "rb") as f:
                    # Support both SDK argument styles (sample_rate if supported)
                    try:
                        response = client.speech_to_text.transcribe(
                            file=f,
                            model=self.stt_model,
                            language_code=target_lang,
                            mode="transcribe",
                            sample_rate=16000,
                        )
                    except TypeError:
                        f.seek(0)
                        response = client.speech_to_text.transcribe(
                            file=f,
                            model=self.stt_model,
                            language_code=target_lang,
                            mode="transcribe",
                        )

                # Extract transcript safely from response
                transcript = getattr(response, "transcript", None)
                if transcript is None and isinstance(response, dict):
                    transcript = response.get("transcript")
                if transcript is not None:
                    return str(transcript).strip()

                raise ValueError("Response missing transcript field")
            except Exception as e:
                last_err = e
                # Security: NEVER log transcripts, audio, or keys!
                logger.warning("Sarvam STT attempt %d failed (%s)", attempt + 1, type(e).__name__)
                if attempt == 0:
                    time.sleep(0.5)
                    continue

        raise SarvamUnavailable(f"Sarvam STT failed after 1 retry: {type(last_err).__name__}")

    def tts(self, text: str, lang: Optional[str] = None) -> Path:
        """
        Synthesizes text to speech using Sarvam Text-to-Speech SDK.
        client.text_to_speech.convert_stream(text=..., target_language_code=lang, speaker=SPEAKER, model=TTS_MODEL, pace=1, speech_sample_rate=24000)
        Handles both bytes and iterator-of-bytes responses.
        Caches by sha256(text|lang|speaker|model) in backend/cache/ and returns the cached file if it exists.
        Returns path to .mp3 file.
        Rule: Timeout, one retry, then raise SarvamUnavailable. Never log audio, transcripts, or keys.
        """
        if not text:
            raise ValueError("Text cannot be empty for TTS.")

        target_lang = lang or self.default_language
        # 1. Check disk cache first: return immediately if present
        cache_key = self.get_tts_cache_key(text, target_lang, self.speaker, self.tts_model)
        cache_file = CACHE_DIR / f"{cache_key}.mp3"

        if cache_file.exists() and cache_file.stat().st_size > 0:
            return cache_file

        client = self.get_client()
        last_err = None

        for attempt in range(2):
            try:
                # Handle target_language_code vs language_code parameter
                try:
                    res = client.text_to_speech.convert_stream(
                        text=text,
                        target_language_code=target_lang,
                        speaker=self.speaker,
                        model=self.tts_model,
                        pace=1,
                        speech_sample_rate=24000,
                    )
                except TypeError:
                    res = client.text_to_speech.convert_stream(
                        text=text,
                        language_code=target_lang,
                        speaker=self.speaker,
                        model=self.tts_model,
                        pace=1,
                        speech_sample_rate=24000,
                    )

                # Handle both bytes and iterator-of-bytes responses
                if isinstance(res, (bytes, bytearray)):
                    audio_bytes = bytes(res)
                elif hasattr(res, "__iter__"):
                    audio_bytes = b"".join(res)
                else:
                    audio_bytes = bytes(res)

                if not audio_bytes:
                    raise ValueError("Received empty audio stream from TTS.")

                # Persist to disk cache
                cache_file.write_bytes(audio_bytes)
                return cache_file

            except Exception as e:
                last_err = e
                # Security: NEVER log text, audio, or keys!
                logger.warning("Sarvam TTS attempt %d failed (%s)", attempt + 1, type(e).__name__)
                if attempt == 0:
                    time.sleep(0.5)
                    continue

        raise SarvamUnavailable(f"Sarvam TTS failed after 1 retry: {type(last_err).__name__}")

    def translate(self, text: str, src: str, tgt: str) -> str:
        """
        Translates text from src language to tgt language using Sarvam Translation SDK.
        client.text.translate(input=..., source_language_code=..., target_language_code=..., model=TRANSLATE_MODEL, numerals_format="international", mode="formal")
        Rule: Use it ONLY for display text (review screen), NEVER in the extraction path.
        Rule: Timeout, one retry, then raise SarvamUnavailable. Never log audio, transcripts, or keys.
        """
        if not text:
            return ""

        if src == tgt:
            return text

        client = self.get_client()
        last_err = None

        for attempt in range(2):
            try:
                response = client.text.translate(
                    input=text,
                    source_language_code=src,
                    target_language_code=tgt,
                    model=self.translate_model,
                    numerals_format="international",
                    mode="formal",
                )

                translated = getattr(response, "translated_text", None)
                if translated is None and isinstance(response, dict):
                    translated = response.get("translated_text")
                if translated is not None:
                    return str(translated).strip()

                raise ValueError("Response missing translated_text")

            except Exception as e:
                last_err = e
                # Security: NEVER log text or keys!
                logger.warning("Sarvam translate attempt %d failed (%s)", attempt + 1, type(e).__name__)
                if attempt == 0:
                    time.sleep(0.5)
                    continue

        raise SarvamUnavailable(f"Sarvam translate failed after 1 retry: {type(last_err).__name__}")

    # --------------------------------------------------------------------------
    # Backward-Compatible Helper Methods for Turns
    # --------------------------------------------------------------------------

    async def speech_to_text(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language_code: str = "mr-IN",
    ) -> SttResponse:
        """
        Convenience wrapper that converts audio bytes to tempfile and runs stt().
        Returns SttResponse with transcript and language_code.
        """
        if not self.is_configured:
            return SttResponse(
                transcript="",
                language_code=language_code,
                is_fallback=True,
                error="Sarvam API key not configured. Please use text input fallback.",
            )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = Path(tmp.name)

        try:
            transcript = self.stt(path=tmp_path, lang=language_code)
            return SttResponse(
                transcript=transcript,
                language_code=language_code,
                is_fallback=False,
            )
        except SarvamUnavailable as err:
            return SttResponse(
                transcript="",
                language_code=language_code,
                is_fallback=True,
                error=str(err),
            )
        finally:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass

    async def text_to_speech(
        self,
        text: str,
        target_language_code: str = "mr-IN",
        speaker: Optional[str] = None,
    ) -> TtsResponse:
        """
        Convenience wrapper that converts amounts to words and calls tts().
        Returns TtsResponse with audio_base64 and cached path.
        """
        if not text:
            return TtsResponse(audio_base64=None, is_fallback=True, error="Empty text")

        spk = speaker or self.speaker
        spoken_text = convert_amounts_in_text(text, language_code=target_language_code)
        cache_key = self.get_tts_cache_key(spoken_text, target_language_code, spk, self.tts_model)
        json_cache = CACHE_DIR / f"{cache_key}.json"

        # Check JSON cache
        if json_cache.exists():
            try:
                data = json.loads(json_cache.read_text(encoding="utf-8"))
                return TtsResponse(
                    audio_base64=data.get("audio_base64"),
                    file_path=data.get("file_path"),
                    format="mp3",
                    is_fallback=data.get("is_fallback", False),
                    cached=True,
                    spoken_text=spoken_text,
                )
            except Exception:
                pass

        if not self.is_configured:
            mock_audio = generate_mock_wav_base64()
            try:
                json_cache.write_text(
                    json.dumps({
                        "audio_base64": mock_audio,
                        "file_path": None,
                        "is_fallback": True,
                        "spoken_text": spoken_text,
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
            )

        try:
            mp3_path = self.tts(text=spoken_text, lang=target_language_code)
            audio_bytes = mp3_path.read_bytes()
            b64_audio = base64.b64encode(audio_bytes).decode("ascii")
            try:
                json_cache.write_text(
                    json.dumps({
                        "audio_base64": b64_audio,
                        "file_path": str(mp3_path),
                        "is_fallback": False,
                        "spoken_text": spoken_text,
                    }),
                    encoding="utf-8",
                )
            except Exception:
                pass
            return TtsResponse(
                audio_base64=b64_audio,
                file_path=str(mp3_path),
                format="mp3",
                is_fallback=False,
                cached=True,
                spoken_text=spoken_text,
            )
        except SarvamUnavailable as err:
            logger.warning("TTS unavailable: %s", err)
            return TtsResponse(
                audio_base64=None,
                is_fallback=True,
                error=str(err),
                spoken_text=spoken_text,
            )


sarvam_service = SarvamService()


async def pregenerate_demo_audio() -> Dict[str, Any]:
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
                )
                if res.audio_base64:
                    count += 1
            except Exception as err:
                logger.debug("Pre-generation item error: %s", err)

    logger.info("Pre-generated and verified TTS audio cache for %d demo scenarios.", count)
    return {"cached_items": count}
