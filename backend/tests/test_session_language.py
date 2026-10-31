from pathlib import Path

import httpx
import pytest

from backend.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
@pytest.mark.parametrize("language_code", ["hi-IN", "mr-IN"])
async def test_session_tts_uses_session_language_for_initial_and_followup_reply(monkeypatch, tmp_path, language_code):
    import backend.main as main
    from backend.llm.base import ExtractionResult

    spoken_languages: list[str] = []
    translation_targets: list[str] = []
    audio_file = Path(tmp_path / "reply.mp3")
    audio_file.write_bytes(b"sample audio")

    def capture_tts(*, text, lang):
        spoken_languages.append(lang)
        return audio_file

    def capture_translation(text, src, tgt):
        translation_targets.append(tgt)
        return f"{tgt} translated reply"

    async def no_llm_extraction(**_):
        return ExtractionResult()

    monkeypatch.setattr(main.sarvam_service, "tts", capture_tts)
    monkeypatch.setattr(main.sarvam_service, "translate", capture_translation)
    monkeypatch.setattr(main.llm_service, "extract_with_fallback", no_llm_extraction)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/sessions", json={"journey_id": "personal_loan", "language_code": language_code})
        session_id = created.json()["session_id"]
        followup = await client.post(f"/sessions/{session_id}/turns", json={"text": "80000"})

    assert created.status_code == 200
    assert created.json()["state"]["language_code"] == language_code
    assert followup.status_code == 200
    assert spoken_languages == [language_code, language_code]
    assert translation_targets == [language_code, language_code]

