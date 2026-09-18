"""
TranscriptSegment           --> một đoạn transcript cuối
Transcript                  --> transcript hoàn chỉnh sau meeting
RealtimeTranscriptEventType --> loại event realtime
RealtimeTranscriptWord      --> word + timestamp
RealtimeTranscriptEvent     --> event từ STT realtime
"""

from enum import StrEnum

from pydantic import Field

from skynet_core.models.base import FrozenModel


class TranscriptSegment(FrozenModel):
    text: str = Field(min_length=1)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    speaker: str | None = None


class Transcript(FrozenModel):
    text: str = Field(min_length=1)

    segments: list[TranscriptSegment] = Field(
        default_factory=list
    )

    source: str = "elevenlabs_realtime"

    language_code: str | None = None


class RealtimeTranscriptEventType(StrEnum):
    SESSION_STARTED = "session_started"
    PARTIAL = "partial_transcript"
    FINAL = "final_transcript"
    COMMITTED = "committed_transcript"
    COMMITTED_WITH_TIMESTAMPS = (
        "committed_transcript_with_timestamps"
    )


class RealtimeTranscriptWord(FrozenModel):
    text: str = Field(min_length=1)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)


class RealtimeTranscriptEvent(FrozenModel):
    event_type: RealtimeTranscriptEventType

    text: str | None = None

    session_id: str | None = None

    language_code: str | None = None

    words: list[RealtimeTranscriptWord] = Field(
        default_factory=list
    )