import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path

import discord

from discord import app_commands
from discord.ext import commands, voice_recv

from skynet_core import MeetingCore

from bot.audio.recording_sink import (
    PerUserWaveSink,
)

from bot.config import validate_meeting_core_config

from bot.services.recording_manager import (
    RecordingSession,
    recording_manager,
)

from bot.services.meeting_processing_service import (
    MeetingProcessingService,
)
from bot.services.meeting_memory_service import meeting_memory_service


class MeetingSummaryView(discord.ui.View):
    """Render MeetingCoreResult fields as interactive Discord tabs."""

    def __init__(self, result):
        super().__init__(timeout=900)
        self.result = result
        self.active_tab = "summary"
        self._update_button_styles()

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[: limit - 1].rstrip() + "…"

    @classmethod
    def _readable_lines(
        cls,
        value: str,
        limit: int,
        empty_text: str,
    ) -> str:
        """Render paragraphs as one concise bullet per line."""
        parts = [
            part.strip()
            for part in re.split(r"(?:\r?\n)+|(?<=[.!?])\s+", value.strip())
            if part.strip()
        ]
        if not parts:
            return empty_text
        return cls._truncate(
            "\n".join(f"• {part}" for part in parts),
            limit,
        )

    def _update_button_styles(self):
        for button in self.children:
            tab_name = (button.custom_id or "").rsplit(":", 1)[-1]
            if tab_name in {"summary", "notes", "transcript"}:
                button.style = (
                    discord.ButtonStyle.primary
                    if tab_name == self.active_tab
                    else discord.ButtonStyle.secondary
                )

    def _set_active_tab(self, tab_name: str):
        self.active_tab = tab_name
        self._update_button_styles()

    def _summary_embed(self):
        report = self.result.report
        embed = discord.Embed(
            title="📋 Tóm tắt cuộc họp",
            description=self._readable_lines(
                report.overview,
                4096,
                "Không có nội dung tóm tắt.",
            ),
            color=discord.Color.blurple(),
        )

        attendance = self.result.attendance
        if attendance:
            participant_names = [
                participant.get("name", "Không rõ")
                for participant in attendance.get("participants", [])
            ]
            attendance_lines = [
                f"**Tham dự duy nhất:** {attendance.get('unique_count', 0)}",
                f"**Có mặt lúc bắt đầu:** {attendance.get('initial_count', 0)}",
                f"**Cao nhất cùng lúc:** {attendance.get('peak_count', 0)}",
            ]
            if participant_names:
                attendance_lines.append(
                    "**Thành viên:** " + ", ".join(participant_names)
                )
            embed.add_field(
                name="👥 Người tham dự",
                value=self._truncate("\n".join(attendance_lines), 1024),
                inline=False,
            )

        embed.add_field(
            name="✅ Action Items",
            value=self._action_items_text(report.action_items),
            inline=False,
        )

        for section in report.sections[:20]:
            points = [
                (
                    f"**{index}. Nội dung:** {point.content}\n"
                    f"**Bằng chứng:** {point.evidence}"
                )
                for index, point in enumerate(section.points, start=1)
            ]
            embed.add_field(
                name=self._truncate(f"🧩 {section.title}", 256),
                value=self._truncate(
                    "\n\n".join(points) or "Không ghi nhận",
                    1024,
                ),
                inline=False,
            )

        embed.set_footer(text="Skynet • AI Meeting Assistant")
        return embed

    def _notes_embed(self, user_id: int):
        notes = self.result.personal_notes.get(user_id, [])
        embed = discord.Embed(
            title="📝 Ghi chú cuộc họp",
            description="Ghi chú cá nhân của bạn trong cuộc họp này.",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="📌 Ghi chú cá nhân",
            value=self._truncate(
                "\n".join(
                    f"**{index}.** {note}"
                    for index, note in enumerate(notes, start=1)
                ) or "Không có ghi chú cá nhân.",
                1024,
            ),
            inline=False,
        )
        embed.set_footer(text="Chỉ bạn có thể xem nội dung này")
        return embed

    def _transcript_embed(self):
        transcript_text = self.result.transcript.text
        embed = discord.Embed(
            title="🗒️ Bản chép lời",
            description=self._readable_lines(
                transcript_text,
                3900,
                "Không có nội dung transcript.",
            ),
            color=discord.Color.orange(),
        )
        return embed

    @classmethod
    def _action_items_text(cls, action_items):
        if not action_items:
            return "Không ghi nhận"

        lines = []
        for index, item in enumerate(action_items, start=1):
            owner = item.owner or "Chưa xác định"
            deadline = item.deadline or "Chưa xác định"
            lines.append(
                f"**{index}. Công việc:** {item.task}\n"
                f"**Người phụ trách:** {owner}\n"
                f"**Hạn chót:** {deadline}\n"
                f"**Bằng chứng:** {item.evidence}"
            )
        return cls._truncate("\n\n".join(lines), 1024)

    @discord.ui.button(
        label="Tóm tắt",
        style=discord.ButtonStyle.primary,
        custom_id="meeting_summary:summary",
    )
    async def summary_tab(self, interaction: discord.Interaction, button):
        self._set_active_tab("summary")
        await interaction.response.edit_message(
            embed=self._summary_embed(),
            view=self,
        )

    @discord.ui.button(
        label="Ghi chú",
        style=discord.ButtonStyle.secondary,
        custom_id="meeting_summary:notes",
    )
    async def notes_tab(self, interaction: discord.Interaction, button):
        await interaction.response.send_message(
            embed=self._notes_embed(interaction.user.id),
            ephemeral=True,
        )

    @discord.ui.button(
        label="Bản chép lời",
        style=discord.ButtonStyle.secondary,
        custom_id="meeting_summary:transcript",
    )
    async def transcript_tab(self, interaction: discord.Interaction, button):
        self._set_active_tab("transcript")
        await interaction.response.edit_message(
            embed=self._transcript_embed(),
            view=self,
        )


