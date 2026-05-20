import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _read_env_file_value(name):
    env_path = BASE_DIR / ".env"

    if not env_path.exists():
        return ""

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)

        if key.strip() == name:
            return value.strip().strip('"').strip("'")

    return ""


def get_config_value(name):
    return (
        os.getenv(name, "").strip()
        or _read_env_file_value(name)
    )


def _read_token_file():
    token_path = BASE_DIR / "token.txt"

    if not token_path.exists():
        return ""

    return token_path.read_text(encoding="utf-8").strip()


def get_bot_token():
    return (
        get_config_value("TELEGRAM_BOT_TOKEN")
        or _read_token_file()
    )


def missing_token_message():
    return (
        "Missing Telegram bot token. Type it into BOT_TOKEN in main.py, set "
        "TELEGRAM_BOT_TOKEN, add TELEGRAM_BOT_TOKEN=your_token_here to .env, "
        "or put the token in token.txt."
    )
