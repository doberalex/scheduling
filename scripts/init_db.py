import asyncio
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.settings_store import close_db, init_db, load_settings


async def main() -> None:
    await init_db()
    settings = await load_settings()
    print(f"Database is ready. Participants: {len(settings['people'])}")
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
