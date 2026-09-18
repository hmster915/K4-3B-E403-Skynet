import discord

from discord import app_commands
from discord.ext import commands


class GeneralCommands(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="ping",
        description="Kiểm tra độ trễ của bot",
    )
    async def ping(
        self,
        interaction: discord.Interaction,
    ):
        latency = round(self.bot.latency * 1000)

        await interaction.response.send_message(
            f"Pong! Độ trễ: {latency}ms"
        )

    @app_commands.command(
        name="help",
        description="Hiển thị hướng dẫn sử dụng Skynet",
    )
    async def help_command(
        self,
        interaction: discord.Interaction,
    ):
        embed = discord.Embed(
            title="📘 Hướng dẫn sử dụng Skynet",
            description=(
                "Skynet hỗ trợ ghi âm cuộc họp, tạo biên bản, "
                "ghi chú cá nhân và tóm tắt tài liệu."
            ),
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="🎙️ Ghi và tóm tắt cuộc họp",
            value=(
                "**1.** Vào một voice channel.\n"
                "**2.** Dùng `/record` để bắt đầu ghi.\n"
                "**3.** Dùng `/note <nội dung>` để lưu ghi chú cá nhân.\n"
                "**4.** Dùng `/end-record` để kết thúc và xử lý.\n"
                "**5.** Xem kết quả tại các tab **Tóm tắt**, "
                "**Ghi chú** và **Bản chép lời**."
            ),
            inline=False,
        )
        embed.add_field(
            name="📄 Tóm tắt tài liệu",
            value=(
                "Dùng `/summarize-doc file:<tệp>` rồi tải lên tệp "
                "`.txt`, `.md` hoặc `.docx`.\n"
                "Kết quả chỉ hiển thị cho người gọi lệnh."
            ),
            inline=False,
        )
        embed.add_field(
            name="💬 Hỏi AI trong ngữ cảnh server",
            value=(
                "Dùng `/ask question:<câu hỏi>` hoặc tag `@Skynet` để hỏi "
                "về file, biên bản cuộc họp trong các channel bot đọc được "
                "trên server và tối đa 300 tin nhắn gần nhất trong channel "
                "hiện tại.\n"
                "Ví dụ: `@Skynet cuộc họp gần nhất giao việc gì cho Khoa?`\n"
                "Ví dụ: `@Skynet cuộc họp gần nhất có bao nhiêu người tham dự?`\n"
                "Có thể đính kèm file `.txt`, `.md` hoặc `.docx`.\n"
                "Bot cũng có thể tìm vị trí và link của file ZIP, ảnh, audio, "
                "video, sticker và media khác đã gửi trong server.\n"
                "Nếu server không có bằng chứng, bot sẽ từ chối trả lời thay "
                "vì dùng kiến thức bên ngoài."
            ),
            inline=False,
        )
        embed.add_field(
            name="🛠️ Lệnh tiện ích",
            value=(
                "`/ping` — kiểm tra độ trễ của bot.\n"
                "`/chao` — gửi lời chào đến thành viên.\n"
                "`/demo` — xem giao diện demo của biên bản.\n"
                "`/help` — mở hướng dẫn này."
            ),
            inline=False,
        )
        embed.add_field(
            name="🔒 Quyền riêng tư và lưu ý",
            value=(
                "• Hãy thông báo cho mọi người trước khi ghi âm.\n"
                "• Ghi chú từ `/note` chỉ người tạo mới xem được.\n"
                "• Luôn kiểm tra bằng chứng và bản chép lời trước khi "
                "dùng action item, owner hoặc deadline."
            ),
            inline=False,
        )
        embed.set_footer(text="Skynet • Meeting Assistant")

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    @app_commands.command(
        name="chao",
        description="Gửi lời chào tới một người bạn",
    )
    @app_commands.describe(
        member="Chọn người bạn muốn chào",
        message="Lời nhắn kèm theo",
    )
    async def chao(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        message: str = "Chào bạn nha!",
    ):
        await interaction.response.send_message(
            f"{interaction.user.mention} gửi lời chào đến "
            f"{member.mention}: {message}"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(GeneralCommands(bot))
