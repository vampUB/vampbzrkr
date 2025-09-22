"""Static configuration for the Telegram casino bot."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, Optional


@dataclass(frozen=True)
class Settings:
    """Application configuration loaded from :mod:`casino_bot.config`."""

    bot_token: str
    database_url: str = "sqlite+aiosqlite:///./casino.db"
    cryptobot_token: Optional[str] = None
    environment: Literal["development", "production", "test"] = "development"
    start_bonus: int = 500
    daily_bonus_amount: int = 250
    minimum_bet: int = 10
    maximum_bet: int = 10_000


#: Base configuration. Update these values to match your environment.
CONFIG: dict[str, object] = {
    "bot_token": "TEST_TOKEN",  # Replace with the bot token from @BotFather
    "database_url": "sqlite+aiosqlite:///./casino.db",
    "cryptobot_token": None,  # Optional token from @CryptoBot
    "environment": "development",
    "start_bonus": 500,
    "daily_bonus_amount": 250,
    "minimum_bet": 10,
    "maximum_bet": 10_000,
}


@lru_cache()
def load_settings() -> Settings:
    """Return cached settings instance built from :data:`CONFIG`."""

    return Settings(**CONFIG)  # type: ignore[arg-type]


__all__ = ["Settings", "load_settings", "CONFIG"]
