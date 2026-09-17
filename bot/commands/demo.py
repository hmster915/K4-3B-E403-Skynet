import discord
from discord import app_commands
from discord.ext import commands


class DemoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(
        label="Xem chi tiết",
        style=discord.ButtonStyle.primary,
    )
    async def detail_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        embed = discord.Embed(
            title="Chi tiết cuộc họp",
            description=(
                "Mentor tập trung vào việc xác định rõ "
                "problem statement và scope của solution."
            ),
        )

        embed.add_field(
            name="Chủ đề chính",
            value="Problem validation",
            inline=False,
        )

        embed.add_field(
            name="Trạng thái",
            value="Đã tổng hợp",
            inline=True,
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    @discord.ui.button(
        label="Action Items",
        style=discord.ButtonStyle.success,
    )
    async def actions_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        embed = discord.Embed(
            title="Action Items"
        )

        embed.add_field(
            name="1. Problem Statement",
            value="Khoa — Viết lại problem statement",
            inline=False,
        )

        embed.add_field(
            name="2. Dataset",
            value="Team — Kiểm tra lại dataset",
            inline=False,
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )


class DemoCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="demo",
        description="Demo giao diện Trợ lý Kute",
    )
    async def demo(
        self,
        interaction: discord.Interaction,
    ):
        embed = discord.Embed(
            title="📋 Mentor Meeting",
            description=(
                "**17/09/2026**\n\n"
                "Buổi họp tập trung vào việc thu hẹp "
                "phạm vi bài toán và xác định hướng "
                "phát triển solution."
            ),
        )

        embed.add_field(
            name="🎯 Decisions",
            value=(
                "• Thu hẹp problem scope\n"
                "• Tập trung vào pain point cụ thể"
            ),
            inline=False,
        )

        embed.add_field(
            name="✅ Action Items",
            value=(
                "• Khoa — sửa problem statement\n"
                "• Team — kiểm tra dataset"
            ),
            inline=False,
        )

        embed.add_field(
            name="❓ Open Questions",
            value="• Benchmark AI output như thế nào?",
            inline=False,
        )

        embed.set_footer(
            text="Skynet Assistance"
        )

        await interaction.response.send_message(
            embed=embed,
            view=DemoView(),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(DemoCommands(bot))