"""
from_env()      --> build configured MeetingCore
process_wavs()  --> WAV files -> MeetingCoreResult
_aggregate()    --> raw Transcripts -> consolidated Transcript
"""

import asyncio
import os
from collections.abc import Sequence
from pathlib import Path

from skynet_core.ai.meeting_analyzer import MeetingAnalyzer
from skynet_core.models.base import FrozenModel
from skynet_core.models.meeting import MeetingReport
from skynet_core.models.transcript import Transcript
from skynet_core.providers.audio.base import AudioProvider
from skynet_core.providers.audio.elevenlabs import ElevenLabsAudioProvider
from skynet_core.providers.text.openai_compatible import OpenAICompatibleTextGenerator


class MeetingCoreError(RuntimeError):
    """Raised when meeting processing fails across STT, aggregation, or analysis."""


class MeetingCoreResult(FrozenModel):
    """Immutable result containing full transcript and structured meeting report."""

    transcript: Transcript
    report: MeetingReport


class MeetingCore:
    """Public façade orchestrating WAV transcription and structured meeting note analysis."""

    # Preflight: Role=Initialize MeetingCore | Input=AudioProvider, MeetingAnalyzer | Output=MeetingCore | Decision boundary=Dependency injection only | Failure/Test=TypeError on invalid types
    def __init__(
        self,
        audio_provider: AudioProvider,
        meeting_analyzer: MeetingAnalyzer,
    ) -> None:
        self._audio_provider = audio_provider
        self._meeting_analyzer = meeting_analyzer

    # Preflight: Role=Build configured MeetingCore | Input=environment variables | Output=MeetingCore instance | Decision boundary=Config validation and composition | Failure/Test=MeetingCoreError on missing env vars
    @classmethod
    def from_env(cls) -> "MeetingCore":
        required_vars = (
            "ELEVENLABS_API_KEY",
            "LLM_API_KEY",
            "LLM_BASE_URL",
            "LLM_MODEL",
        )
        missing = [var for var in required_vars if not os.getenv(var, "").strip()]
        if missing:
            raise MeetingCoreError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        elevenlabs_key = os.environ["ELEVENLABS_API_KEY"].strip()
        elevenlabs_base_url = os.getenv("ELEVENLABS_BASE_URL", "").strip() or None

        llm_key = os.environ["LLM_API_KEY"].strip()
        llm_base_url = os.environ["LLM_BASE_URL"].strip()
        llm_model = os.environ["LLM_MODEL"].strip()

        audio_provider = ElevenLabsAudioProvider(
            api_key=elevenlabs_key,
            base_url=elevenlabs_base_url,
        )
        text_generator = OpenAICompatibleTextGenerator(
            api_key=llm_key,
            base_url=llm_base_url,
            model=llm_model,
        )
        analyzer = MeetingAnalyzer(text_generator=text_generator)

        return cls(
            audio_provider=audio_provider,
            meeting_analyzer=analyzer,
        )

    # Preflight: Role=Process WAV audio files to meeting report | Input=Sequence of Path | Output=MeetingCoreResult | Decision boundary=Orchestrate STT + text join + LLM analysis | Failure/Test=MeetingCoreError on empty input, STT failure, blank transcript, or analysis failure
    async def process_wavs(
        self,
        wav_paths: Sequence[Path],
    ) -> MeetingCoreResult:
        if not wav_paths:
            raise MeetingCoreError("No WAV files provided for processing.")

        raw_transcripts: list[Transcript] = []
        for wav_path in wav_paths:
            try:
                transcript = await self._audio_provider.transcribe_wav(wav_path)
            except Exception as err:
                raise MeetingCoreError(
                    f"Audio transcription failed for '{wav_path.name}': {type(err).__name__}"
                ) from err
            raw_transcripts.append(transcript)

        full_transcript = self._aggregate(raw_transcripts)

        try:
            report = await asyncio.to_thread(
                self._meeting_analyzer.analyze,
                full_transcript,
            )
        except Exception as err:
            raise MeetingCoreError(
                f"Meeting analysis failed: {type(err).__name__}"
            ) from err

        return MeetingCoreResult(
            transcript=full_transcript,
            report=report,
        )

    # Preflight: Role=Aggregate raw transcripts into single Transcript | Input=Sequence of Transcript | Output=Transcript | Decision boundary=Newline joining and empty filtering | Failure/Test=MeetingCoreError if no usable transcript
    def _aggregate(
        self,
        raw_transcripts: Sequence[Transcript],
    ) -> Transcript:
        useful_texts: list[str] = []
        for t in raw_transcripts:
            stripped = t.text.strip()
            if stripped:
                useful_texts.append(stripped)

        if not useful_texts:
            raise MeetingCoreError(
                "No usable transcript produced from the provided WAV files."
            )

        combined_text = "\n".join(useful_texts)
        return Transcript(text=combined_text)
