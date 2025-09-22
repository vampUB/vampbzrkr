"""Dice duel against the house."""
from __future__ import annotations

import secrets
from dataclasses import dataclass

from .base import GameContext, GameResult, GameStrategy


@dataclass(slots=True)
class DiceDuel(GameStrategy):
    name: str = "dice"

    async def play(self, ctx: GameContext, **_: object) -> GameResult:
        player_roll = secrets.randbelow(6) + 1
        dealer_roll = secrets.randbelow(6) + 1
        if player_roll > dealer_roll:
            payout = ctx.bet * 2
            summary = "Вы победили дилера!"
        elif player_roll == dealer_roll:
            payout = ctx.bet
            summary = "Ничья — ставка возвращена."
        else:
            payout = 0
            summary = "Дилер оказался сильнее."
        display = (
            "🎲 Бросок костей\n"
            f"Вы: {player_roll}. Дилер: {dealer_roll}.\n"
            f"{summary}"
        )
        state = {
            "player_roll": player_roll,
            "dealer_roll": dealer_roll,
            "payout": payout,
        }
        return GameResult(payout=payout, display=display, state=state)


__all__ = ["DiceDuel"]
