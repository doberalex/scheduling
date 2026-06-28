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
DATA_FILE = Path(os.getenv("DATA_FILE", "data/settings.json"))

if not DATA_FILE.is_absolute():
    DATA_FILE = BASE_DIR / DATA_FILE


def parse_admin_ids(value: str) -> set[int]:
    ids = set()

    for part in value.split(","):
        part = part.strip()

        if part:
            ids.add(int(part))

    return ids


ADMIN_IDS = parse_admin_ids(os.getenv("ADMIN_IDS", ""))
