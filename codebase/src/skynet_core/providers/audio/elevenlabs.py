"""
__init__()               --> cấu hình ElevenLabs Realtime STT
connect()                --> mở WebSocket realtime
_build_websocket_url()   --> tạo URL + query params

send_chunk()             --> gửi PCM audio chunk
commit()                 --> chốt transcript segment
events()                 --> nhận transcript events
close()                  --> đóng WebSocket

_parse_event()           --> response -> realtime event
_map_words()             --> timestamps -> normalized words
"""

import base64
import json
import os

from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
)

from typing import Any

from urllib.parse import (
    urlencode,
    urlsplit,
    urlunsplit,
)

import websockets

from skynet_core.models.transcript import (
    RealtimeTranscriptEvent,
    RealtimeTranscriptEventType,
    RealtimeTranscriptWord,
)


DEFAULT_ELEVENLABS_BASE_URL = (
    "https://api.elevenlabs.io"
)

DEFAULT_REALTIME_MODEL_ID = (
    "scribe_v2_realtime"
)

DEFAULT_AUDIO_FORMAT = "pcm_16000"

DEFAULT_SAMPLE_RATE = 16000


ERROR_MESSAGE_TYPES = {
    "error",
    "auth_error",
    "quota_exceeded",
    "commit_throttled",
    "transcriber_error",
    "unaccepted_terms",
    "rate_limited",
    "input_error",
    "invalid_request",
    "queue_overflow",
    "resource_exhausted",
    "session_time_limit_exceeded",
    "chunk_size_exceeded",
    "insufficient_audio_activity",
}


WebSocketConnector = Callable[
    ...,
    Awaitable[Any],
]


class RealtimeTranscriptionError(
    RuntimeError
):
    pass


