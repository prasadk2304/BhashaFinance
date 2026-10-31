from backend.config import Settings


def test_uses_the_current_sarvam_v1_chat_model_by_default(monkeypatch):
    monkeypatch.delenv("SARVAM_CHAT_MODEL", raising=False)
    assert Settings().sarvam_chat_model == "sarvam-105b"
