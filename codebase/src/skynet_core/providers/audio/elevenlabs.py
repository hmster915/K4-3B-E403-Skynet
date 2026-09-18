import mimetypes
import os
from pathlib import Path
from typing import Any, Protocol

import httpx

from skynet_core.models.transcript import (
    Transcript,
    TranscriptSegment,
)
"""
__init__()                  --> cấu hình ElevenLabs provider
transcribe()                --> audio -> Transcript
_request_transcription()    --> gọi ElevenLabs STT API
_build_form_data()          --> tạo request parameters
_parse_json_response()      --> đọc JSON response
_map_response()             --> response -> Transcript
_group_words_by_speaker()   --> gom word thành speaker segments
flush()                     --> đóng segment speaker hiện tại
"""

DEFAULT_ELEVENLABS_BASE_URL = "https://api.elevenlabs.io"
DEFAULT_MODEL_ID = "scribe_v2"


class AsyncPostClient(Protocol):

    async def post(
        self,
        url: str,
        **kwargs: Any,
    ) -> Any:
        ...


class AudioTranscriptionError(RuntimeError):
    """Raised when ElevenLabs cannot produce a usable transcript."""


class ElevenLabsAudioProvider:

    # Preflight:
    # Role=configure ElevenLabs STT transport
    # Input=API key/base URL/options
    # Output=provider instance
    # Decision boundary=configuration only
    # Failure/Test=missing key or invalid URL.

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        client: AsyncPostClient | None = None,
        model_id: str = DEFAULT_MODEL_ID,
        language_code: str | None = "vie",
        diarize: bool = True,
        keyterms: list[str] | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:

        resolved_api_key = (
            api_key
            or os.getenv("ELEVENLABS_API_KEY")
            or ""
        ).strip()

        if not resolved_api_key:
            raise ValueError(
                "ELEVENLABS_API_KEY is required"
            )

        resolved_base_url = (
            base_url
            or os.getenv("ELEVENLABS_BASE_URL")
            or DEFAULT_ELEVENLABS_BASE_URL
        ).strip().rstrip("/")

        if not resolved_base_url.startswith(
            ("http://", "https://")
        ):
            raise ValueError(
                "ELEVENLABS_BASE_URL must be an http(s) URL"
            )

        self._api_key = resolved_api_key
        self.base_url = resolved_base_url

        self._client = client
        self._model_id = model_id
        self._language_code = language_code
        self._diarize = diarize
        self._keyterms = list(keyterms or [])
        self._timeout_seconds = timeout_seconds

    # Preflight:
    # Role=transcribe one local recording
    # Input=existing audio/video path
    # Output=normalized Transcript
    # Decision boundary=STT only; never infer meeting facts
    # Failure/Test=missing file, HTTP/provider error,
    # malformed/empty response.

    async def transcribe(
        self,
        audio_path: Path,
    ) -> Transcript:

        if not audio_path.is_file():
            raise FileNotFoundError(
                f"Audio file not found: {audio_path}"
            )

        try:
            response = await self._request_transcription(
                audio_path
            )

            payload = self._parse_json_response(
                response
            )

            return self._map_response(
                payload
            )

        except AudioTranscriptionError:
            raise

        except Exception as exc:
            raise AudioTranscriptionError(
                "ElevenLabs transcription failed"
            ) from exc

    # Preflight:
    # Role=send multipart request to ElevenLabs
    # Input=audio path
    # Output=raw HTTP response
    # Decision boundary=transport only
    # Failure/Test=non-2xx or network failure.

    async def _request_transcription(
        self,
        audio_path: Path,
    ) -> Any:

        url = (
            f"{self.base_url}/v1/speech-to-text"
        )

        data = self._build_form_data()

        content_type = (
            mimetypes.guess_type(audio_path.name)[0]
            or "application/octet-stream"
        )

        headers = {
            "xi-api-key": self._api_key
        }

        with audio_path.open("rb") as audio_file:

            files = {
                "file": (
                    audio_path.name,
                    audio_file,
                    content_type,
                )
            }

            if self._client is not None:

                response = await self._client.post(
                    url,
                    headers=headers,
                    data=data,
                    files=files,
                )

            else:

                async with httpx.AsyncClient(
                    timeout=self._timeout_seconds
                ) as client:

                    response = await client.post(
                        url,
                        headers=headers,
                        data=data,
                        files=files,
                    )

        try:
            response.raise_for_status()

        except Exception as exc:

            status_code = getattr(
                response,
                "status_code",
                "unknown",
            )

            raise AudioTranscriptionError(
                f"ElevenLabs STT returned HTTP {status_code}"
            ) from exc

        return response

    # Preflight:
    # Role=build ElevenLabs multipart fields
    # Input=provider config
    # Output=form field pairs
    # Decision boundary=request encoding only
    # Failure/Test=optional fields omitted when unset.

    def _build_form_data(
        self,
    ) -> list[tuple[str, str]]:

        fields: list[tuple[str, str]] = [
            (
                "model_id",
                self._model_id,
            ),
            (
                "diarize",
                str(self._diarize).lower(),
            ),
            (
                "timestamps_granularity",
                "word",
            ),
            (
                "tag_audio_events",
                "false",
            ),
        ]

        if self._language_code:

            fields.append(
                (
                    "language_code",
                    self._language_code,
                )
            )

        for keyterm in self._keyterms:

            fields.append(
                (
                    "keyterms",
                    keyterm,
                )
            )

        return fields

    # Preflight:
    # Role=parse provider JSON
    # Input=HTTP response
    # Output=dict payload
    # Decision boundary=no domain interpretation
    # Failure/Test=invalid/non-object JSON fails closed.

    @staticmethod
    def _parse_json_response(
        response: Any,
    ) -> dict[str, Any]:

        try:
            payload = response.json()

        except Exception as exc:
            raise AudioTranscriptionError(
                "ElevenLabs returned invalid JSON"
            ) from exc

        if not isinstance(payload, dict):

            raise AudioTranscriptionError(
                "ElevenLabs returned an invalid response shape"
            )

        return payload

    # Preflight:
    # Role=normalize ElevenLabs payload
    # Input=provider response dict
    # Output=Transcript
    # Decision boundary=map text/timestamps/speakers only
    # Failure/Test=empty transcript fails closed.

    def _map_response(
        self,
        payload: dict[str, Any],
    ) -> Transcript:

        text = str(
            payload.get("text") or ""
        ).strip()

        if not text:

            raise AudioTranscriptionError(
                "ElevenLabs returned an empty transcript"
            )

        raw_words = (
            payload.get("words") or []
        )

        words = (
            raw_words
            if isinstance(raw_words, list)
            else []
        )

        language_probability = payload.get(
            "language_probability"
        )

        if not isinstance(
            language_probability,
            (int, float),
        ):
            language_probability = None

        return Transcript(
            text=text,

            segments=self._group_words_by_speaker(
                words
            ),

            source=(
                f"elevenlabs:{self._model_id}"
            ),

            language_code=(
                str(payload["language_code"])
                if payload.get("language_code")
                is not None
                else None
            ),

            language_probability=(
                language_probability
            ),
        )

    # Preflight:
    # Role=group timestamped tokens into speaker turns
    # Input=ElevenLabs word dictionaries
    # Output=TranscriptSegment list
    # Decision boundary=no semantic interpretation
    # Failure/Test=malformed tokens are skipped.

    @staticmethod
    def _group_words_by_speaker(
        words: list[Any],
    ) -> list[TranscriptSegment]:

        segments: list[TranscriptSegment] = []

        current_speaker: str | None = None
        current_text: list[str] = []

        current_start: float | None = None
        current_end: float | None = None

        def flush() -> None:

            nonlocal current_speaker
            nonlocal current_text
            nonlocal current_start
            nonlocal current_end

            joined_text = "".join(
                current_text
            ).strip()

            if (
                joined_text
                and current_start is not None
                and current_end is not None
            ):

                segments.append(
                    TranscriptSegment(
                        text=joined_text,
                        start_seconds=current_start,
                        end_seconds=current_end,
                        speaker=current_speaker,
                    )
                )

            current_speaker = None
            current_text = []
            current_start = None
            current_end = None

        for word in words:

            if not isinstance(word, dict):
                continue

            token_text = str(
                word.get("text") or ""
            )

            start = word.get("start")
            end = word.get("end")
            speaker = word.get("speaker_id")

            if (
                not token_text
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

            if (
                current_text
                and speaker != current_speaker
            ):
                flush()

            if not current_text:

                current_speaker = (
                    str(speaker)
                    if speaker is not None
                    else None
                )

                current_start = float(start)

            current_text.append(
                token_text
            )

            current_end = float(end)

        flush()

        return segments