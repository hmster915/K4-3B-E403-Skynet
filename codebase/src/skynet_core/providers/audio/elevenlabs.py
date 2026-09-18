"""
__init__()              --> cấu hình ElevenLabs
transcribe_wav()        --> WAV -> Transcript
_validate_wav()         --> kiểm tra PCM16 WAV hỗ trợ
_iter_pcm16_chunks()    --> chuẩn hóa Discord WAV + chia chunk
_build_websocket_url()  --> tạo realtime URL
_send_chunk()           --> gửi audio chunk
_commit()               --> chốt audio segment
_wait_for_transcript()  --> nhận committed transcript
_parse_message()        --> đọc provider response
"""

import base64
import json
import os
import sys
import wave

from array import array
from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
)

from pathlib import Path
from typing import Protocol

from urllib.parse import (
    urlencode,
    urlsplit,
    urlunsplit,
)

import websockets

from skynet_core.models.transcript import Transcript
from skynet_core.providers.audio.buffer import TranscriptBuffer


DEFAULT_BASE_URL = "https://api.elevenlabs.io"
DEFAULT_MODEL_ID = "scribe_v2_realtime"

SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2
CHANNELS = 1

# Discord voice dùng Opus 48 kHz stereo. Bot/voice adapter cần
# giải mã Opus thành WAV PCM16 trước khi gọi transcribe_wav().
DISCORD_SAMPLE_RATE = 48000
SUPPORTED_CHANNELS = {CHANNELS, 2}
SUPPORTED_SAMPLE_RATES = {
    SAMPLE_RATE,
    DISCORD_SAMPLE_RATE,
}

# gửi 0.5 giây audio mỗi lần
CHUNK_FRAMES = 8000

# commit sau khoảng 10 giây
CHUNKS_PER_COMMIT = 20


ERROR_EVENTS = {
    "error",
    "auth_error",
    "quota_exceeded",
    "transcriber_error",
    "rate_limited",
    "input_error",
    "invalid_request",
    "resource_exhausted",
    "commit_throttled",
    "unaccepted_terms",
    "queue_overflow",
    "session_time_limit_exceeded",
    "chunk_size_exceeded",
    "insufficient_audio_activity",
}


class RealtimeSocket(Protocol):

    async def send(
        self,
        message: str,
    ) -> None:
        ...

    async def close(self) -> None:
        ...

    def __aiter__(
        self,
    ) -> AsyncIterator[str | bytes]:
        ...


WebSocketConnector = Callable[
    ...,
    Awaitable[RealtimeSocket],
]


class RealtimeTranscriptionError(
    RuntimeError
):
    pass


