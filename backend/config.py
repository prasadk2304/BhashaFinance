import os
from pathlib import Path
from pydantic import BaseModel

# Load .env if present
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass


class Settings(BaseModel):
    app_name: str = "BhashaFinance AI"
    version: str = "0.1.0"
    llm_provider: str = os.getenv("LLM_PROVIDER", "sarvam")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    llm_model: str = os.getenv("LLM_MODEL", "qwen2.5:3b")
    sarvam_api_key: str = os.getenv("SARVAM_API_KEY", "")
    sarvam_api_base_url: str = os.getenv("SARVAM_API_BASE_URL", "https://api.sarvam.ai/v1")
    sarvam_chat_model: str = os.getenv("SARVAM_CHAT_MODEL", "sarvam-30b")
    sarvam_stt_model: str = os.getenv("SARVAM_STT_MODEL", "saaras:v4")
    sarvam_tts_model: str = os.getenv("SARVAM_TTS_MODEL", "bulbul:v4-flash")
    sarvam_translate_model: str = os.getenv("SARVAM_TRANSLATE_MODEL", "mayura:v1")
    sarvam_tts_speaker: str = os.getenv("SARVAM_TTS_SPEAKER", "shubh_enhi_ads")
    default_language: str = os.getenv("DEFAULT_LANGUAGE", "mr-IN")
    db_path: str = os.getenv("DB_PATH", "bhashafinance.db")
    sample_label: str = "Sample"
    sample_disclaimer: str = (
        "Sample offer for illustrative purposes only. All calculations and figures "
        "are synthetic and non-binding."
    )


SUPPORTED_LANGUAGES = {
    "mr-IN": "मराठी",
    "hi-IN": "हिन्दी",
    "en-IN": "English",
}


settings = Settings()

