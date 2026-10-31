"""
Live testing script for Sarvam AI integration.
Used manually only when SARVAM_API_KEY is available.

Usage:
  python scripts/test_sarvam_live.py [path_to_audio.wav]
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

from backend.config import settings
from backend.sarvam import sarvam_service, SarvamUnavailable
from backend.rules.spoken_numbers import convert_amounts_in_text


def main():
    print("=" * 60)
    print("Sarvam AI Live Integration Verification Script")
    print("=" * 60)

    if not sarvam_service.is_configured:
        print("[WARNING] SARVAM_API_KEY is not configured or placeholder in .env.")
        print("Set a valid SARVAM_API_KEY in .env to run live API calls.")
        print("Configured models:")
        print(f"  STT Model:       {settings.sarvam_stt_model}")
        print(f"  TTS Model:       {settings.sarvam_tts_model}")
        print(f"  Translate Model: {settings.sarvam_translate_model}")
        print(f"  TTS Speaker:     {settings.sarvam_tts_speaker}")
        print(f"  Default Lang:    {settings.default_language}")

    # 1. Spoken amounts check
    sample_text = "तुमची ईएमआय ₹7,027 प्रति महिना आहे आणि एकूण रक्कम ₹1,50,000 आहे."
    spoken_mr = convert_amounts_in_text(sample_text, language_code="mr-IN")
    print(f"\n[1] Spoken Amounts Helper (Marathi):\n  Input:  {sample_text}\n  Output: {spoken_mr}")

    # 2. Live Text-to-Speech (TTS)
    print(f"\n[2] Testing Live TTS with model: {settings.sarvam_tts_model}, speaker: {settings.sarvam_tts_speaker}...")
    try:
        mp3_path = sarvam_service.tts(text=spoken_mr, lang="mr-IN")
        print(f"  SUCCESS: Playable MP3 generated at:\n    {mp3_path} ({mp3_path.stat().st_size} bytes)")
    except Exception as e:
        print(f"  TTS Result: {e}")

    # 3. Live Speech-to-Text (STT) - optional WAV path from argv
    print(f"\n[3] Testing Live STT with model: {settings.sarvam_stt_model}...")
    audio_path = sys.argv[1] if len(sys.argv) > 1 else None
    if audio_path and Path(audio_path).exists():
        print(f"  Transcribing file: {audio_path}")
        try:
            transcript = sarvam_service.stt(path=audio_path, lang="mr-IN")
            print(f"  SUCCESS: Transcript: {transcript}")
        except Exception as e:
            print(f"  STT Result: {e}")
    else:
        print("  No audio file provided in sys.argv[1].")
        print("  To test STT with a Marathi WAV, pass the file path:\n    python scripts/test_sarvam_live.py path/to/marathi.wav")

    # 4. Live Translation (for review/display only, never in extraction path)
    print(f"\n[4] Testing Live Translate with model: {settings.sarvam_translate_model}...")
    en_phrase = "Your loan offer has been successfully verified."
    try:
        translated = sarvam_service.translate(text=en_phrase, src="en-IN", tgt="mr-IN")
        print(f"  Source (en-IN): {en_phrase}")
        print(f"  SUCCESS: Translated (mr-IN): {translated}")
    except Exception as e:
        print(f"  Translate Result: {e}")

    print("\n" + "=" * 60)
    print("Verification completed.")
    print("=" * 60)


if __name__ == "__main__":
    main()

