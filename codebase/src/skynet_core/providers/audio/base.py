"""
transcribe_wav() --> WAV -> full Transcript
"""

from pathlib import Path
from typing import Protocol

from skynet_core.models.transcript import Transcript


class AudioProvider(Protocol):

    # Preflight: Role=transcribe meeting WAV | Input=WAV path | Output=Transcript | Decision boundary=STT only, no LLM | Failure/Test=invalid WAV/provider error
    async def transcribe_wav(
        self,
        wav_path: Path,
    ) -> Transcript:
        ...