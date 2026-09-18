import discord

from discord import app_commands
from discord.ext import commands

from bot.services.document_summarization_service import (
    DocumentExtractionError,
    DocumentSummarizationService,
    MAX_ATTACHMENT_BYTES,
)


class DocumentCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.summarizer = DocumentSummarizationService()

    @staticmethod
    def _truncate(value: str, limit: int = 3900) -> str:
        cleaned = value.strip()
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 1].rstrip() + "…"

    @app_commands.command(
        name="summarize-doc",
        description="Trích xuất và tóm tắt tệp TXT, Markdown hoặc DOCX",
    )
    @app_commands.describe(
        file="Tệp .txt, .md hoặc .docx cần tóm tắt",
    )
    async def summarize_document(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment,
    ):
        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )

        try:
            if file.size > MAX_ATTACHMENT_BYTES:
                raise DocumentExtractionError(
                    "Tệp phải nhỏ hơn hoặc bằng 8 MB."
                )
            content = await file.read()
            document = self.summarizer.extract(file.filename, content)
            summary = await self.summarizer.summarize(document)
        except DocumentExtractionError as exc:
            await interaction.followup.send(
                f"❌ {exc}",
                ephemeral=True,
            )
            return
        except Exception as exc:
            print("[DOCUMENT SUMMARY ERROR]", repr(exc))
            await interaction.followup.send(
                "❌ Không thể tóm tắt tài liệu lúc này. "
                "Vui lòng kiểm tra cấu hình LLM và thử lại.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="📄 Tóm tắt tài liệu",
            description=self._truncate(summary),
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Tệp nguồn",
            value=file.filename[:1024],
            inline=False,
        )
        if document.truncated:
            embed.add_field(
                name="Lưu ý",
                value=(
                    "Tài liệu dài hơn giới hạn xử lý; bản tóm tắt chỉ "
                    "dựa trên 40.000 ký tự đầu tiên."
                ),
                inline=False,
            )
        embed.set_footer(
            text="Kết quả riêng tư • Hãy kiểm tra lại với tài liệu gốc"
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(DocumentCommands(bot))
