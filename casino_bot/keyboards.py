"""Inline keyboards for bot interactions."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎮 Играть", callback_data="menu:play"),
                InlineKeyboardButton(text="👤 Профиль", callback_data="menu:profile"),
            ],
            [
                InlineKeyboardButton(text="🎁 Бонус", callback_data="menu:daily"),
                InlineKeyboardButton(text="💰 Пополнить", callback_data="menu:deposit"),
            ],
            [
                InlineKeyboardButton(text="🔥 Миссии", callback_data="menu:missions"),
                InlineKeyboardButton(text="🏆 Лидерборд", callback_data="menu:leaderboard"),
            ],
        ]
    )


def game_selection() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎰 Слоты", callback_data="game:slots")],
            [InlineKeyboardButton(text="🪙 Монетка", callback_data="game:coinflip")],
            [InlineKeyboardButton(text="🃏 Блэкджек", callback_data="game:blackjack")],
            [InlineKeyboardButton(text="🎡 Рулетка", callback_data="game:roulette")],
            [InlineKeyboardButton(text="🎲 Кости", callback_data="game:dice")],
            [InlineKeyboardButton(text="🚀 Крэш", callback_data="game:crash")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")],
        ]
    )


def coinflip_choice() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Орёл", callback_data="coin:heads")],
            [InlineKeyboardButton(text="Решка", callback_data="coin:tails")],
        ]
    )


def blackjack_actions(double_available: bool) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Ещё", callback_data="bj:hit")],
        [InlineKeyboardButton(text="Хватит", callback_data="bj:stand")],
    ]
    if double_available:
        buttons.insert(1, [InlineKeyboardButton(text="Удвоить", callback_data="bj:double")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def roulette_choice() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔴 Красное", callback_data="roulette:red")],
            [InlineKeyboardButton(text="⚫️ Чёрное", callback_data="roulette:black")],
            [InlineKeyboardButton(text="🟢 Зеро", callback_data="roulette:green")],
        ]
    )


def bet_shortcuts() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="100", callback_data="bet:100"), InlineKeyboardButton(text="250", callback_data="bet:250")],
            [InlineKeyboardButton(text="500", callback_data="bet:500"), InlineKeyboardButton(text="1000", callback_data="bet:1000")],
            [InlineKeyboardButton(text="Другая сумма", callback_data="bet:custom")],
        ]
    )


__all__ = [
    "main_menu",
    "game_selection",
    "coinflip_choice",
    "blackjack_actions",
    "roulette_choice",
    "bet_shortcuts",
]
