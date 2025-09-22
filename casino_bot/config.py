"""Configuration management for the Telegram casino bot."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    bot_token: str = Field("TEST_TOKEN", env="BOT_TOKEN")
    database_url: str = Field("sqlite+aiosqlite:///./casino.db", env="DATABASE_URL")
    cryptobot_token: Optional[str] = Field(None, env="CRYPTOBOT_TOKEN")
    environment: Literal["development", "production", "test"] = Field(
        "development", env="APP_ENV"
    )
    start_bonus: int = Field(500, env="START_BONUS")
    daily_bonus_amount: int = Field(250, env="DAILY_BONUS")
    minimum_bet: int = Field(10, env="MIN_BET")
    maximum_bet: int = Field(10_000, env="MAX_BET")

    @validator("bot_token")
    def validate_token(cls, value: str) -> str:
        if not value:
            raise ValueError("BOT_TOKEN must be provided (can be a placeholder in dev)")
        return value

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def load_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


__all__ = ["Settings", "load_settings"]
