import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")

if not DISCORD_TOKEN:
    raise RuntimeError("Thiếu DISCORD_TOKEN trong .env")

if not DISCORD_GUILD_ID:
    raise RuntimeError("Thiếu DISCORD_GUILD_ID trong .env")

DISCORD_GUILD_ID = int(DISCORD_GUILD_ID)