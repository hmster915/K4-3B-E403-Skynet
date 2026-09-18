from pathlib import Path
from typing import Protocol

from skynet_core.models.transcript import Transcript


class AudioProvider(Protocol):

    # Preflight:
    # Role=transcribe audio only
    # Input=audio path
    # Output=Transcript
    # Decision boundary=no meeting interpretation
    # Failure/Test=provider raises typed/runtime error.

    async def transcribe(
        self,
        audio_path: Path,
    ) -> Transcript:
        ...