class RecordingCommands(commands.Cog):

    def __init__(
        self,
        bot: commands.Bot
    ):
        self.bot = bot
        validate_meeting_core_config()
        self.meeting_core = MeetingCore.from_env()
        self.meeting_processor = MeetingProcessingService(
            self.meeting_core
        )

    # =====================================================
    # /record
    # =====================================================

    @app_commands.command(
        name="record",
        description=(
            "Thêm Skynet vào voice "
            "và bắt đầu ghi cuộc họp"
        )
    )
    async def record(
        self,
        interaction: discord.Interaction
    ):
        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "Lệnh này chỉ sử dụng trong server.",
                ephemeral=True
            )
            return

        # User phải đang ở voice
        user_voice = interaction.user.voice

        if (
            user_voice is None
            or user_voice.channel is None
        ):
            await interaction.response.send_message(
                (
                    "Bạn cần tham gia một voice channel "
                    "trước khi dùng `/record`."
                ),
                ephemeral=True
            )
            return

        # Guild đang record
        if recording_manager.is_recording(
            guild.id
        ):
            session = recording_manager.get(
                guild.id
            )

            channel = guild.get_channel(
                session.voice_channel_id
            )

            await interaction.response.send_message(
                (
                    "🔴 Skynet đang ghi tại "
                    f"**{channel.name}**."
                ),
                ephemeral=True
            )
            return

        voice_channel = user_voice.channel

        await interaction.response.defer()

        # Nếu bot đang nằm ở voice channel khác
        if guild.voice_client is not None:
            try:
                await guild.voice_client.disconnect(
                    force=True
                )
            except Exception:
                pass

        timestamp = datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%d-%H%M%S"
        )

        output_dir = (
            Path("recordings")
            / str(guild.id)
            / timestamp
        )

        sink = PerUserWaveSink(
            output_dir
        )

        try:
            voice_client = await voice_channel.connect(
                cls=voice_recv.VoiceRecvClient
            )

            voice_client.listen(
                sink
            )

        except Exception as exc:
            print(
                "[VOICE] Failed:",
                repr(exc)
            )

            await interaction.followup.send(
                (
                    "❌ Không thể bắt đầu recording.\n"
                    f"`{type(exc).__name__}: {exc}`"
                ),
                ephemeral=True
            )

            return

        started_at = datetime.now(timezone.utc)
        initial_humans = [
            member for member in voice_channel.members if not member.bot
        ]
        initial_participant_ids = {
            member.id for member in initial_humans
        }
        session = RecordingSession(
            guild_id=guild.id,
            voice_channel_id=voice_channel.id,
            text_channel_id=interaction.channel_id,

            started_by=interaction.user.id,

            started_at=started_at,

            output_dir=output_dir,

            voice_client=voice_client,
            sink=sink,
            participant_names={
                member.id: member.display_name
                for member in initial_humans
            },
            initial_participant_ids=initial_participant_ids,
            peak_participant_count=len(initial_humans),
            attendance_events=[
                {
                    "timestamp": started_at.isoformat(),
                    "event": "session_started",
                    "active_count": len(initial_humans),
                    "user_id": None,
                    "name": None,
                }
            ],
        )

        recording_manager.add(
            session
        )

        embed = discord.Embed(
            title="🔴 Recording started",
            description=(
                f"Skynet đang ghi lại cuộc trò chuyện "
                f"trong {voice_channel.mention}."
            )
        )

        embed.add_field(
            name="Bắt đầu bởi",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="Voice channel",
            value=voice_channel.mention,
            inline=True
        )

        embed.add_field(
            name="Cách kết thúc",
            value=(
                "Dùng `/end-record`\n"
                "hoặc bot tự kết thúc khi mọi người "
                "đã rời voice channel."
            ),
            inline=False
        )

        embed.add_field(
            name="Recording notice",
            value=(
                "Cuộc trò chuyện đang được ghi lại "
                "để tạo transcript và biên bản cuộc họp."
            ),
            inline=False
        )

        embed.set_footer(
            text="Skynet • Meeting Assistant"
        )

        await interaction.followup.send(
            embed=embed
        )

    # =====================================================
    # /note
    # =====================================================

    @app_commands.command(
        name="note",
        description="Lưu một ghi chú cá nhân cho cuộc họp đang diễn ra",
    )
    @app_commands.describe(
        content="Nội dung ghi chú của bạn",
    )
    async def note(
        self,
        interaction: discord.Interaction,
        content: str,
    ):
        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "Lệnh này chỉ sử dụng trong server.",
                ephemeral=True,
            )
            return

        session = recording_manager.get(guild.id)
        if session is None or session.ending:
            await interaction.response.send_message(
                "Hiện không có cuộc họp nào đang được ghi âm.",
                ephemeral=True,
            )
            return

        user_voice = getattr(interaction.user, "voice", None)
        if (
            user_voice is None
            or user_voice.channel is None
            or user_voice.channel.id != session.voice_channel_id
        ):
            await interaction.response.send_message(
                "Bạn cần ở trong voice channel của cuộc họp để dùng `/note`.",
                ephemeral=True,
            )
            return

        note_text = content.strip()
        if not note_text:
            await interaction.response.send_message(
                "Ghi chú không được để trống.",
                ephemeral=True,
            )
            return

        if len(note_text) > 1000:
            await interaction.response.send_message(
                "Ghi chú tối đa 1000 ký tự.",
                ephemeral=True,
            )
            return

        notes = session.personal_notes.setdefault(
            interaction.user.id,
            [],
        )
        notes.append(note_text)

        await interaction.response.send_message(
            f"Đã lưu ghi chú cá nhân số {len(notes)} cho cuộc họp.",
            ephemeral=True,
        )

    # =====================================================
    # /end-record
    # =====================================================

    @app_commands.command(
        name="end-record",
        description=(
            "Dừng ghi âm và kết thúc cuộc họp"
        )
    )
    async def end_record(
        self,
        interaction: discord.Interaction
    ):
        guild = interaction.guild

        if guild is None:
            return

        if not recording_manager.is_recording(
            guild.id
        ):
            await interaction.response.send_message(
                "Không có recording nào đang chạy.",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        await self.finish_recording(
            guild_id=guild.id,
            reason="manual"
        )

        await interaction.followup.send(
            "Recording đã được kết thúc."
        )

    # =====================================================
    # Central stop function
    # =====================================================

    async def finish_recording(
        self,
        guild_id: int,
        reason: str
    ):
        session = recording_manager.get(
            guild_id
        )

        if session is None or session.ending:
            return

        session.ending = True

        ended_at = datetime.now(timezone.utc)
        session.ended_at = ended_at
        guild = self.bot.get_guild(guild_id)
        voice_channel = (
            guild.get_channel(session.voice_channel_id)
            if guild is not None
            else None
        )
        active_humans = (
            [member for member in voice_channel.members if not member.bot]
            if voice_channel is not None
            else []
        )
        for active_member in active_humans:
            session.participant_names[
                active_member.id
            ] = active_member.display_name
        session.record_attendance_event(
            event="session_ended",
            active_count=len(active_humans),
            occurred_at=ended_at,
        )

        voice_client = session.voice_client

        try:

            if voice_client.is_listening():
                voice_client.stop_listening()

            # Chờ sink cleanup
            await asyncio.to_thread(
                session.sink.closed.wait,
                5
            )

        except Exception as exc:
            print(
                "[RECORD STOP]",
                repr(exc)
            )

        finally:

            if voice_client.is_connected():
                try:
                    await voice_client.disconnect(
                        force=True
                    )
                except Exception:
                    pass

        recording_manager.remove(
            guild_id
        )

        text_channel = self.bot.get_channel(
            session.text_channel_id
        )

        if text_channel is None:
            return

        duration = (
            datetime.now(timezone.utc)
            - session.started_at
        )

        total_seconds = int(
            duration.total_seconds()
        )

        minutes, seconds = divmod(
            total_seconds,
            60
        )

        files = session.sink.audio_files

        if reason == "manual":
            reason_text = "Lệnh `/end-record`"
        else:
            reason_text = (
                "Tất cả thành viên đã rời voice"
            )

        embed = discord.Embed(
            title="⏹️ Recording completed",
            description=(
                "Skynet đã kết thúc ghi âm "
                "và rời voice channel."
            )
        )

        embed.add_field(
            name="Thời lượng",
            value=f"{minutes:02d}:{seconds:02d}",
            inline=True
        )

        embed.add_field(
            name="Speakers",
            value=str(len(files)),
            inline=True
        )

        embed.add_field(
            name="Unique attendees",
            value=str(len(session.participant_names)),
            inline=True,
        )

        embed.add_field(
            name="Kết thúc bởi",
            value=reason_text,
            inline=False
        )

        if files:
            speaker_names = []

            for user_id in files:
                name = session.sink.user_names.get(
                    user_id,
                    str(user_id)
                )

                speaker_names.append(
                    f"• {name}"
                )

            embed.add_field(
                name="Đã ghi nhận",
                value="\n".join(
                    speaker_names
                ),
                inline=False
            )

        embed.set_footer(
            text="Skynet • Meeting Assistant"
        )

        await text_channel.send(
            embed=embed
        )

        asyncio.create_task(
            self.process_meeting(
                session=session,
                text_channel=text_channel,
            )
        )

    # =====================================================
    # Auto stop khi tất cả human leave
    # =====================================================

    # =====================================================
    # Process meeting: STT -> Summary
    # =====================================================

    async def process_meeting(
        self,
        session: RecordingSession,
        text_channel
    ):
        """
        Xử lý recording sau khi kết thúc:

        WAV files
            -> MeetingCore.process_wavs()
            -> MeetingCoreResult
            -> Discord meeting report
        """

        try:
            print(
                "[MEETING] Starting meeting processing..."
            )

            result = await self.meeting_processor.process(
                session
            )

            print(
                "[MEETING] Processing completed."
            )

            await self.send_meeting_summary(
                text_channel=text_channel,
                result=result
            )

        except Exception as exc:

            print(
                "[MEETING PROCESS ERROR]",
                repr(exc)
            )

            error_embed = discord.Embed(
                title="❌ Không thể xử lý cuộc họp",
                description=(
                    "Quá trình tạo transcript "
                    "hoặc summary gặp lỗi."
                )
            )

            error_embed.add_field(
                name="Error",
                value=(
                    f"`{type(exc).__name__}: {exc}`"
                ),
                inline=False
            )

            error_embed.set_footer(
                text="Skynet • Meeting Assistant"
            )

            await text_channel.send(
                embed=error_embed
            )

        # =====================================================
    # Discord Meeting Summary UI
    # =====================================================

    async def send_meeting_summary(
        self,
        text_channel,
        result,
    ):
        view = MeetingSummaryView(result)

        summary_message = await text_channel.send(
            embed=view._summary_embed(),
            view=view,
        )

        try:
            await meeting_memory_service.save(
                guild_id=text_channel.guild.id,
                channel_id=text_channel.id,
                message_id=summary_message.id,
                result=result,
            )
        except Exception as exc:
            print("[MEETING MEMORY ERROR]", repr(exc))

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ):
        # Không xử lý event của bot
        if member.bot:
            return

        guild = member.guild

        session = recording_manager.get(
            guild.id
        )

        if session is None or session.ending:
            return

        voice_channel_id = (
            session.voice_channel_id
        )

        # Chỉ quan tâm event liên quan
        # tới channel đang record
        before_id = (
            before.channel.id
            if before.channel
            else None
        )

        after_id = (
            after.channel.id
            if after.channel
            else None
        )

        if (
            before_id != voice_channel_id
            and after_id != voice_channel_id
        ):
            return

        voice_channel = guild.get_channel(voice_channel_id)
        humans_now = (
            [voice_member for voice_member in voice_channel.members if not voice_member.bot]
            if voice_channel is not None
            else []
        )
        if after_id == voice_channel_id and before_id != voice_channel_id:
            session.record_attendance_event(
                event="joined",
                active_count=len(humans_now),
                member_id=member.id,
                member_name=member.display_name,
            )
        elif before_id == voice_channel_id and after_id != voice_channel_id:
            session.record_attendance_event(
                event="left",
                active_count=len(humans_now),
                member_id=member.id,
                member_name=member.display_name,
            )

        # Grace period cho reconnect
        await asyncio.sleep(3)

        session = recording_manager.get(
            guild.id
        )

        if (
            session is None
            or session.ending
        ):
            return

        voice_channel = guild.get_channel(
            session.voice_channel_id
        )

        if voice_channel is None:
            return

        humans = [
            member
            for member in voice_channel.members
            if not member.bot
        ]

        if len(humans) == 0:
            print(
                "[RECORD] Voice channel empty. "
                "Auto stopping."
            )

            await self.finish_recording(
                guild_id=guild.id,
                reason="empty-channel"
            )


async def setup(
    bot: commands.Bot
):
    await bot.add_cog(
        RecordingCommands(bot)
    )
