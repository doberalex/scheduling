import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*args, **kwargs):
        return False


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow").strip()
DB_HOST = os.getenv("DB_HOST", "localhost").strip()
DB_PORT = int(os.getenv("DB_PORT", "3306").strip())
DB_USER = os.getenv("DB_USER", "doberalex_tbotschedule").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip()
DB_NAME = os.getenv("DB_NAME", "doberalex_tbotschedule").strip()


def parse_admin_ids(value: str) -> set[int]:
    ids = set()

    for part in value.split(","):
        part = part.strip()

        if part:
            ids.add(int(part))

    return ids


ADMIN_IDS = parse_admin_ids(os.getenv("ADMIN_IDS", ""))
