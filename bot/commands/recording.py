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


class RecordingCommands(commands.Cog):

    def __init__(
        self,
        bot: commands.Bot
    ):
        self.bot = bot

    # =====================================================
    # /record
    # =====================================================

    @app_commands.command(
        name="record",
        description=(
            "Thêm Trợ lý Kute vào voice "
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
                    "🔴 Trợ lý Kute đang ghi tại "
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
                f"Trợ lý Kute đang ghi lại cuộc trò chuyện "
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
            text="Trợ lý Kute • Meeting Assistant"
        )

        await interaction.followup.send(
            embed=embed
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

        embed.add_field(
            name="Trạng thái",
            value=(
                "✅ Audio đã lưu\n"
                "⏳ Chờ xử lý transcript"
            ),
            inline=False
        )

        embed.set_footer(
            text="Trợ lý Kute • Meeting Assistant"
        )

        await text_channel.send(
            embed=embed
        )

    # =====================================================
    # Auto stop khi tất cả human leave
    # =====================================================

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