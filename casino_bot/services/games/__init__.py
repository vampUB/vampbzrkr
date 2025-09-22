"""Game registry utilities."""
from __future__ import annotations

from .base import GameContext, GameRegistry, GameResult, GameStrategy
from .blackjack import Blackjack
from .coinflip import CoinFlip
from .crash import Crash
from .dice import DiceDuel
from .roulette import Roulette
from .slots import SlotMachine


def build_registry() -> GameRegistry:
    registry = GameRegistry()
    registry.register(SlotMachine())
    registry.register(CoinFlip())
    registry.register(Blackjack())
    registry.register(Roulette())
    registry.register(DiceDuel())
    registry.register(Crash())
    return registry


__all__ = [
    "GameContext",
    "GameRegistry",
    "GameResult",
    "GameStrategy",
    "build_registry",
]
