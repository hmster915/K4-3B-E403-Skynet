import asyncio
from datetime import datetime, timezone
from pathlib import Path

import discord

from discord import app_commands
from discord.ext import commands, voice_recv

from bot.audio.recording_sink import (
    PerUserWaveSink,
)

from bot.services.recording_manager import (
    RecordingSession,
    recording_manager,
)

from bot.services.transcription_service import (
    TranscriptionService,
)

from bot.services.summarization_service import (
    SummarizationService,
)

from bot.services.meeting_processing_service import (
    MeetingProcessingService,
)


class MeetingSummaryView(discord.ui.View):
    """Interactive tabs for the generated meeting report."""

    def __init__(self, result):
        super().__init__(timeout=900)
        self.result = result
        self.active_tab = "summary"
        self._update_button_styles()

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

    @staticmethod
    def _bullet_list(items: list[str], empty_text: str = "Không ghi nhận"):
        if not items:
            return empty_text

        return "\n".join(f"• {item}" for item in items)

    def _summary_embed(self):
        summary = self.result.summary
        transcript = self.result.transcript

        embed = discord.Embed(
            title="📋 Tóm tắt cuộc họp",
            description=summary.summary or "Không có nội dung tóm tắt.",
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="🧩 Chủ đề chính",
            value=self._bullet_list(summary.topics),
            inline=False,
        )
        embed.add_field(
            name="🎯 Quyết định",
            value=self._bullet_list(summary.decisions),
            inline=False,
        )
        embed.add_field(
            name="✅ Action Items",
            value=self._action_items_text(summary.action_items),
            inline=False,
        )
        embed.add_field(
            name="💬 Transcript",
            value=(
                f"**{len(transcript)}** đoạn hội thoại | "
                f"**{self._speaker_count()}** speaker"
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
            value=self._bullet_list(notes),
            inline=False,
        )
        embed.set_footer(text="Skynet • AI Meeting Assistant")
        return embed

    def _transcript_embed(self):
        transcript = self.result.transcript
        lines = [
            f"**{segment.speaker_name}:** {segment.text}"
            for segment in transcript
        ]

        transcript_text = "\n\n".join(lines) or "Không có nội dung transcript."
        if len(transcript_text) > 3900:
            transcript_text = (
                transcript_text[:3900]
                + "\n\n… Transcript quá dài, chỉ hiển thị phần đầu."
            )

        embed = discord.Embed(
            title="🗒️ Bản chép lời",
            description=transcript_text,
            color=discord.Color.orange(),
        )
        embed.set_footer(
            text=(
                f"{len(transcript)} đoạn hội thoại • "
                f"{self._speaker_count()} speaker"
            )
        )
        return embed

    def _speaker_count(self):
        return len({segment.speaker_name for segment in self.result.transcript})

    @staticmethod
    def _action_items_text(action_items):
        if not action_items:
            return "Không ghi nhận"

        lines = []
        for item in action_items:
            owner = item.owner or "Chưa xác định"
            line = f"• **{owner}** — {item.task}"
            if item.deadline:
                line += f"\n  ↳ Deadline: {item.deadline}"
            lines.append(line)

        return "\n".join(lines)

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

        transcription_service = (
            TranscriptionService(
                mode="mock"
            )
        )

        summarization_service = (
            SummarizationService(
                mode="mock"
            )
        )

        self.meeting_processor = (
            MeetingProcessingService(
                transcription_service=
                    transcription_service,

                summarization_service=
                    summarization_service,
            )
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

        session = RecordingSession(
            guild_id=guild.id,
            voice_channel_id=voice_channel.id,
            text_channel_id=interaction.channel_id,

            started_by=interaction.user.id,

            started_at=datetime.now(
                timezone.utc
            ),

            output_dir=output_dir,

            voice_client=voice_client,
            sink=sink
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

        if session is None:
            return

        # Tránh /end-record + auto leave chạy cùng lúc
        if session.ending:
            return

        session.ending = True

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

        Audio
            -> TranscriptionService
            -> SummarizationService
            -> Discord Meeting Summary
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

    async def _legacy_send_meeting_summary(
        self,
        text_channel,
        result
    ):
        summary = result.summary
        transcript = result.transcript

        embed = discord.Embed(
            title="📋 Biên bản cuộc họp",
            description=(
                summary.summary
                or "Không có nội dung tóm tắt."
            )
        )

        # =========================
        # Topics
        # =========================

        topics_text = "\n".join(
            f"• {topic}"
            for topic in summary.topics
        )

        embed.add_field(
            name="🧩 Chủ đề chính",
            value=(
                topics_text
                or "Không ghi nhận"
            ),
            inline=False
        )

        # =========================
        # Decisions
        # =========================

        decisions_text = "\n".join(
            f"• {decision}"
            for decision in summary.decisions
        )

        embed.add_field(
            name="🎯 Quyết định",
            value=(
                decisions_text
                or "Không ghi nhận"
            ),
            inline=False
        )

        # =========================
        # Action items
        # =========================

        actions = []

        for item in summary.action_items:

            owner = (
                item.owner
                or "Chưa xác định"
            )

            action_text = (
                f"• **{owner}** — {item.task}"
            )

            if item.deadline:
                action_text += (
                    f"\n  ↳ Deadline: {item.deadline}"
                )

            actions.append(
                action_text
            )

        embed.add_field(
            name="✅ Action Items",
            value=(
                "\n".join(actions)
                or "Không ghi nhận"
            ),
            inline=False
        )

        # =========================
        # Open questions
        # =========================

        questions_text = "\n".join(
            f"• {question}"
            for question
            in summary.open_questions
        )

        embed.add_field(
            name="❓ Open Questions",
            value=(
                questions_text
                or "Không ghi nhận"
            ),
            inline=False
        )

        # =========================
        # Transcript info
        # =========================

        speakers = {
            segment.speaker_name
            for segment in transcript
        }

        embed.add_field(
            name="💬 Transcript",
            value=(
                f"**{len(transcript)}** đoạn hội thoại\n"
                f"**{len(speakers)}** speaker"
            ),
            inline=True
        )

        embed.set_footer(
            text="Skynet • AI Meeting Assistant"
        )

        await text_channel.send(
            embed=embed
        )

    async def send_meeting_summary(
        self,
        text_channel,
        result,
    ):
        view = MeetingSummaryView(result)

        await text_channel.send(
            embed=view._summary_embed(),
            view=view,
        )

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

        if session is None:
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
