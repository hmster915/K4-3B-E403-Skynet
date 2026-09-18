"""
Offline tests for the WAV -> chunk -> ElevenLabs -> Transcript flow.

The fake WebSocket keeps these tests deterministic and prevents API usage.
"""

import asyncio
import base64
import json
import struct
import tempfile
import wave

from array import array
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from skynet_core.providers.audio.elevenlabs import (
    CHUNK_FRAMES,
    DISCORD_SAMPLE_RATE,
    SAMPLE_RATE,
    ElevenLabsAudioProvider,
    RealtimeTranscriptionError,
)


class _FakeRealtimeSocket:

    def __init__(
        self,
        responses: list[dict[str, str]],
    ) -> None:
        self.sent_messages: list[str] = []
        self.closed = False
        self._responses = [
            json.dumps(response)
            for response in responses
        ]

    async def send(
        self,
        message: str,
    ) -> None:
        self.sent_messages.append(message)

    async def close(self) -> None:
        self.closed = True

    def __aiter__(
        self,
    ) -> "_FakeRealtimeSocket":
        return self

    async def __anext__(self) -> str:
        if not self._responses:
            raise StopAsyncIteration

        return self._responses.pop(0)


class _FakeConnector:

    def __init__(
        self,
        socket: _FakeRealtimeSocket,
    ) -> None:
        self.socket = socket
        self.url = ""
        self.headers: dict[str, str] = {}

    async def __call__(
        self,
        url: str,
        *,
        additional_headers: dict[str, str],
    ) -> _FakeRealtimeSocket:
        self.url = url
        self.headers = additional_headers
        return self.socket


def _write_pcm16_wav(
    wav_path: Path,
    *,
    channels: int,
    sample_rate: int,
    frames: int,
    frame: bytes,
) -> bytes:
    pcm = frame * frames

    with wave.open(
        str(wav_path),
        "wb",
    ) as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(pcm)

    return pcm


def _payloads(
    socket: _FakeRealtimeSocket,
) -> list[dict[str, object]]:
    return [
        json.loads(message)
        for message in socket.sent_messages
    ]


@pytest.fixture
def audio_tmp_path() -> Iterator[Path]:
    with tempfile.TemporaryDirectory(
        prefix="skynet-audio-tests-",
    ) as directory:
        yield Path(directory)


def test_transcribe_discord_wav_normalizes_and_chunks(
    audio_tmp_path: Path,
) -> None:
    wav_path = (
        audio_tmp_path
        / "discord_voice.wav"
    )

    # 10.25 seconds creates 20 full 0.5-second chunks and
    # one final half chunk after conversion to mono 16 kHz.
    discord_frames = (
        DISCORD_SAMPLE_RATE * 10
        + DISCORD_SAMPLE_RATE // 4
    )

    _write_pcm16_wav(
        wav_path,
        channels=2,
        sample_rate=DISCORD_SAMPLE_RATE,
        frames=discord_frames,
        frame=struct.pack(
            "<hh",
            1000,
            -200,
        ),
    )

    socket = _FakeRealtimeSocket(
        [
            {
                "message_type": "session_started",
            },
            {
                "message_type": "partial_transcript",
                "text": "đoạn",
            },
            {
                "message_type": "committed_transcript",
                "text": "đoạn một",
            },
            {
                "message_type": "committed_transcript",
                "text": "đoạn hai",
            },
        ]
    )
    connector = _FakeConnector(socket)
    provider = ElevenLabsAudioProvider(
        api_key="test-api-key",
        connector=connector,
    )

    transcript = asyncio.run(
        provider.transcribe_wav(
            wav_path
        )
    )

    assert transcript.text == (
        "đoạn một\nđoạn hai"
    )
    assert socket.closed
    assert connector.headers == {
        "xi-api-key": "test-api-key",
    }

    query = parse_qs(
        urlsplit(connector.url).query
    )
    assert query["audio_format"] == [
        "pcm_16000"
    ]

    payloads = _payloads(socket)
    audio_payloads = [
        payload
        for payload in payloads
        if not payload["commit"]
    ]
    commit_payloads = [
        payload
        for payload in payloads
        if payload["commit"]
    ]

    assert len(audio_payloads) == 21
    assert len(commit_payloads) == 2
    assert [
        payload["commit"]
        for payload in payloads
    ] == (
        [False] * 20
        + [True, False, True]
    )
    assert all(
        payload["sample_rate"]
        == SAMPLE_RATE
        for payload in payloads
    )

    chunk_sizes = [
        len(
            base64.b64decode(
                str(payload["audio_base_64"])
            )
        )
        for payload in audio_payloads
    ]
    assert chunk_sizes == (
        [CHUNK_FRAMES * 2] * 20
        + [CHUNK_FRAMES]
    )

    first_chunk = array("h")
    first_chunk.frombytes(
        base64.b64decode(
            str(
                audio_payloads[0][
                    "audio_base_64"
                ]
            )
        )
    )

    # Stereo (1000, -200) is downmixed to mono 400.
    assert set(first_chunk) == {400}


def test_transcribe_mono_16k_keeps_pcm_bytes(
    audio_tmp_path: Path,
) -> None:
    wav_path = (
        audio_tmp_path
        / "ready_for_stt.wav"
    )
    source_pcm = _write_pcm16_wav(
        wav_path,
        channels=1,
        sample_rate=SAMPLE_RATE,
        frames=SAMPLE_RATE // 4,
        frame=struct.pack("<h", 321),
    )

    socket = _FakeRealtimeSocket(
        [
            {
                "message_type": "committed_transcript",
                "text": "xin chào",
            },
        ]
    )
    provider = ElevenLabsAudioProvider(
        api_key="test-api-key",
        connector=_FakeConnector(socket),
    )

    transcript = asyncio.run(
        provider.transcribe_wav(
            wav_path
        )
    )

    audio_payload = _payloads(socket)[0]
    sent_pcm = base64.b64decode(
        str(audio_payload["audio_base_64"])
    )

    assert sent_pcm == source_pcm
    assert transcript.text == "xin chào"


def test_transcribe_wav_rejects_raw_discord_opus(
    audio_tmp_path: Path,
) -> None:
    opus_path = (
        audio_tmp_path
        / "discord_packet.opus"
    )
    opus_path.write_bytes(b"not-a-wav")

    socket = _FakeRealtimeSocket([])
    provider = ElevenLabsAudioProvider(
        api_key="test-api-key",
        connector=_FakeConnector(socket),
    )

    with pytest.raises(
        ValueError,
        match="decoded to PCM16 WAV",
    ):
        asyncio.run(
            provider.transcribe_wav(
                opus_path
            )
        )

    assert not socket.sent_messages
    assert not socket.closed


def test_transcribe_wav_closes_socket_on_provider_error(
    audio_tmp_path: Path,
) -> None:
    wav_path = (
        audio_tmp_path
        / "provider_error.wav"
    )
    _write_pcm16_wav(
        wav_path,
        channels=1,
        sample_rate=SAMPLE_RATE,
        frames=SAMPLE_RATE,
        frame=struct.pack("<h", 100),
    )

    socket = _FakeRealtimeSocket(
        [
            {
                "message_type": "input_error",
                "error": "invalid audio",
            },
        ]
    )
    provider = ElevenLabsAudioProvider(
        api_key="test-api-key",
        connector=_FakeConnector(socket),
    )

    with pytest.raises(
        RealtimeTranscriptionError,
        match="invalid audio",
    ):
        asyncio.run(
            provider.transcribe_wav(
                wav_path
            )
        )

    assert socket.closed
