"""
_get_test_wav()          --> lấy WAV test
_print_wav_info()        --> in format WAV
_run_realtime_test()     --> gọi STT provider
test_realtime_stt_wav()  --> integration test
"""

import asyncio
import os
import wave

from pathlib import Path

from dotenv import load_dotenv

from skynet_core.models.transcript import Transcript
from skynet_core.providers.audio import (
    ElevenLabsAudioProvider,
)


CODEBASE_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(
    CODEBASE_ROOT / ".env"
)

DEFAULT_TEST_WAV = (
    Path(__file__).resolve().parent
    / "973234901300158564.wav"
)


# Preflight: Role=resolve WAV test | Input=env/default path | Output=existing WAV path | Decision boundary=path only | Failure/Test=file missing
def _get_test_wav() -> Path:
    custom_path = os.getenv(
        "TEST_WAV_PATH"
    )

    wav_path = (
        Path(custom_path)
        if custom_path
        else DEFAULT_TEST_WAV
    )

    if not wav_path.is_file():
        raise FileNotFoundError(
            f"WAV test file not found: {wav_path}"
        )

    return wav_path


# Preflight: Role=show WAV metadata | Input=WAV path | Output=None | Decision boundary=debug info only | Failure/Test=invalid WAV
def _print_wav_info(
    wav_path: Path,
) -> None:
    with wave.open(
        str(wav_path),
        "rb",
    ) as audio:
        print(
            "\nWAV INPUT"
            f"\nchannels    = {audio.getnchannels()}"
            f"\nsample_rate = {audio.getframerate()}"
            f"\nsample_width= {audio.getsampwidth() * 8} bit"
        )


# Preflight: Role=run realtime STT | Input=WAV + API key | Output=Transcript | Decision boundary=STT only, no LLM | Failure/Test=auth/network/provider error
async def _run_realtime_test() -> Transcript:
    api_key = (
        os.getenv(
            "ELEVENLABS_API_KEY"
        )
        or ""
    ).strip()

    if not api_key:
        raise ValueError(
            "ELEVENLABS_API_KEY not found in codebase/.env"
        )

    wav_path = _get_test_wav()

    _print_wav_info(
        wav_path
    )

    provider = ElevenLabsAudioProvider(
        api_key=api_key,
    )

    return await provider.transcribe_wav(
        wav_path
    )


# Preflight: Role=pytest integration entry | Input=test WAV | Output=non-empty transcript | Decision boundary=no LLM | Failure/Test=empty transcript
def test_realtime_stt_wav() -> None:
    transcript = asyncio.run(
        _run_realtime_test()
    )

    print(
        "\n"
        "==============================\n"
        "FULL TRANSCRIPT\n"
        "=============================="
    )

    print(
        transcript.text
    )

    assert transcript.text.strip()