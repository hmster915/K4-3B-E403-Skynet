import asyncio
from pathlib import Path

from bot.models.meeting import TranscriptSegment
from bot.services.recording_manager import RecordingSession


class TranscriptionService:

    def __init__(
        self,
        mode: str = "mock"
    ):
        self.mode = mode

    async def transcribe_session(
        self,
        session: RecordingSession
    ) -> list[TranscriptSegment]:

        if self.mode == "mock":
            return await self._mock_transcription(
                session
            )

        raise NotImplementedError(
            f"Transcription mode '{self.mode}' "
            "chưa được implement."
        )

    async def _mock_transcription(
        self,
        session: RecordingSession
    ) -> list[TranscriptSegment]:

        # Giả lập thời gian xử lý STT
        await asyncio.sleep(2)

        files = session.sink.audio_files
        names = session.sink.user_names

        segments: list[TranscriptSegment] = []

        for user_id, path in files.items():

            speaker_name = names.get(
                user_id,
                str(user_id)
            )

            segments.append(
                TranscriptSegment(
                    speaker_id=user_id,
                    speaker_name=speaker_name,
                    text=(
                        f"[MOCK TRANSCRIPT] "
                        f"Nội dung được ghi từ {speaker_name}."
                    ),
                )
            )

        return segments