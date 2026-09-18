from pydantic import Field

from skynet_core.models.base import FrozenModel


class TranscriptSegment(FrozenModel):
    text: str = Field(min_length=1)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    speaker: str | None = None


class Transcript(FrozenModel):
    text: str = Field(min_length=1)
    segments: list[TranscriptSegment] = Field(default_factory=list)

    source: str = "audio"

    language_code: str | None = None
    language_probability: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )