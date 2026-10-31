"""
Audio conversion and validation utilities for BhashaFinance AI.
Converts any uploaded browser audio (webm/ogg/mp4) to 16 kHz mono WAV with ffmpeg via subprocess.
Enforces:
- 10 MB maximum upload limit
- 30 seconds maximum duration limit
"""

import logging
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Optional, Union
import wave

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_DURATION_SECONDS = 30.0  # 30 seconds


def resolve_media_binary(name: str) -> Optional[str]:
    """Find an FFmpeg executable from PATH, explicit config, or WinGet.

    Windows installs Gyan.FFmpeg under the user's WinGet package directory,
    which is not always inherited by a process started from a desktop app.
    """
    configured_name = "FFMPEG_BIN" if name == "ffmpeg" else "FFPROBE_BIN"
    configured_path = os.getenv(configured_name)
    if configured_path:
        try:
            if Path(configured_path).is_file():
                return configured_path
        except OSError:
            # A process can be allowed to execute the configured binary even
            # when this sandboxed probe cannot inspect its parent directory.
            return configured_path

    on_path = shutil.which(name)
    if on_path:
        return on_path

    if os.name == "nt":
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
            executable = f"{name}.exe"
            try:
                for candidate in packages.glob(f"Gyan.FFmpeg_*/ffmpeg-*/bin/{executable}"):
                    if candidate.is_file():
                        return str(candidate)
            except OSError:
                logger.debug("Unable to inspect the WinGet FFmpeg directory.")

    return None


def check_ffmpeg_exists() -> bool:
    """Checks whether ffmpeg is available to this server process."""
    return resolve_media_binary("ffmpeg") is not None


def check_ffprobe_exists() -> bool:
    """Checks whether ffprobe is available to this server process."""
    return resolve_media_binary("ffprobe") is not None


def verify_ffmpeg_on_startup() -> bool:
    """
    Invoked on application startup.
    Prints a clear install message if ffmpeg is missing.
    """
    installed = check_ffmpeg_exists()
    if not installed:
        msg = (
            "FFmpeg is not installed or not found on PATH.\n"
            "To convert browser audio (webm/ogg/mp4) to 16 kHz mono WAV, please install FFmpeg:\n"
            "  Windows: winget install ffmpeg\n"
            "  macOS:   brew install ffmpeg\n"
            "  Linux:   sudo apt install ffmpeg"
        )
        print(f"\n[AUDIO WARNING] {msg}\n")
        logger.warning(msg)
    return installed


def get_audio_duration_seconds(file_path: Union[str, Path]) -> Optional[float]:
    """
    Returns duration of audio file in seconds.
    Tries standard library wave first for WAV files, falls back to ffprobe.
    """
    path = Path(file_path)
    # Check if standard WAV
    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return frames / float(rate)
    except Exception:
        pass

    # Use ffprobe if available
    if check_ffprobe_exists():
        try:
            cmd = [
                resolve_media_binary("ffprobe") or "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                return float(res.stdout.strip())
        except Exception:
            pass

    return None


def convert_to_16k_mono_wav(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
) -> Path:
    """
    Converts input audio file (webm, ogg, mp4, wav) to 16 kHz mono PCM WAV.
    Enforces 10 MB upload limit and 30s max duration.
    """
    in_path = Path(input_path)
    if not in_path.exists():
        raise FileNotFoundError(f"Input audio file not found: {in_path}")

    file_size = in_path.stat().st_size
    if file_size > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"Audio upload size ({file_size / (1024 * 1024):.1f} MB) exceeds maximum limit of 10 MB."
        )

    # Check duration if determinable
    duration = get_audio_duration_seconds(in_path)
    if duration is not None and duration > MAX_DURATION_SECONDS:
        raise ValueError(
            f"Audio duration ({duration:.1f}s) exceeds maximum allowed limit of {MAX_DURATION_SECONDS:.0f} seconds."
        )

    if output_path is None:
        fd, temp_out = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        out_path = Path(temp_out)
    else:
        out_path = Path(output_path)

    if not check_ffmpeg_exists():
        # Fallback: if already a WAV file, check if it meets or can be used
        try:
            with wave.open(str(in_path), "rb") as wf:
                channels = wf.getnchannels()
                rate = wf.getframerate()
                # If already mono and 16k, copy directly
                if channels == 1 and rate == 16000:
                    shutil.copyfile(str(in_path), str(out_path))
                    return out_path
                else:
                    shutil.copyfile(str(in_path), str(out_path))
                    return out_path
        except Exception:
            raise RuntimeError(
                "FFmpeg is required to convert browser audio formats. "
                "Install via: winget install ffmpeg"
            )

    # Run ffmpeg to convert to 16 kHz mono WAV, max 30s duration
    cmd = [
        resolve_media_binary("ffmpeg") or "ffmpeg",
        "-y",
        "-i", str(in_path),
        "-ac", "1",
        "-ar", "16000",
        "-t", str(int(MAX_DURATION_SECONDS)),
        "-f", "wav",
        str(out_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg conversion failed: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg audio conversion timed out.")

    return out_path

