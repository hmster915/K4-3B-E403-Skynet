from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from discord.ext import voice_recv

from bot.audio.recording_sink import PerUserWaveSink


@dataclass
class RecordingSession:
    guild_id: int
    voice_channel_id: int
    text_channel_id: int

    started_by: int
    started_at: datetime

    output_dir: Path

    voice_client: voice_recv.VoiceRecvClient
    sink: PerUserWaveSink

    ending: bool = False


class RecordingManager:

    def __init__(self):
        self.sessions: dict[int, RecordingSession] = {}

    def get(
        self,
        guild_id: int
    ) -> RecordingSession | None:
        return self.sessions.get(
            guild_id
        )

    def is_recording(
        self,
        guild_id: int
    ) -> bool:
        return guild_id in self.sessions

    def add(
        self,
        session: RecordingSession
    ):
        self.sessions[
            session.guild_id
        ] = session

    def remove(
        self,
        guild_id: int
    ):
        return self.sessions.pop(
            guild_id,
            None
        )


recording_manager = RecordingManager()