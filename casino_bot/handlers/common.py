"""Common command handlers."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional


from aiogram import Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from ..keyboards import main_menu
from ..utils.context import BotContext

router = Router()


def _get_context(dispatcher: Dispatcher) -> BotContext:
    ctx: Optional[BotContext] = dispatcher.data.get("context")  # type: ignore[assignment]
    if ctx is None:
        raise RuntimeError("Bot context is not initialised")
    return ctx


async def _format_profile(ctx: BotContext, user_id: int) -> str:
    wallet = await ctx.economy.get_wallet(user_id)
    overview = await ctx.progression.get_profile(user_id)
    transactions = await ctx.storage.get_recent_transactions(user_id)
    games = await ctx.storage.get_recent_games(user_id)
    win_rate = (
        overview.stats.wins / overview.stats.games_played * 100
        if overview.stats.games_played
        else 0
    )
    lines = [
        f"Баланс: {wallet.balance} чипов",
        f"Уровень: {overview.level} (до следующего: {overview.xp_to_next} XP)",
        f"Клуб лояльности: {overview.loyalty_tier.name} x{overview.loyalty_tier.bonus_multiplier:.2f}",
        f"Сыграно раундов: {overview.stats.games_played}",
        f"Винрейт: {win_rate:.1f}%",
        f"Суммарно поставлено: {overview.stats.total_wagered}",
        f"Суммарно выиграно: {overview.stats.total_won}",
        f"Лучший выигрыш за раунд: {overview.stats.biggest_win}",
        f"Достижений: {len(overview.achievements)}",
    ]
    if wallet.last_daily_bonus:
        next_bonus = wallet.last_daily_bonus + timedelta(hours=24)
        if next_bonus > datetime.utcnow():
            remaining = next_bonus - datetime.utcnow()
            lines.append(
                "Следующий ежедневный бонус через: "
                f"{remaining.seconds // 3600}ч {(remaining.seconds // 60) % 60}м"
            )
        else:
            lines.append("Ежедневный бонус доступен!")
    if transactions:
        lines.append("\nПоследние транзакции:")
        for txn in transactions:
            lines.append(
                f"• {txn.type}: {txn.amount} ({txn.created_at.strftime('%d.%m %H:%M')})"
            )
    if games:
        lines.append("\nПоследние игры:")
        for game in games:
            lines.append(
                f"• {game.game}: ставка {game.bet}, изменение {game.payout}"
            )
    missions_ready = [m for m in overview.missions if m.completed_at and not m.claimed_at]
    if missions_ready:
        lines.append(
            "\nДоступно наград: " + ", ".join(m.mission.title for m in missions_ready)
        )
    return "\n".join(lines)


@router.message(CommandStart())
async def cmd_start(message: Message, dispatcher: Dispatcher) -> None:
    ctx = _get_context(dispatcher)
    await ctx.economy.ensure_user(
        message.from_user.id,
        message.from_user.username,
        ctx.start_bonus,
    )
    await message.answer(
        "Добро пожаловать в Fantasy Casino!\n"
        "Все ставки — это виртуальные чипы без реальной ценности.\n"
        "Используйте кнопки ниже, чтобы начать игру.",
        reply_markup=main_menu(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "🎲 *Fantasy Casino* — развлекательный бот с виртуальными чипами.\n"
        "Команды:\n"
        "/profile — ваш профиль и баланс\n"
        "/missions — активные задания\n"
        "/achievements — полученные достижения\n"
        "/daily — ежедневный бонус\n"
        "/deposit — пополнение через CryptoBot (виртуально)\n"
        "/withdraw — запрос на вывод (модерация)\n"
        "Используйте меню для выбора игр.",
        parse_mode="Markdown",
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message, dispatcher: Dispatcher) -> None:
    ctx = _get_context(dispatcher)
    text = await _format_profile(ctx, message.from_user.id)
    await message.answer(text, reply_markup=main_menu())



@router.callback_query(lambda c: c.data == "menu:main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.answer("Главное меню:", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "menu:play")
async def menu_play(callback: CallbackQuery):
    from ..keyboards import game_selection

    await callback.message.answer("Выберите игру:", reply_markup=game_selection())
    await callback.answer()


@router.callback_query(lambda c: c.data == "menu:leaderboard")
async def menu_leaderboard(callback: CallbackQuery, dispatcher: Dispatcher) -> None:
    ctx = _get_context(dispatcher)
    leaders = await ctx.storage.get_leaderboard()
    if not leaders:
        text = "Пока нет победителей."
    else:
        lines = ["🏆 Топ игроков:"]
        for idx, row in enumerate(leaders, start=1):
            username = row["username"] or row["telegram_id"]
            lines.append(f"{idx}. {username}: {row['winnings']}")
        text = "\n".join(lines)
    await callback.message.answer(text)
    await callback.answer()
