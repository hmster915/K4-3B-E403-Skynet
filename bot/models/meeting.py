from dataclasses import dataclass, field


@dataclass
class TranscriptSegment:
    speaker_id: int
    speaker_name: str
    text: str

    start_ms: int | None = None
    end_ms: int | None = None


@dataclass
class ActionItem:
    task: str
    owner: str | None = None
    deadline: str | None = None


@dataclass
class MeetingSummary:
    summary: str

    topics: list[str] = field(
        default_factory=list
    )

    decisions: list[str] = field(
        default_factory=list
    )

    action_items: list[ActionItem] = field(
        default_factory=list
    )

    open_questions: list[str] = field(
        default_factory=list
    )


@dataclass
class MeetingProcessingResult:
    transcript: list[TranscriptSegment]
    summary: MeetingSummary
    personal_notes: dict[int, list[str]] = field(default_factory=dict)
