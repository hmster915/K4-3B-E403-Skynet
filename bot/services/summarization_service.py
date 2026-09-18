import asyncio

from bot.models.meeting import (
    TranscriptSegment,
    MeetingSummary,
    ActionItem,
)


class SummarizationService:

    def __init__(
        self,
        mode: str = "mock"
    ):
        self.mode = mode

    async def summarize(
        self,
        transcript: list[TranscriptSegment]
    ) -> MeetingSummary:

        if self.mode == "mock":
            return await self._mock_summary(
                transcript
            )

        raise NotImplementedError(
            f"Summarization mode '{self.mode}' "
            "chưa được implement."
        )

    async def _mock_summary(
        self,
        transcript: list[TranscriptSegment]
    ) -> MeetingSummary:

        await asyncio.sleep(2)

        speakers = list({
            segment.speaker_name
            for segment in transcript
        })

        speaker_text = ", ".join(
            speakers
        )

        return MeetingSummary(
            summary=(
                "Đây là dữ liệu tổng hợp thử nghiệm của "
                "Skynet. "
                f"Cuộc họp ghi nhận các speaker: "
                f"{speaker_text or 'không xác định'}."
            ),

            topics=[
                "Phân tích vấn đề",
                "Trao đổi hướng giải quyết",
                "Phân chia công việc",
            ],

            decisions=[
                "Tiếp tục hoàn thiện solution theo scope đã thống nhất.",
                "Kiểm tra lại dữ liệu trước bước xử lý AI.",
            ],

            action_items=[
                ActionItem(
                    owner="Khoa",
                    task="Hoàn thiện Discord bot recording."
                ),

                ActionItem(
                    owner="Team",
                    task="Tích hợp pipeline transcription."
                ),
            ],

            open_questions=[
                "Sử dụng STT provider nào?",
                "Cách benchmark chất lượng summary?"
            ],
        )