class ElevenLabsRealtimeSession:

    # Preflight:
    # Role=wrap realtime STT session
    # Input=connected websocket
    # Output=audio/transcript exchange
    # Decision boundary=transport only
    # Failure/Test=provider error

    def __init__(
        self,
        websocket: Any,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
    ) -> None:

        self._websocket = websocket

        self._sample_rate = sample_rate

        self._closed = False

    # Preflight:
    # Role=send audio
    # Input=PCM bytes
    # Output=input_audio_chunk
    # Decision boundary=no STT inference
    # Failure/Test=empty/closed session

    async def send_chunk(
        self,
        audio_chunk: bytes,
    ) -> None:

        if self._closed:

            raise RealtimeTranscriptionError(
                "Realtime STT session is closed"
            )

        if not audio_chunk:

            raise ValueError(
                "audio_chunk must not be empty"
            )

        payload = {
            "message_type": "input_audio_chunk",

            "audio_base_64": (
                base64.b64encode(
                    audio_chunk
                ).decode("ascii")
            ),

            "commit": False,

            "sample_rate": (
                self._sample_rate
            ),
        }

        await self._websocket.send(
            json.dumps(payload)
        )

    # Preflight:
    # Role=commit STT segment
    # Input=none
    # Output=commit message
    # Decision boundary=segment boundary
    # Failure/Test=closed session

    async def commit(
        self,
    ) -> None:

        if self._closed:

            raise RealtimeTranscriptionError(
                "Realtime STT session is closed"
            )

        payload = {
            "message_type": "input_audio_chunk",
            "audio_base_64": "",
            "commit": True,
            "sample_rate": self._sample_rate,
        }

        await self._websocket.send(
            json.dumps(payload)
        )

    # Preflight:
    # Role=receive STT events
    # Input=WebSocket messages
    # Output=normalized events
    # Decision boundary=no meeting inference
    # Failure/Test=invalid/error event

    async def events(
        self,
    ) -> AsyncIterator[
        RealtimeTranscriptEvent
    ]:

        if self._closed:

            raise RealtimeTranscriptionError(
                "Realtime STT session is closed"
            )

        async for raw_message in (
            self._websocket
        ):

            event = self._parse_event(
                raw_message
            )

            if event is not None:
                yield event

    # Preflight:
    # Role=close connection
    # Input=none
    # Output=closed websocket
    # Decision boundary=cleanup only
    # Failure/Test=idempotent

    async def close(
        self,
    ) -> None:

        if self._closed:
            return

        self._closed = True

        await self._websocket.close()

    # Preflight:
    # Role=normalize provider event
    # Input=raw JSON
    # Output=RealtimeTranscriptEvent
    # Decision boundary=mapping only
    # Failure/Test=invalid/error payload

    @staticmethod
    def _parse_event(
        raw_message: str | bytes,
    ) -> RealtimeTranscriptEvent | None:

        try:

            if isinstance(
                raw_message,
                bytes,
            ):

                raw_message = (
                    raw_message.decode(
                        "utf-8"
                    )
                )

            payload = json.loads(
                raw_message
            )

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:

            raise RealtimeTranscriptionError(
                "ElevenLabs returned "
                "invalid realtime JSON"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):

            raise RealtimeTranscriptionError(
                "Invalid realtime event shape"
            )

        message_type = str(
            payload.get(
                "message_type"
            )
            or ""
        )

        if message_type in (
            ERROR_MESSAGE_TYPES
        ):

            detail = (
                payload.get("error")
                or payload.get("message")
                or message_type
            )

            raise RealtimeTranscriptionError(
                "ElevenLabs realtime "
                f"STT error: {detail}"
            )

        event_type_map = {

            "session_started":
                RealtimeTranscriptEventType
                .SESSION_STARTED,

            "partial_transcript":
                RealtimeTranscriptEventType
                .PARTIAL,

            "final_transcript":
                RealtimeTranscriptEventType
                .FINAL,

            "final_transcript_with_timestamps":
                RealtimeTranscriptEventType
                .FINAL,

            "committed_transcript":
                RealtimeTranscriptEventType
                .COMMITTED,

            "committed_transcript_with_timestamps":
                RealtimeTranscriptEventType
                .COMMITTED_WITH_TIMESTAMPS,
        }

        event_type = event_type_map.get(
            message_type
        )

        if event_type is None:
            return None

        text = payload.get("text")

        return RealtimeTranscriptEvent(

            event_type=event_type,

            text=(
                str(text).strip()
                if text
                else None
            ),

            session_id=(
                str(
                    payload[
                        "session_id"
                    ]
                )
                if payload.get(
                    "session_id"
                )
                else None
            ),

            language_code=(
                str(
                    payload[
                        "language_code"
                    ]
                )
                if payload.get(
                    "language_code"
                )
                else None
            ),

            words=(
                ElevenLabsRealtimeSession
                ._map_words(
                    payload.get(
                        "words"
                    )
                )
            ),
        )

    # Preflight:
    # Role=normalize timestamp words
    # Input=provider word list
    # Output=typed words
    # Decision boundary=mapping only
    # Failure/Test=skip invalid words

    @staticmethod
    def _map_words(
        raw_words: Any,
    ) -> list[
        RealtimeTranscriptWord
    ]:

        if not isinstance(
            raw_words,
            list,
        ):
            return []

        words: list[
            RealtimeTranscriptWord
        ] = []

        for raw_word in raw_words:

            if not isinstance(
                raw_word,
                dict,
            ):
                continue

            text = str(
                raw_word.get("text")
                or ""
            ).strip()

            start = raw_word.get(
                "start"
            )

            end = raw_word.get(
                "end"
            )

            if (
                not text
                or not isinstance(
                    start,
                    (int, float),
                )
                or not isinstance(
                    end,
                    (int, float),
                )
            ):
                continue

            words.append(
                RealtimeTranscriptWord(
                    text=text,
                    start_seconds=float(
                        start
                    ),
                    end_seconds=float(
                        end
                    ),
                )
            )

        return words


