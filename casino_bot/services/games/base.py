"""Base classes for casino games."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Protocol


@dataclass(slots=True)
class GameContext:
    user_id: int
    bet: int


@dataclass(slots=True)
class GameResult:
    payout: int
    display: str
    state: Dict[str, object]

    @property
    def net(self) -> int:
        return self.payout - self.state.get("bet", 0) if "bet" in self.state else 0


class GameStrategy(Protocol):
    name: str

    async def play(self, ctx: GameContext, **kwargs) -> GameResult:
        ...


class GameRegistry:
    """Registry for available game strategies."""

    def __init__(self) -> None:
        self._games: Dict[str, GameStrategy] = {}

    def register(self, game: GameStrategy) -> None:
        if game.name in self._games:
            raise ValueError(f"Game '{game.name}' already registered")
        self._games[game.name] = game

    def get(self, name: str) -> GameStrategy:
        try:
            return self._games[name]
        except KeyError as exc:
            raise KeyError(f"Game '{name}' is not registered") from exc

    def all(self) -> Dict[str, GameStrategy]:
        return dict(self._games)


__all__ = ["GameContext", "GameResult", "GameStrategy", "GameRegistry"]
