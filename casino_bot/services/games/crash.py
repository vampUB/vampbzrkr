"""Crash multiplier game."""
from __future__ import annotations

import random
from dataclasses import dataclass

from .base import GameContext, GameResult, GameStrategy


@dataclass(slots=True)
class Crash(GameStrategy):
    name: str = "crash"
    _rng: random.Random = random.SystemRandom()

    async def play(self, ctx: GameContext, **_: object) -> GameResult:
        crash_point = round(self._rng.uniform(1.0, 10.0), 2)
        auto_cashout = round(self._rng.uniform(1.3, 3.5), 2)
        if crash_point >= auto_cashout:
            multiplier = auto_cashout
            payout = int(ctx.bet * multiplier)
            outcome = "🚀 Вы успели выйти!"
        else:
            multiplier = crash_point
            payout = 0
            outcome = "💥 Кривая обрушилась до выхода."
        display = (
            "🚀 Crash\n"
            f"Авто-выход: x{auto_cashout:.2f}. Фактический максимум: x{crash_point:.2f}.\n"
            f"{outcome}"
        )
        state = {
            "auto_cashout": auto_cashout,
            "crash_point": crash_point,
            "multiplier": multiplier,
            "payout": payout,
        }
        return GameResult(payout=payout, display=display, state=state)


__all__ = ["Crash"]
