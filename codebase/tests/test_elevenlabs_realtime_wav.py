"""
_validate_wav()          --> kiểm tra WAV đầu vào
_stream_wav_realtime()   --> chia WAV thành chunk và gửi realtime
_collect_transcript()    --> nhận committed transcript
_run_realtime_test()     --> chạy full integration test
test_realtime_stt_wav()  --> pytest entrypoint
"""

import asyncio
import os
import wave

from pathlib import Path

from skynet_core.models.transcript import (
    RealtimeTranscriptEventType,
)

from skynet_core.providers.audio.elevenlabs import (
    ElevenLabsAudioProvider,
    ElevenLabsRealtimeSession,
)


CHUNK_SECONDS = 0.5
FINAL_SILENCE_SECONDS = 2.0

TEST_WAV_PATH = Path(
    os.getenv(
        "TEST_WAV_PATH",
        "tests/973234901300158564.wav",
    )
)


# Preflight: Role=validate test WAV | Input=WAV path | Output=audio format | Decision boundary=validation only | Failure/Test=missing/wrong WAV format
def _validate_wav(
    wav_path: Path,
) -> tuple[int, int, int]:

    if not wav_path.is_file():
        raise FileNotFoundError(
            f"WAV file not found: {wav_path}"
        )

    with wave.open(
        str(wav_path),
        "rb",
    ) as audio:

        channels = audio.getnchannels()
        sample_width = audio.getsampwidth()
        sample_rate = audio.getframerate()

    if channels != 1:
        raise ValueError(
            "Test WAV must be mono"
        )

    if sample_width != 2:
        raise ValueError(
            "Test WAV must be PCM 16-bit"
        )

    if sample_rate != 16000:
        raise ValueError(
            "Test WAV must be 16000 Hz"
        )

    return (
        channels,
        sample_width,
        sample_rate,
    )


# Preflight: Role=simulate realtime audio | Input=WAV + STT session | Output=None | Decision boundary=audio transport only | Failure/Test=invalid file/provider failure
async def _stream_wav_realtime(
    session: ElevenLabsRealtimeSession,
    wav_path: Path,
) -> None:

    (
        channels,
        sample_width,
        sample_rate,
    ) = _validate_wav(
        wav_path
    )

    frames_per_chunk = int(
        sample_rate * CHUNK_SECONDS
    )

    with wave.open(
        str(wav_path),
        "rb",
    ) as audio:

        while True:
            chunk = audio.readframes(
                frames_per_chunk
            )

            if not chunk:
                break

            await session.send_chunk(
                chunk
            )

            # Giả lập audio đến theo thời gian thật.
            await asyncio.sleep(
                CHUNK_SECONDS
            )

    # Gửi silence cuối để VAD nhận ra người nói đã dừng.
    silence_chunk = (
        b"\x00"
        * frames_per_chunk
        * channels
        * sample_width
    )

    silence_chunks = int(
        FINAL_SILENCE_SECONDS
        / CHUNK_SECONDS
    )

    for _ in range(
        silence_chunks
    ):
        await session.send_chunk(
            silence_chunk
        )

        await asyncio.sleep(
            CHUNK_SECONDS
        )


# Preflight: Role=collect confirmed STT | Input=realtime events | Output=committed text list | Decision boundary=ignore partial/final; no LLM | Failure/Test=provider stream failure
async def _collect_transcript(
    session: ElevenLabsRealtimeSession,
    parts: list[str],
) -> None:

    committed_types = {
        RealtimeTranscriptEventType.COMMITTED,
        RealtimeTranscriptEventType.COMMITTED_WITH_TIMESTAMPS,
    }

    async for event in session.events():

        if (
            event.event_type
            not in committed_types
        ):
            continue

        text = (
            event.text or ""
        ).strip()

        if not text:
            continue

        # include_timestamps có thể tạo event
        # chứa cùng text ngay sau committed event.
        if (
            parts
            and parts[-1] == text
        ):
            continue

        parts.append(text)

        print(
            f"[COMMITTED] {text}"
        )


# Preflight: Role=run realtime STT integration | Input=WAV path/API key | Output=full transcript | Decision boundary=STT only | Failure/Test=no transcript/network/auth error
async def _run_realtime_test() -> str:

    api_key = (
        os.getenv(
            "ELEVENLABS_API_KEY"
        )
        or ""
    ).strip()

    if not api_key:
        raise ValueError(
            "ELEVENLABS_API_KEY is required"
        )

    provider = ElevenLabsAudioProvider(
        api_key=api_key
    )

    session = await provider.connect()

    parts: list[str] = []

    collector_task = (
        asyncio.create_task(
            _collect_transcript(
                session,
                parts,
            )
        )
    )

    try:
        await _stream_wav_realtime(
            session,
            TEST_WAV_PATH,
        )

        # Chờ ElevenLabs trả nốt event cuối.
        await asyncio.sleep(2)

    finally:
        await session.close()

        await asyncio.wait_for(
            collector_task,
            timeout=5,
        )

    if not parts:
        raise AssertionError(
            "No committed transcript received"
        )

    return "\n".join(parts)


# Preflight: Role=pytest integration entry | Input=test WAV | Output=assert transcript | Decision boundary=no LLM | Failure/Test=empty STT result
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

    print(transcript)

    assert transcript.strip()