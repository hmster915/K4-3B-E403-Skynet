import discord
from discord.ext import commands

from bot.config import DISCORD_TOKEN


intents = discord.Intents.default()
intents.message_content = True


class KuteBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
        )

    async def setup_hook(self):
        await self.load_extension("bot.commands.general")
        await self.load_extension("bot.commands.moderation")

        # Các command UI/demo của bạn
        await self.load_extension("bot.commands.demo")

        await self.tree.sync()

        print("Đã đồng bộ Slash Commands!")


bot = KuteBot()


@bot.event
async def on_ready():
    print(
        f"Bot đã online: {bot.user} "
        f"(ID: {bot.user.id})"
    )


def main():
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()