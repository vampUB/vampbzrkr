"""Blackjack game logic."""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Dict, List

from .base import GameContext, GameResult, GameStrategy

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
VALUES = {"A": 11, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10, "J": 10, "Q": 10, "K": 10}


@dataclass(slots=True)
class Card:
    rank: str
    suit: str

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


@dataclass(slots=True)
class BlackjackRound:
    bet: int
    deck: List[Card] = field(default_factory=list)
    player_hand: List[Card] = field(default_factory=list)
    dealer_hand: List[Card] = field(default_factory=list)
    doubled: bool = False
    finished: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "bet": self.bet,
            "player": [str(card) for card in self.player_hand],
            "dealer": [str(card) for card in self.dealer_hand],
            "doubled": self.doubled,
            "finished": self.finished,
        }


class Blackjack(GameStrategy):
    name = "blackjack"

    def __init__(self) -> None:
        self._rng = secrets.SystemRandom()

    async def play(self, ctx: GameContext) -> GameResult:
        round_state = self.new_round(ctx.bet)
        return self.finish_round(round_state)

    def new_round(self, bet: int) -> BlackjackRound:
        deck = [Card(rank, suit) for rank in RANKS for suit in SUITS]
        self._rng.shuffle(deck)
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        round_state = BlackjackRound(bet=bet, deck=deck, player_hand=player_hand, dealer_hand=dealer_hand)
        if self._is_blackjack(round_state.player_hand) or self._is_blackjack(round_state.dealer_hand):
            round_state.finished = True
        return round_state

    def player_hit(self, round_state: BlackjackRound) -> None:
        if round_state.finished:
            return
        round_state.player_hand.append(round_state.deck.pop())
        if self._hand_value(round_state.player_hand)[0] > 21:
            round_state.finished = True

    def player_double(self, round_state: BlackjackRound) -> None:
        if round_state.finished or round_state.doubled:
            return
        round_state.doubled = True
        round_state.bet *= 2
        self.player_hit(round_state)
        round_state.finished = True

    def player_stand(self, round_state: BlackjackRound) -> None:
        if round_state.finished:
            return
        round_state.finished = True

    def finish_round(self, round_state: BlackjackRound) -> GameResult:
        player_value, player_soft = self._hand_value(round_state.player_hand)
        dealer_value, dealer_soft = self._hand_value(round_state.dealer_hand)
        if player_value <= 21 and not (self._is_blackjack(round_state.player_hand) and self._is_blackjack(round_state.dealer_hand)):
            dealer_value, dealer_soft = self._dealer_play(round_state, initial_value=dealer_value, initial_soft=dealer_soft)
        if player_value > 21:
            payout = 0
            outcome = "Перебор! Вы проиграли."
        elif dealer_value > 21:
            payout = round_state.bet * 2
            outcome = "Дилер перебрал. Победа!"
        else:
            if player_value > dealer_value:
                if self._is_blackjack(round_state.player_hand) and not self._is_blackjack(round_state.dealer_hand):
                    payout = int(round_state.bet * 2.5)
                    outcome = "Блэкджек! Выплата 3:2"
                else:
                    payout = round_state.bet * 2
                    outcome = "Вы ближе к 21. Победа!"
            elif player_value == dealer_value:
                payout = round_state.bet
                outcome = "Ничья. Ставка возвращена."
            else:
                payout = 0
                outcome = "Дилер ближе к 21. Проигрыш."
        display = (
            "🃏 Блэкджек\n"
            f"Ваши карты ({player_value}{' мягко' if player_soft else ''}): "
            f"{' '.join(str(card) for card in round_state.player_hand)}\n"
            f"Карты дилера ({dealer_value}{' мягко' if dealer_soft else ''}): {' '.join(str(card) for card in round_state.dealer_hand)}\n"
            f"{outcome}"
        )
        state = round_state.to_dict()
        state.update({"player_value": player_value, "dealer_value": dealer_value, "outcome": outcome, "payout": payout})
        return GameResult(payout=payout, display=display, state=state)

    def _dealer_play(self, round_state: BlackjackRound, *, initial_value: int, initial_soft: bool) -> tuple[int, bool]:
        value = initial_value
        soft = initial_soft
        while value < 17 and round_state.deck:
            round_state.dealer_hand.append(round_state.deck.pop())
            value, soft = self._hand_value(round_state.dealer_hand)
        return value, soft

    def _hand_value(self, hand: List[Card]) -> tuple[int, bool]:
        value = 0
        aces = 0
        for card in hand:
            value += VALUES[card.rank]
            if card.rank == "A":
                aces += 1
        soft = False
        while value > 21 and aces:
            value -= 10
            aces -= 1
        if aces:
            soft = True
        return value, soft

    def _is_blackjack(self, hand: List[Card]) -> bool:
        return len(hand) == 2 and self._hand_value(hand)[0] == 21


__all__ = ["Blackjack", "BlackjackRound", "Card"]
