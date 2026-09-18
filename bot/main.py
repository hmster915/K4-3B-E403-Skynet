import discord
from discord.ext import commands

from bot.config import DISCORD_TOKEN


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True


class KuteBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

        self._commands_synced = False

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

bot = KuteBot()


@bot.event
async def on_ready():
    if not bot._commands_synced:
        total = 0

        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            total += len(synced)

            print(
                f"[SYNC] Synced {len(synced)} commands "
                f"to guild {guild.name} ({guild.id})"
            )

        bot._commands_synced = True
        print(
            f"[SYNC] Synced commands to {len(bot.guilds)} guild(s) "
            f"({total} total command entries)"
        )

    print(
        f"[READY] Bot online: {bot.user} "
        f"(ID: {bot.user.id})"
    )


def main():
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
