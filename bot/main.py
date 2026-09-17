import discord
from discord.ext import commands

from bot.config import DISCORD_TOKEN, DISCORD_GUILD_ID


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True


class KuteBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        extensions = [
            "bot.commands.general",
            "bot.commands.moderation",
            "bot.commands.demo",
            "bot.commands.recording",
        ]

        for extension in extensions:
            try:
                await self.load_extension(extension)
                print(f"[OK] Loaded extension: {extension}")
            except Exception as e:
                print(f"[ERROR] Failed to load {extension}: {e}")
                raise

        guild = discord.Object(id=DISCORD_GUILD_ID)

        # Copy các global command vào server test
        self.tree.copy_global_to(guild=guild)

        synced = await self.tree.sync(guild=guild)

        print(
            f"[SYNC] Đã đồng bộ {len(synced)} commands "
            f"vào guild {DISCORD_GUILD_ID}"
        )

        for command in synced:
            print(f"   /{command.name}")


bot = KuteBot()


@bot.event
async def on_ready():
    print(
        f"[READY] Bot online: {bot.user} "
        f"(ID: {bot.user.id})"
    )


def main():
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()