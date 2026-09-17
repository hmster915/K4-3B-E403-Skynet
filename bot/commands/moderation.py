import discord

from discord import app_commands
from discord.ext import commands


class ModerationCommands(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="kick",
        description="Kick một thành viên khỏi server",
    )
    @app_commands.describe(
        member="Thành viên cần kick",
        reason="Lý do kick",
    )
    @app_commands.default_permissions(
        kick_members=True
    )
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Không có lý do",
    ):
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "Bạn không thể kick người có vai trò "
                "bằng hoặc cao hơn bạn!",
                ephemeral=True,
            )
            return

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "Bot không thể kick người này vì vai trò "
                "của họ cao hơn vai trò của bot!",
                ephemeral=True,
            )
            return

        await member.kick(reason=reason)

        await interaction.response.send_message(
            f"Đã kick **{member.display_name}** khỏi server. "
            f"Lý do: {reason}"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(
        ModerationCommands(bot)
    )