class ElevenLabsRealtimeAudioProvider:

    # Preflight:
    # Role=configure realtime STT
    # Input=key/base URL/VAD config
    # Output=provider
    # Decision boundary=config only
    # Failure/Test=missing key/URL

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,

        connector:
            WebSocketConnector
            | None = None,

        model_id: str = (
            DEFAULT_REALTIME_MODEL_ID
        ),

        language_code:
            str | None = "vie",

        keyterms:
            list[str] | None = None,

        vad_silence_threshold_secs:
            float = 1.5,

        vad_threshold:
            float = 0.4,

        min_speech_duration_ms:
            int = 100,

        min_silence_duration_ms:
            int = 100,

        open_timeout_seconds:
            float = 10.0,
    ) -> None:

        resolved_api_key = (
            api_key
            or os.getenv(
                "ELEVENLABS_API_KEY"
            )
            or ""
        ).strip()

        if not resolved_api_key:

            raise ValueError(
                "ELEVENLABS_API_KEY "
                "is required"
            )

        resolved_base_url = (
            base_url
            or os.getenv(
                "ELEVENLABS_BASE_URL"
            )
            or DEFAULT_ELEVENLABS_BASE_URL
        ).strip().rstrip("/")

        if not resolved_base_url.startswith(
            (
                "http://",
                "https://",
                "ws://",
                "wss://",
            )
        ):

            raise ValueError(
                "ELEVENLABS_BASE_URL "
                "must be an http(s) "
                "or ws(s) URL"
            )

        self._api_key = (
            resolved_api_key
        )

        self._base_url = (
            resolved_base_url
        )

        self._connector = (
            connector
            or websockets.connect
        )

        self._model_id = model_id

        self._language_code = (
            language_code
        )

        self._keyterms = list(
            keyterms or []
        )

        self._vad_silence_threshold_secs = (
            vad_silence_threshold_secs
        )

        self._vad_threshold = (
            vad_threshold
        )

        self._min_speech_duration_ms = (
            min_speech_duration_ms
        )

        self._min_silence_duration_ms = (
            min_silence_duration_ms
        )

        self._open_timeout_seconds = (
            open_timeout_seconds
        )

    # Preflight:
    # Role=open ElevenLabs websocket
    # Input=provider config
    # Output=realtime session
    # Decision boundary=connection only
    # Failure/Test=network/auth failure

    async def connect(
        self,
    ) -> ElevenLabsRealtimeSession:

        websocket = await self._connector(

            self._build_websocket_url(),

            additional_headers={
                "xi-api-key":
                    self._api_key
            },

            open_timeout=(
                self._open_timeout_seconds
            ),
        )

        return ElevenLabsRealtimeSession(
            websocket
        )

    # Preflight:
    # Role=build WSS URL
    # Input=provider config
    # Output=realtime endpoint
    # Decision boundary=encoding only
    # Failure/Test=custom URL supported

    def _build_websocket_url(
        self,
    ) -> str:

        parsed = urlsplit(
            self._base_url
        )

        ws_scheme = (
            "wss"
            if parsed.scheme
            in {"https", "wss"}
            else "ws"
        )

        base_path = (
            parsed.path.rstrip("/")
        )

        path = (
            f"{base_path}"
            "/v1/speech-to-text/realtime"
        )

        params: list[
            tuple[str, str]
        ] = [

            (
                "model_id",
                self._model_id,
            ),

            (
                "audio_format",
                DEFAULT_AUDIO_FORMAT,
            ),

            (
                "commit_strategy",
                "vad",
            ),

            (
                "vad_silence_threshold_secs",
                str(
                    self
                    ._vad_silence_threshold_secs
                ),
            ),

            (
                "vad_threshold",
                str(
                    self._vad_threshold
                ),
            ),

            (
                "min_speech_duration_ms",
                str(
                    self
                    ._min_speech_duration_ms
                ),
            ),

            (
                "min_silence_duration_ms",
                str(
                    self
                    ._min_silence_duration_ms
                ),
            ),

            (
                "include_timestamps",
                "true",
            ),

            (
                "no_verbatim",
                "false",
            ),
        ]

        if self._language_code:

            params.append(
                (
                    "language_code",
                    self._language_code,
                )
            )

        for keyterm in (
            self._keyterms
        ):

            params.append(
                (
                    "keyterms",
                    keyterm,
                )
            )

        return urlunsplit(
            (
                ws_scheme,
                parsed.netloc,
                path,
                urlencode(params),
                "",
            )
        )