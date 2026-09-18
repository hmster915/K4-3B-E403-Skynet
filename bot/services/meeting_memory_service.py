import asyncio
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bot.models.meeting import MeetingProcessingResult


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATABASE_PATH = ROOT_DIR / ".bot-data" / "meeting_history.sqlite3"
MAX_MEETINGS_PER_CHANNEL = 20


@dataclass(frozen=True)
class StoredMeeting:
    created_at: str
    channel_id: int
    message_id: int
    transcript: dict
    report: dict


class MeetingMemoryService:
    """Persist meeting results without Discord-only personal notes."""

    def __init__(self, database_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.database_path = database_path
        self._lock = asyncio.Lock()

    async def save(
        self,
        *,
        guild_id: int,
        channel_id: int,
        message_id: int,
        result: MeetingProcessingResult,
    ) -> None:
        payload = result.to_dict()
        async with self._lock:
            await asyncio.to_thread(
                self._save_sync,
                guild_id,
                channel_id,
                message_id,
                payload["transcript"],
                payload["report"],
            )

    async def recent(
        self,
        *,
        guild_id: int,
        channel_id: int,
        limit: int = 3,
    ) -> list[StoredMeeting]:
        safe_limit = max(1, min(limit, MAX_MEETINGS_PER_CHANNEL))
        async with self._lock:
            return await asyncio.to_thread(
                self._recent_sync,
                guild_id,
                channel_id,
                safe_limit,
            )

    async def recent_for_guild(
        self,
        *,
        guild_id: int,
        limit: int = 5,
    ) -> list[StoredMeeting]:
        safe_limit = max(1, min(limit, MAX_MEETINGS_PER_CHANNEL))
        async with self._lock:
            return await asyncio.to_thread(
                self._recent_for_guild_sync,
                guild_id,
                safe_limit,
            )

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS meeting_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                transcript_json TEXT NOT NULL,
                report_json TEXT NOT NULL
            )
            """
        )
        return connection

    def _save_sync(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
        transcript: dict,
        report: dict,
    ) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO meeting_history (
                        guild_id,
                        channel_id,
                        message_id,
                        created_at,
                        transcript_json,
                        report_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        guild_id,
                        channel_id,
                        message_id,
                        datetime.now(timezone.utc).isoformat(),
                        json.dumps(transcript, ensure_ascii=False),
                        json.dumps(report, ensure_ascii=False),
                    ),
                )
                connection.execute(
                    """
                    DELETE FROM meeting_history
                    WHERE guild_id = ?
                      AND channel_id = ?
                      AND id NOT IN (
                          SELECT id
                          FROM meeting_history
                          WHERE guild_id = ? AND channel_id = ?
                          ORDER BY id DESC
                          LIMIT ?
                      )
                    """,
                    (
                        guild_id,
                        channel_id,
                        guild_id,
                        channel_id,
                        MAX_MEETINGS_PER_CHANNEL,
                    ),
                )

    def _recent_sync(
        self,
        guild_id: int,
        channel_id: int,
        limit: int,
    ) -> list[StoredMeeting]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT created_at, channel_id, message_id,
                       transcript_json, report_json
                FROM meeting_history
                WHERE guild_id = ? AND channel_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (guild_id, channel_id, limit),
            ).fetchall()

        return self._rows_to_meetings(rows)

    def _recent_for_guild_sync(
        self,
        guild_id: int,
        limit: int,
    ) -> list[StoredMeeting]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT created_at, channel_id, message_id,
                       transcript_json, report_json
                FROM meeting_history
                WHERE guild_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (guild_id, limit),
            ).fetchall()
        return self._rows_to_meetings(rows)

    @staticmethod
    def _rows_to_meetings(rows) -> list[StoredMeeting]:
        meetings: list[StoredMeeting] = []
        for (
            created_at,
            channel_id,
            message_id,
            transcript_json,
            report_json,
        ) in rows:
            try:
                meetings.append(
                    StoredMeeting(
                        created_at=created_at,
                        channel_id=channel_id,
                        message_id=message_id,
                        transcript=json.loads(transcript_json),
                        report=json.loads(report_json),
                    )
                )
            except (json.JSONDecodeError, TypeError):
                continue
        return meetings


meeting_memory_service = MeetingMemoryService()
