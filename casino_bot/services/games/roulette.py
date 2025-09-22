"""Roulette game implementation."""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Dict

from .base import GameContext, GameResult, GameStrategy


@dataclass(slots=True)
class Roulette(GameStrategy):
    name: str = "roulette"

    _colors: Dict[int, str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self._colors is None:
            reds = {
                1,
                3,
                5,
                7,
                9,
                12,
                14,
                16,
                18,
                19,
                21,
                23,
                25,
                27,
                30,
                32,
                34,
                36,
            }
            self._colors = {0: "green"}
            for number in range(1, 37):
                self._colors[number] = "red" if number in reds else "black"

    async def play(self, ctx: GameContext, *, choice: str = "red") -> GameResult:
        choice = choice.lower()
        if choice not in {"red", "black", "green"}:
            raise ValueError("Unsupported roulette bet")
        number = secrets.randbelow(37)
        color = self._colors[number]
        payout = 0
        if choice == "green":
            if number == 0:
                payout = ctx.bet * 14
        elif color == choice:
            payout = ctx.bet * 2
        display = (
            "🎡 Рулетка\n"
            f"Ставка: {ctx.bet} на {choice}. Выпало {number} ({color}).\n"
        )
        if payout:
            display += f"Выигрыш: {payout}!"
        else:
            display += "Не повезло в этот раз."
        state = {"number": number, "color": color, "choice": choice, "payout": payout}
        return GameResult(payout=payout, display=display, state=state)


__all__ = ["Roulette"]
