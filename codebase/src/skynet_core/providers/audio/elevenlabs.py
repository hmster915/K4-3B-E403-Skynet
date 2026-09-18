"""
__init__()              --> cấu hình ElevenLabs
transcribe_wav()        --> WAV -> Transcript
_validate_wav()         --> kiểm tra PCM16 mono 16k
_build_websocket_url()  --> tạo realtime URL
_send_chunk()           --> gửi audio chunk
_commit()               --> chốt audio segment
_wait_for_transcript()  --> nhận committed transcript
_parse_message()        --> đọc provider response
"""

import base64
import json
import os
import wave

from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
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

    # Preflight: Role=transcribe WAV meeting | Input=PCM16 mono 16k WAV | Output=Transcript | Decision boundary=STT only, no LLM | Failure/Test=invalid WAV/network/provider failure
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

                while True:
                    chunk = audio.readframes(
                        CHUNK_FRAMES
                    )

                    if not chunk:
                        break

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

    # Preflight: Role=validate WAV contract | Input=file path | Output=None | Decision boundary=format validation only | Failure/Test=missing/wrong format
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
                    != CHANNELS
                ):
                    raise ValueError(
                        "WAV must be mono"
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
                    != SAMPLE_RATE
                ):
                    raise ValueError(
                        "WAV must be 16000 Hz"
                    )

                if (
                    audio.getcomptype()
                    != "NONE"
                ):
                    raise ValueError(
                        "WAV must be uncompressed PCM"
                    )

        except wave.Error as exc:
            raise ValueError(
                "Invalid WAV file"
            ) from exc

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