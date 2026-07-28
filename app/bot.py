import socket

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiohttp.resolver import DefaultResolver

from app.config import BOT_TOKEN
from app.handlers import router
from app.services.settings_store import close_db, init_db


TELEGRAM_API_IP = "149.154.167.220"


class TelegramIPv4Resolver:
    def __init__(self) -> None:
        self._default = DefaultResolver()

    async def resolve(
        self,
        host: str,
        port: int = 0,
        family: socket.AddressFamily = socket.AF_INET,
    ) -> list[dict]:
        if host == "api.telegram.org":
            return [
                {
                    "hostname": host,
                    "host": TELEGRAM_API_IP,
                    "port": port,
                    "family": socket.AF_INET,
                    "proto": socket.IPPROTO_TCP,
                    "flags": 0,
                }
            ]

        return await self._default.resolve(host, port, family)

    async def close(self) -> None:
        await self._default.close()


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is empty. Create .env from .env.example.")

    session = AiohttpSession()
    session._connector_init["family"] = socket.AF_INET
    session._connector_init["resolver"] = TelegramIPv4Resolver()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )
    dp = Dispatcher()
    dp.include_router(router)

    await init_db()

    try:
        await dp.start_polling(bot)
    finally:
        await close_db()
