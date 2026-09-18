"""
Transcript --> full transcript sau meeting
"""

from pydantic import Field

from skynet_core.models.base import FrozenModel


class Transcript(FrozenModel):
    text: str = Field(min_length=1)

    source: str = "elevenlabs_realtime"

    language_code: str | None = None