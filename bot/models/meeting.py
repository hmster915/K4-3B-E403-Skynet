from dataclasses import dataclass, field

from skynet_core import MeetingCoreResult
from skynet_core.models.meeting import MeetingReport
from skynet_core.models.transcript import Transcript


@dataclass(frozen=True)
class MeetingProcessingResult:
    """Core output plus Discord-only personal notes."""

    transcript: Transcript
    report: MeetingReport
    personal_notes: dict[int, list[str]] = field(default_factory=dict)
    attendance: dict = field(default_factory=dict)

    @classmethod
    def from_core(
        cls,
        core_result: MeetingCoreResult,
        personal_notes: dict[int, list[str]],
        attendance: dict,
    ) -> "MeetingProcessingResult":
        return cls(
            transcript=core_result.transcript,
            report=core_result.report,
            personal_notes={
                user_id: list(notes)
                for user_id, notes in personal_notes.items()
            },
            attendance=dict(attendance),
        )

    def to_dict(self) -> dict:
        """Return the core JSON shape plus Discord-only personal notes."""

        return {
            "transcript": self.transcript.model_dump(),
            "report": self.report.model_dump(),
            "personal_notes": {
                str(user_id): list(notes)
                for user_id, notes in self.personal_notes.items()
            },
            "attendance": dict(self.attendance),
        }
