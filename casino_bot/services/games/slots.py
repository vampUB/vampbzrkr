"""Slot machine implementation."""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Dict, List

from .base import GameContext, GameResult, GameStrategy


@dataclass(slots=True)
class Symbol:
    emoji: str
    multiplier: int


SYMBOLS: List[Symbol] = [
    Symbol("🍒", 2),
    Symbol("🍋", 3),
    Symbol("🔔", 5),
    Symbol("⭐", 7),
    Symbol("7️⃣", 10),
]


class SlotMachine(GameStrategy):
    name = "slots"

    async def play(self, ctx: GameContext) -> GameResult:
        reels = [[secrets.choice(SYMBOLS) for _ in range(3)] for _ in range(3)]
        payout = self._calculate_payout(ctx.bet, reels)
        rows = ["".join(symbol.emoji for symbol in row) for row in reels]
        display = "🎰 Результат спина:\n" + "\n".join(rows)
        if payout:
            display += f"\nВы выиграли {payout} чипов!"
        else:
            display += "\nУдача отвернулась 😢"
        state: Dict[str, object] = {
            "bet": ctx.bet,
            "reels": [[symbol.emoji for symbol in row] for row in reels],
            "payout": payout,
        }
        return GameResult(payout=payout, display=display, state=state)

    def _calculate_payout(self, bet: int, reels: List[List[Symbol]]) -> int:
        base_multiplier = 0
        for row in reels:
            if row.count(row[0]) == 3:
                base_multiplier = max(base_multiplier, row[0].multiplier)
            if any(symbol.emoji == "7️⃣" for symbol in row):
                base_multiplier = max(base_multiplier, 5)
        if base_multiplier == 0:
            return 0
        return bet * base_multiplier


__all__ = ["SlotMachine", "SYMBOLS"]
