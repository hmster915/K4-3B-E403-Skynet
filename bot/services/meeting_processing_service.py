from bot.models.meeting import MeetingProcessingResult
from bot.services.recording_manager import RecordingSession
from skynet_core import MeetingCore


class MeetingProcessingService:

    def __init__(self, meeting_core: MeetingCore):
        self.meeting_core = meeting_core

    async def process(
        self,
        session: RecordingSession,
    ) -> MeetingProcessingResult:

        wav_paths = list(session.sink.audio_files.values())
        print(f"[MEETING] Processing {len(wav_paths)} WAV file(s) with Skynet Core...")

        core_result = await self.meeting_core.process_wavs(
            wav_paths
        )

        print("[MEETING] Skynet Core processing completed.")

        return MeetingProcessingResult.from_core(
            core_result=core_result,
            personal_notes=session.personal_notes,
            attendance=session.attendance_snapshot(),
        )
