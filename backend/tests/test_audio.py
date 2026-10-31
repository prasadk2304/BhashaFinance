from pathlib import Path

import backend.audio as audio


def test_resolve_media_binary_uses_configured_ffmpeg_path(monkeypatch, tmp_path):
    binary = tmp_path / "ffmpeg.exe"
    binary.write_bytes(b"test binary")
    monkeypatch.setenv("FFMPEG_BIN", str(binary))

    assert audio.resolve_media_binary("ffmpeg") == str(binary)


def test_resolve_media_binary_keeps_explicit_path_when_it_cannot_be_inspected(monkeypatch):
    configured_path = r"C:\restricted\ffmpeg.exe"
    monkeypatch.setenv("FFMPEG_BIN", configured_path)
    monkeypatch.setattr(audio.Path, "is_file", lambda _: (_ for _ in ()).throw(PermissionError("access denied")))

    assert audio.resolve_media_binary("ffmpeg") == configured_path


def test_resolve_media_binary_ignores_an_unreadable_winget_directory(monkeypatch):
    monkeypatch.delenv("FFMPEG_BIN", raising=False)
    monkeypatch.setattr(audio.shutil, "which", lambda _: None)
    monkeypatch.setattr(
        audio.Path,
        "glob",
        lambda self, pattern: (_ for _ in ()).throw(PermissionError("access denied")),
    )

    assert audio.resolve_media_binary("ffmpeg") is None

