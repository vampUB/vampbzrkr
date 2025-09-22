"""Shared context object passed around the bot."""
from __future__ import annotations

from dataclasses import dataclass

from ..crypto import CryptoBotClient
from ..services.economy import EconomyService
from ..services.games import GameRegistry
from ..services.progression import ProgressionService
from ..storage import CasinoStorage


@dataclass(slots=True)
class BotContext:
    storage: CasinoStorage
    economy: EconomyService
    games: GameRegistry
    crypto: CryptoBotClient
    progression: ProgressionService
    start_bonus: int
    daily_bonus: int


__all__ = ["BotContext"]
