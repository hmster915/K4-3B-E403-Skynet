import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

MEETING_CORE_ENV_VARS = (
    "ELEVENLABS_API_KEY",
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL",
)

if not DISCORD_TOKEN:
    raise RuntimeError("Thiếu DISCORD_TOKEN trong .env")


def validate_meeting_core_config() -> None:
    missing = [
        name
        for name in MEETING_CORE_ENV_VARS
        if not os.getenv(name, "").strip()
    ]
    if missing:
        raise RuntimeError(
            "Thiếu cấu hình Skynet Core trong .env: "
            + ", ".join(missing)
        )
