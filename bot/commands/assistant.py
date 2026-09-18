import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord

from discord import app_commands
from discord.ext import commands

from bot.services.context_answering_service import (
    ContextAnswer,
    ContextAnsweringService,
    MAX_CONTEXT_CHARACTERS,
)
from bot.services.document_summarization_service import (
    DocumentExtractionError,
    DocumentSummarizationService,
    MAX_ATTACHMENT_BYTES,
    SUPPORTED_DOCUMENT_EXTENSIONS,
)
from bot.services.meeting_memory_service import meeting_memory_service


MAX_HISTORY_MESSAGES = 300
MAX_HISTORY_CHARACTERS = 10_000
MAX_SKYNET_SUMMARY_CHARACTERS = 14_000
MAX_FILE_CHARACTERS = 14_000
MAX_MEETING_CHARACTERS = 12_000
MAX_RECENT_FILES = 2
MAX_SERVER_SUMMARY_CHARACTERS = 16_000
MAX_SERVER_CHANNELS = 25
SERVER_TIMEZONE = timezone(timedelta(hours=7))


class MentionAssistant(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.answering_service = ContextAnsweringService()
        self._channel_locks: dict[int, asyncio.Lock] = {}

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[: limit - 1].rstrip() + "…"

    @staticmethod
    def _local_timestamp(value: datetime | str) -> str:
        try:
            parsed = (
                datetime.fromisoformat(value)
                if isinstance(value, str)
                else value
            )
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(SERVER_TIMEZONE).isoformat()
        except (TypeError, ValueError):
            return str(value)

    def _question_from_message(self, message: discord.Message) -> str:
        if self.bot.user is None:
            return ""
        question = message.content
        question = question.replace(f"<@{self.bot.user.id}>", "")
        question = question.replace(f"<@!{self.bot.user.id}>", "")
        return question.strip()

    @staticmethod
    def _meeting_embed_text(embed: discord.Embed) -> str:
        title = embed.title or ""
        field_names = " ".join(field.name for field in embed.fields)
        searchable = f"{title} {field_names}".lower()
        markers = (
            "meeting",
            "cuộc họp",
            "biên bản",
            "tóm tắt",
            "bản chép lời",
            "action item",
            "decision",
            "recording completed",
            "speakers",
            "unique attendees",
            "người tham dự",
        )
        if not any(marker in searchable for marker in markers):
            return ""

        parts = [title, embed.description or ""]
        parts.extend(
            f"{field.name}: {field.value}" for field in embed.fields
        )
        return "\n".join(part for part in parts if part).strip()

    @staticmethod
    def _message_resource_text(message: discord.Message) -> str:
        resources: list[str] = []
        message_url = getattr(message, "jump_url", "")

        for attachment in message.attachments:
            content_type = attachment.content_type or "unknown"
            resources.append(
                "Attachment: "
                f"name={attachment.filename}; "
                f"type={content_type}; "
                f"size={attachment.size} bytes; "
                f"download_url={attachment.url}; "
                f"message_url={message_url}"
            )

        for sticker in getattr(message, "stickers", []):
            resources.append(
                "Sticker: "
                f"name={sticker.name}; "
                f"url={sticker.url}; "
                f"message_url={message_url}"
            )

        for embed in message.embeds:
            urls: list[str] = []
            for candidate in (
                embed.url,
                getattr(embed.image, "url", None),
                getattr(embed.thumbnail, "url", None),
                getattr(embed.video, "url", None),
            ):
                if candidate and candidate not in urls:
                    urls.append(candidate)
            if not urls:
                continue
            resources.append(
                "Embedded media/link: "
                f"title={embed.title or 'Untitled'}; "
                f"urls={', '.join(urls)}; "
                f"message_url={message_url}"
            )

        if not resources:
            return ""
        return "Shared resources:\n" + "\n".join(
            f"- {resource}" for resource in resources
        )

    async def _document_context(
        self,
        attachments: list[discord.Attachment],
    ) -> tuple[list[str], list[str]]:
        sections: list[str] = []
        labels: list[str] = []
        remaining = MAX_FILE_CHARACTERS

        for attachment in attachments[:MAX_RECENT_FILES]:
            extension = Path(attachment.filename).suffix.lower()
            if remaining <= 0:
                continue

            label = f"File: {attachment.filename}"
            metadata = (
                f"[{label}]\n"
                f"Filename: {attachment.filename}\n"
                f"Content type: {attachment.content_type or 'unknown'}\n"
                f"Size: {attachment.size} bytes\n"
                f"Download URL: {attachment.url}"
            )
            text = metadata
            if (
                extension in SUPPORTED_DOCUMENT_EXTENSIONS
                and attachment.size <= MAX_ATTACHMENT_BYTES
            ):
                try:
                    content = await attachment.read()
                    document = DocumentSummarizationService.extract(
                        attachment.filename,
                        content,
                    )
                    text += f"\nExtracted content:\n{document.text}"
                except (DocumentExtractionError, discord.HTTPException):
                    pass

            text = self._truncate(text, remaining)
            sections.append(text)
            labels.append(label)
            remaining -= len(text)
        return sections, labels

    async def _meeting_context(
        self,
        guild: discord.Guild,
    ) -> tuple[list[str], list[str]]:
        meetings = await meeting_memory_service.recent_for_guild(
            guild_id=guild.id,
            limit=5,
        )
        sections: list[str] = []
        labels: list[str] = []
        remaining = MAX_MEETING_CHARACTERS

        for index, meeting in enumerate(meetings, start=1):
            if remaining <= 0:
                break
            report = meeting.report
            action_lines = []
            for item in report.get("action_items", []):
                action_lines.append(
                    "- Task: {task}; Owner: {owner}; Deadline: {deadline}; "
                    "Evidence: {evidence}".format(
                        task=item.get("task", ""),
                        owner=item.get("owner") or "Chưa xác định",
                        deadline=item.get("deadline") or "Chưa xác định",
                        evidence=item.get("evidence", ""),
                    )
                )
            topic_lines = []
            for section in report.get("sections", []):
                for point in section.get("points", []):
                    topic_lines.append(
                        f"- {section.get('title', 'Topic')}: "
                        f"{point.get('content', '')} "
                        f"(Evidence: {point.get('evidence', '')})"
                    )

            channel = guild.get_channel(meeting.channel_id)
            channel_name = getattr(channel, "name", str(meeting.channel_id))
            label = f"Meeting {index} in #{channel_name}"
            attendance = meeting.attendance
            participant_names = [
                participant.get("name", "Không rõ")
                for participant in attendance.get("participants", [])
            ]
            attendance_lines = (
                "Attendance:\n"
                f"- Unique attendees: {attendance.get('unique_count', 'unknown')}\n"
                f"- Present at start: {attendance.get('initial_count', 'unknown')}\n"
                f"- Peak simultaneous: {attendance.get('peak_count', 'unknown')}\n"
                f"- Participants: {', '.join(participant_names) or 'unknown'}\n"
                f"- Events: {attendance.get('events', [])}\n"
            )
            block = (
                f"[{label}]\n"
                f"Created (UTC+07:00): "
                f"{self._local_timestamp(meeting.created_at)}\n"
                + attendance_lines
                + f"Overview: {report.get('overview', '')}\n"
                "Action items:\n"
                + ("\n".join(action_lines) or "- Không ghi nhận")
                + "\nTopics:\n"
                + ("\n".join(topic_lines) or "- Không ghi nhận")
                + "\nTranscript:\n"
                + meeting.transcript.get("text", "")
            )
            block = self._truncate(block, remaining)
            sections.append(block)
            labels.append(label)
            remaining -= len(block)
        return sections, labels

    async def _history_context(
        self,
        channel,
        before: discord.Message | None = None,
    ) -> tuple[str, list[discord.Attachment]]:
        lines: list[str] = []
        skynet_summary_lines: list[str] = []
        recent_attachments: list[discord.Attachment] = []
        characters = 0
        summary_characters = 0

        try:
            history = channel.history(
                limit=MAX_HISTORY_MESSAGES,
                before=before,
                oldest_first=False,
            )
            async for historical_message in history:
                is_skynet_message = (
                    self.bot.user is not None
                    and historical_message.author.id == self.bot.user.id
                )
                if historical_message.author.bot and not is_skynet_message:
                    continue

                content_parts: list[str] = []
                if is_skynet_message:
                    for embed in historical_message.embeds:
                        embed_text = self._meeting_embed_text(embed)
                        if embed_text:
                            content_parts.append(embed_text)
                else:
                    content_parts.append(
                        historical_message.clean_content.strip()
                    )
                resource_text = self._message_resource_text(
                    historical_message
                )
                if resource_text:
                    content_parts.append(resource_text)
                content = "\n".join(
                    part for part in content_parts if part
                ).strip()
                if content:
                    timestamp = self._local_timestamp(
                        historical_message.created_at
                    )
                    line = (
                        f"{timestamp} | "
                        f"{historical_message.author.display_name}: {content}"
                    )
                    if is_skynet_message:
                        if (
                            summary_characters + len(line)
                            <= MAX_SKYNET_SUMMARY_CHARACTERS
                        ):
                            skynet_summary_lines.append(line)
                            summary_characters += len(line)
                    elif characters + len(line) <= MAX_HISTORY_CHARACTERS:
                        lines.append(line)
                        characters += len(line)

                for attachment in historical_message.attachments:
                    extension = Path(attachment.filename).suffix.lower()
                    if (
                        extension in SUPPORTED_DOCUMENT_EXTENSIONS
                        and attachment.size <= MAX_ATTACHMENT_BYTES
                        and len(recent_attachments) < MAX_RECENT_FILES
                    ):
                        recent_attachments.append(attachment)
        except (discord.Forbidden, discord.HTTPException):
            return "", []

        lines.reverse()
        skynet_summary_lines.reverse()
        if not lines and not skynet_summary_lines:
            return "", recent_attachments

        now = datetime.now(SERVER_TIMEZONE).isoformat()
        sections = [
            "[Chat history]",
            f"Current server time (UTC+07:00): {now}",
        ]
        if lines:
            sections.append("Recent human messages:\n" + "\n".join(lines))
        if skynet_summary_lines:
            sections.append(
                "Recent Skynet meeting summaries:\n"
                + "\n\n".join(skynet_summary_lines)
            )
        return "\n\n".join(sections), recent_attachments

    async def _server_summary_context(
        self,
        guild: discord.Guild,
        current_channel_id: int,
    ) -> tuple[list[str], list[str]]:
        if self.bot.user is None or guild.me is None:
            return [], []

        sections: list[str] = []
        labels: list[str] = []
        remaining = MAX_SERVER_SUMMARY_CHARACTERS
        channels_checked = 0

        for channel in guild.text_channels:
            if channel.id == current_channel_id or remaining <= 0:
                continue
            permissions = channel.permissions_for(guild.me)
            if not (
                permissions.view_channel
                and permissions.read_message_history
            ):
                continue
            channels_checked += 1
            if channels_checked > MAX_SERVER_CHANNELS:
                break

            channel_lines: list[str] = []
            try:
                async for historical_message in channel.history(
                    limit=MAX_HISTORY_MESSAGES,
                    oldest_first=False,
                ):
                    content_parts: list[str] = []
                    if historical_message.author.id == self.bot.user.id:
                        content_parts.extend(
                            self._meeting_embed_text(embed)
                            for embed in historical_message.embeds
                        )
                    resource_text = self._message_resource_text(
                        historical_message
                    )
                    if resource_text:
                        content_parts.append(resource_text)
                    content = "\n".join(
                        part for part in content_parts if part
                    ).strip()
                    if not content:
                        continue
                    timestamp = self._local_timestamp(
                        historical_message.created_at
                    )
                    line = (
                        f"{timestamp} | "
                        f"{historical_message.author.display_name}: {content}"
                    )
                    if len(line) > remaining:
                        line = self._truncate(line, remaining)
                    channel_lines.append(line)
                    remaining -= len(line)
                    if remaining <= 0:
                        break
            except (discord.Forbidden, discord.HTTPException):
                continue

            if channel_lines:
                channel_lines.reverse()
                label = f"Server meeting and files: #{channel.name}"
                sections.append(f"[{label}]\n" + "\n\n".join(channel_lines))
                labels.append(label)

        return sections, labels

    async def _collect_context(
        self,
        *,
        guild: discord.Guild,
        channel,
        direct_attachments: list[discord.Attachment],
        before: discord.Message | None = None,
    ) -> tuple[str, list[str]]:
        history_section, recent_files = await self._history_context(
            channel,
            before,
        )
        attachments = list(direct_attachments)
        attachment_ids = {item.id for item in attachments}
        attachments.extend(
            item for item in recent_files if item.id not in attachment_ids
        )
        file_sections, file_labels = await self._document_context(attachments)
        meeting_sections, meeting_labels = await self._meeting_context(
            guild,
        )
        server_sections, server_labels = await self._server_summary_context(
            guild,
            channel.id,
        )

        context_entries = list(zip(file_sections, file_labels))
        if history_section:
            context_entries.append((history_section, "Chat history"))
        context_entries.extend(zip(meeting_sections, meeting_labels))
        context_entries.extend(zip(server_sections, server_labels))

        included_sections: list[str] = []
        included_labels: list[str] = []
        remaining = MAX_CONTEXT_CHARACTERS
        for section, label in context_entries:
            if remaining <= 0:
                break
            separator_size = 2 if included_sections else 0
            available = remaining - separator_size
            if available <= 0:
                break
            bounded_section = self._truncate(section, available)
            included_sections.append(bounded_section)
            included_labels.append(label)
            remaining -= len(bounded_section) + separator_size

        return (
            "\n\n".join(included_sections),
            list(dict.fromkeys(included_labels)),
        )

    @staticmethod
    def _source_text(labels: list[str]) -> str:
        unique_labels = list(dict.fromkeys(labels))
        if not unique_labels:
            return "Không tìm thấy nguồn phù hợp trong channel này."
        return " • ".join(unique_labels)[:1024]

    def _answer_embed(
        self,
        result: ContextAnswer,
        checked_labels: list[str],
    ) -> discord.Embed:
        embed = discord.Embed(
            title=(
                "💬 Skynet trả lời"
                if result.supported
                else "🔎 Không đủ dữ liệu trong server"
            ),
            description=self._truncate(result.answer, 3900),
            color=(
                discord.Color.blurple()
                if result.supported
                else discord.Color.orange()
            ),
        )
        embed.add_field(
            name=(
                "Nguồn hỗ trợ câu trả lời"
                if result.supported
                else "Nguồn đã kiểm tra"
            ),
            value=self._source_text(
                result.sources if result.supported else checked_labels
            ),
            inline=False,
        )
        return embed

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or self.bot.user is None:
            return
        if self.bot.user not in message.mentions:
            return
        if message.guild is None:
            await message.reply(
                "Tôi chỉ trả lời câu hỏi dựa trên ngữ cảnh trong server Discord.",
                mention_author=False,
            )
            return

        question = self._question_from_message(message)
        if not question:
            await message.reply(
                "Hãy tag tôi kèm câu hỏi. Ví dụ: "
                "`@Skynet cuộc họp gần nhất giao việc gì cho Khoa?`",
                mention_author=False,
            )
            return

        lock = self._channel_locks.setdefault(message.channel.id, asyncio.Lock())
        if lock.locked():
            await message.reply(
                "Tôi đang xử lý một câu hỏi khác trong channel này. "
                "Vui lòng thử lại sau ít phút.",
                mention_author=False,
            )
            return

        async with lock:
            async with message.channel.typing():
                try:
                    context, labels = await self._collect_context(
                        guild=message.guild,
                        channel=message.channel,
                        direct_attachments=list(message.attachments),
                        before=message,
                    )
                    if not context:
                        await message.reply(
                            "Tôi không tìm thấy file, biên bản cuộc họp hoặc "
                            "lịch sử chat có thể đọc trong channel này.",
                            mention_author=False,
                        )
                        return

                    result = await self.answering_service.answer(
                        question,
                        context,
                        labels,
                    )
                except Exception as exc:
                    print("[MENTION ASSISTANT ERROR]", repr(exc))
                    await message.reply(
                        "Không thể trả lời lúc này. Hãy kiểm tra quyền "
                        "Read Message History và cấu hình LLM rồi thử lại.",
                        mention_author=False,
                    )
                    return

            await message.reply(
                embed=self._answer_embed(result, labels),
                mention_author=False,
            )

    @app_commands.command(
        name="ask",
        description="Hỏi AI bằng dữ liệu trong channel hiện tại",
    )
    @app_commands.guild_only()
    @app_commands.describe(
        question="Câu hỏi về file, meeting hoặc lịch sử chat trong channel",
        file="Tệp .txt, .md hoặc .docx liên quan (không bắt buộc)",
    )
    async def ask(
        self,
        interaction: discord.Interaction,
        question: str,
        file: discord.Attachment | None = None,
    ):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "Lệnh này chỉ sử dụng trong server Discord.",
                ephemeral=True,
            )
            return
        if not question.strip():
            await interaction.response.send_message(
                "Câu hỏi không được để trống.",
                ephemeral=True,
            )
            return
        if len(question) > 1500:
            await interaction.response.send_message(
                "Câu hỏi tối đa 1.500 ký tự.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        lock = self._channel_locks.setdefault(
            interaction.channel_id,
            asyncio.Lock(),
        )
        if lock.locked():
            await interaction.followup.send(
                "Tôi đang xử lý một câu hỏi khác trong channel này. "
                "Vui lòng thử lại sau ít phút.",
                ephemeral=True,
            )
            return

        async with lock:
            try:
                context, labels = await self._collect_context(
                    guild=interaction.guild,
                    channel=interaction.channel,
                    direct_attachments=[file] if file is not None else [],
                )
                result = await self.answering_service.answer(
                    question.strip(),
                    context,
                    labels,
                )
            except Exception as exc:
                print("[ASK COMMAND ERROR]", repr(exc))
                await interaction.followup.send(
                    "Không thể trả lời lúc này. Hãy kiểm tra quyền "
                    "Read Message History và cấu hình LLM rồi thử lại.",
                    ephemeral=True,
                )
                return

        await interaction.followup.send(
            embed=self._answer_embed(result, labels),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(MentionAssistant(bot))
