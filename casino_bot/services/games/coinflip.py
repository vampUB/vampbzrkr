"""Simple coin flip game."""
from __future__ import annotations

import secrets
from typing import Literal

from .base import GameContext, GameResult, GameStrategy

Choice = Literal["heads", "tails"]


class CoinFlip(GameStrategy):
    name = "coinflip"

    def __init__(self, payout_multiplier: float = 1.9) -> None:
        self.payout_multiplier = payout_multiplier

    async def play(self, ctx: GameContext, *, choice: Choice) -> GameResult:
        outcome = secrets.choice(["heads", "tails"])
        win = outcome == choice
        payout = int(ctx.bet * self.payout_multiplier) if win else 0
        display = (
            f"🪙 Монета: {'Орёл' if outcome == 'heads' else 'Решка'}\n"
            f"Ваш выбор: {'Орёл' if choice == 'heads' else 'Решка'}\n"
            f"{'Победа!' if win else 'Проигрыш'}"
        )
        state = {
            "bet": ctx.bet,
            "choice": choice,
            "outcome": outcome,
            "win": win,
            "payout_multiplier": self.payout_multiplier,
        }
        return GameResult(payout=payout, display=display, state=state)


__all__ = ["CoinFlip", "Choice"]
