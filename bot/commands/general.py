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