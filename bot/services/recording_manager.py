from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    personal_notes: dict[int, list[str]] = field(default_factory=dict)
    participant_names: dict[int, str] = field(default_factory=dict)
    initial_participant_ids: set[int] = field(default_factory=set)
    peak_participant_count: int = 0
    attendance_events: list[dict] = field(default_factory=list)
    ended_at: datetime | None = None

    def record_attendance_event(
        self,
        *,
        event: str,
        active_count: int,
        member_id: int | None = None,
        member_name: str | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        if member_id is not None and member_name:
            self.participant_names[member_id] = member_name
        self.peak_participant_count = max(
            self.peak_participant_count,
            active_count,
        )
        self.attendance_events.append(
            {
                "timestamp": (
                    occurred_at or datetime.now(timezone.utc)
                ).isoformat(),
                "event": event,
                "active_count": active_count,
                "user_id": member_id,
                "name": member_name,
            }
        )

    def attendance_snapshot(self) -> dict:
        return {
            "voice_channel_id": self.voice_channel_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": (
                self.ended_at.isoformat() if self.ended_at else None
            ),
            "initial_count": len(self.initial_participant_ids),
            "unique_count": len(self.participant_names),
            "peak_count": self.peak_participant_count,
            "participants": [
                {"user_id": user_id, "name": name}
                for user_id, name in self.participant_names.items()
            ],
            "events": [dict(event) for event in self.attendance_events],
        }


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
