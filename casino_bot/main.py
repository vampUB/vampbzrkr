"""Entrypoint for the Telegram casino bot."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

if __package__ in {None, ""}:
    package_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(package_root.parent))
    __package__ = "casino_bot"

from .config import load_settings
from .crypto import CryptoBotClient
from .handlers import common, economy, games, progression
from .services.economy import EconomyService
from .services.games import build_registry
from .services.progression import ProgressionService
from .storage import CasinoStorage
from .utils.context import BotContext


async def main() -> None:
    settings = load_settings()
    storage = CasinoStorage(settings.database_url)
    await storage.connect()
    economy_service = EconomyService(
        storage,
        min_bet=settings.minimum_bet,
        max_bet=settings.maximum_bet,
    )
    crypto_client = CryptoBotClient(settings.cryptobot_token)
    games_registry = build_registry()
    progression_service = ProgressionService(storage)

    context = BotContext(
        storage=storage,
        economy=economy_service,
        games=games_registry,
        crypto=crypto_client,
        progression=progression_service,
        start_bonus=settings.start_bonus,
        daily_bonus=settings.daily_bonus_amount,
    )

    bot = Bot(settings.bot_token, parse_mode=ParseMode.HTML)

    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.data["context"] = context
    dispatcher.include_router(common.router)
    dispatcher.include_router(economy.router)
    dispatcher.include_router(games.router)
    dispatcher.include_router(progression.router)

    try:
        await dispatcher.start_polling(bot)
    finally:
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