class ElevenLabsAudioProvider:

    # Preflight: Role=configure ElevenLabs STT | Input=API config | Output=provider | Decision boundary=config only | Failure/Test=missing API key
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        connector: WebSocketConnector | None = None,
    ) -> None:

        self._api_key = (
            api_key
            or os.getenv("ELEVENLABS_API_KEY")
            or ""
        ).strip()

        if not self._api_key:
            raise ValueError(
                "ELEVENLABS_API_KEY is required"
            )

        self._base_url = (
            base_url
            or os.getenv("ELEVENLABS_BASE_URL")
            or DEFAULT_BASE_URL
        ).rstrip("/")

        self._connector = (
            connector
            or websockets.connect
        )

    # Preflight: Role=transcribe WAV meeting | Input=PCM16 WAV (mono/stereo, 16k/48k) | Output=Transcript | Decision boundary=normalize + STT only, no LLM | Failure/Test=invalid WAV/network/provider failure
    async def transcribe_wav(
        self,
        wav_path: Path,
    ) -> Transcript:

        self._validate_wav(wav_path)

        websocket = await self._connector(
            self._build_websocket_url(),
            additional_headers={
                "xi-api-key": self._api_key,
            },
        )

        buffer = TranscriptBuffer()

        try:
            with wave.open(
                str(wav_path),
                "rb",
            ) as audio:

                chunks_since_commit = 0

                for chunk in (
                    self._iter_pcm16_chunks(
                        audio
                    )
                ):

                    await self._send_chunk(
                        websocket,
                        chunk,
                    )

                    chunks_since_commit += 1

                    if (
                        chunks_since_commit
                        >= CHUNKS_PER_COMMIT
                    ):
                        await self._commit(
                            websocket
                        )

                        text = (
                            await self
                            ._wait_for_transcript(
                                websocket
                            )
                        )

                        buffer.add(text)

                        chunks_since_commit = 0

                if chunks_since_commit > 0:
                    await self._commit(
                        websocket
                    )

                    text = (
                        await self
                        ._wait_for_transcript(
                            websocket
                        )
                    )

                    buffer.add(text)

        finally:
            await websocket.close()

        return buffer.build()

    # Preflight: Role=validate WAV contract | Input=file path | Output=None | Decision boundary=accept ElevenLabs/decoded Discord PCM only | Failure/Test=missing/wrong format
    @staticmethod
    def _validate_wav(
        wav_path: Path,
    ) -> None:

        if not wav_path.is_file():
            raise FileNotFoundError(
                f"WAV not found: {wav_path}"
            )

        try:
            with wave.open(
                str(wav_path),
                "rb",
            ) as audio:

                if (
                    audio.getnchannels()
                    not in SUPPORTED_CHANNELS
                ):
                    raise ValueError(
                        "WAV must be mono or stereo"
                    )

                if (
                    audio.getsampwidth()
                    != SAMPLE_WIDTH
                ):
                    raise ValueError(
                        "WAV must be PCM 16-bit"
                    )

                if (
                    audio.getframerate()
                    not in SUPPORTED_SAMPLE_RATES
                ):
                    raise ValueError(
                        "WAV sample rate must be "
                        "16000 or 48000 Hz"
                    )

                if (
                    audio.getcomptype()
                    != "NONE"
                ):
                    raise ValueError(
                        "WAV must be uncompressed PCM"
                    )

                if audio.getnframes() <= 0:
                    raise ValueError(
                        "WAV contains no audio frames"
                    )

        except (wave.Error, EOFError) as exc:
            raise ValueError(
                "Invalid WAV file; Discord Opus "
                "must be decoded to PCM16 WAV first"
            ) from exc

    # Preflight: Role=normalize/chunk WAV | Input=open PCM16 WAV | Output=mono 16k PCM chunks | Decision boundary=audio shape only | Failure/Test=Discord stereo 48k conversion
    @classmethod
    def _iter_pcm16_chunks(
        cls,
        audio: wave.Wave_read,
    ) -> Iterator[bytes]:

        source_channels = (
            audio.getnchannels()
        )
        source_sample_rate = (
            audio.getframerate()
        )

        source_frames_per_chunk = (
            CHUNK_FRAMES
            * source_sample_rate
            // SAMPLE_RATE
        )

        while True:
            source_chunk = audio.readframes(
                source_frames_per_chunk
            )

            if not source_chunk:
                return

            yield cls._normalize_pcm16(
                source_chunk,
                channels=source_channels,
                sample_rate=source_sample_rate,
            )

    # Preflight: Role=convert decoded Discord PCM | Input=PCM16 mono/stereo 16k/48k bytes | Output=PCM16 mono 16k bytes | Decision boundary=no encoding/container work | Failure/Test=sample count/value conversion
    @staticmethod
    def _normalize_pcm16(
        pcm: bytes,
        *,
        channels: int,
        sample_rate: int,
    ) -> bytes:

        samples = array("h")
        samples.frombytes(pcm)

        if sys.byteorder != "little":
            samples.byteswap()

        if channels == 2:
            mono_samples = array(
                "h",
                (
                    (
                        int(samples[index])
                        + int(samples[index + 1])
                    )
                    // 2
                    for index in range(
                        0,
                        len(samples),
                        2,
                    )
                ),
            )
        else:
            mono_samples = samples

        if sample_rate == DISCORD_SAMPLE_RATE:
            resampled = array("h")

            for index in range(
                0,
                len(mono_samples),
                3,
            ):
                window = mono_samples[
                    index:index + 3
                ]

                resampled.append(
                    sum(window)
                    // len(window)
                )

            mono_samples = resampled

        if sys.byteorder != "little":
            mono_samples.byteswap()

        return mono_samples.tobytes()

    # Preflight: Role=build ElevenLabs endpoint | Input=base URL | Output=WebSocket URL | Decision boundary=URL only | Failure/Test=http/ws base URL
    def _build_websocket_url(
        self,
    ) -> str:

        parsed = urlsplit(
            self._base_url
        )

        scheme = (
            "wss"
            if parsed.scheme
            in {"https", "wss"}
            else "ws"
        )

        path = (
            parsed.path.rstrip("/")
            + "/v1/speech-to-text/realtime"
        )

        query = urlencode(
            {
                "model_id":
                    DEFAULT_MODEL_ID,

                "audio_format":
                    "pcm_16000",

                "commit_strategy":
                    "manual",

                "language_code":
                    "vie",

                "include_timestamps":
                    "false",

                "no_verbatim":
                    "false",
            }
        )

        return urlunsplit(
            (
                scheme,
                parsed.netloc,
                path,
                query,
                "",
            )
        )

    # Preflight: Role=send PCM chunk | Input=audio bytes | Output=None | Decision boundary=transport only | Failure/Test=socket error
    @staticmethod
    async def _send_chunk(
        websocket: RealtimeSocket,
        chunk: bytes,
    ) -> None:

        payload = {
            "message_type":
                "input_audio_chunk",

            "audio_base_64":
                base64.b64encode(
                    chunk
                ).decode("ascii"),

            "commit": False,

            "sample_rate":
                SAMPLE_RATE,
        }

        await websocket.send(
            json.dumps(payload)
        )

    # Preflight: Role=commit current STT segment | Input=socket | Output=None | Decision boundary=STT segmentation only | Failure/Test=socket/provider error
    @staticmethod
    async def _commit(
        websocket: RealtimeSocket,
    ) -> None:

        payload = {
            "message_type":
                "input_audio_chunk",

            "audio_base_64": "",

            "commit": True,

            "sample_rate":
                SAMPLE_RATE,
        }

        await websocket.send(
            json.dumps(payload)
        )

    # Preflight: Role=wait for committed STT | Input=provider events | Output=text | Decision boundary=ignore partial events | Failure/Test=provider/closed connection
    async def _wait_for_transcript(
        self,
        websocket: RealtimeSocket,
    ) -> str:

        async for raw_message in websocket:

            message_type, text = (
                self._parse_message(
                    raw_message
                )
            )

            if message_type in ERROR_EVENTS:
                raise RealtimeTranscriptionError(
                    text
                    or message_type
                )

            if (
                message_type
                == "committed_transcript"
            ):
                return text

        raise RealtimeTranscriptionError(
            "ElevenLabs connection closed "
            "before transcript was returned"
        )

    # Preflight: Role=parse provider response | Input=raw JSON | Output=message type/text | Decision boundary=parse only | Failure/Test=invalid JSON
    @staticmethod
    def _parse_message(
        raw_message: str | bytes,
    ) -> tuple[str, str]:

        if isinstance(
            raw_message,
            bytes,
        ):
            raw_message = (
                raw_message.decode(
                    "utf-8"
                )
            )

        try:
            payload = json.loads(
                raw_message
            )

        except json.JSONDecodeError as exc:
            raise RealtimeTranscriptionError(
                "Invalid ElevenLabs response"
            ) from exc

        message_type = str(
            payload.get("message_type")
            or ""
        )

        text = str(
            payload.get("text")
            or payload.get("message")
            or payload.get("error")
            or ""
        ).strip()

        return message_type, text
