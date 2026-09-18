from bot.models.meeting import (
    MeetingProcessingResult,
)

from bot.services.recording_manager import (
    RecordingSession,
)

from bot.services.transcription_service import (
    TranscriptionService,
)

from bot.services.summarization_service import (
    SummarizationService,
)


class MeetingProcessingService:

    def __init__(
        self,
        transcription_service: TranscriptionService,
        summarization_service: SummarizationService,
    ):
        self.transcription_service = (
            transcription_service
        )

        self.summarization_service = (
            summarization_service
        )

    async def process(
        self,
        session: RecordingSession,
    ) -> MeetingProcessingResult:

        print(
            "[MEETING] Starting transcription..."
        )

        transcript = (
            await self.transcription_service
            .transcribe_session(session)
        )

        print(
            f"[MEETING] Transcript completed: "
            f"{len(transcript)} segments"
        )

        if not transcript:
            raise RuntimeError(
                "Không tìm thấy nội dung audio "
                "để tạo transcript."
            )

        print(
            "[MEETING] Starting summary..."
        )

        summary = (
            await self.summarization_service
            .summarize(transcript)
        )

        print(
            "[MEETING] Summary completed."
        )

        return MeetingProcessingResult(
            transcript=transcript,
            summary=summary,
            personal_notes={
                user_id: list(notes)
                for user_id, notes in session.personal_notes.items()
            },
        )
