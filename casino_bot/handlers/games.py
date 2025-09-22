"""Game interaction handlers."""
from __future__ import annotations

from typing import Dict, Optional

from aiogram import Router
from aiogram.types import CallbackQuery, Message

from ..keyboards import (
    bet_shortcuts,
    blackjack_actions,
    coinflip_choice,
    main_menu,
    roulette_choice,
)
from ..services.economy import EconomyError, InsufficientBalanceError
from ..services.games import GameContext
from ..services.games.blackjack import Blackjack, BlackjackRound
from ..utils.context import BotContext

router = Router()

PENDING_GAME: Dict[int, str] = {}
AWAITING_CUSTOM_BET: Dict[int, str] = {}
COINFLIP_BETS: Dict[int, int] = {}
BLACKJACK_SESSIONS: Dict[int, BlackjackRound] = {}
ROULETTE_BETS: Dict[int, int] = {}


def _ctx_from_message(message: Message) -> BotContext:
    ctx: Optional[BotContext] = message.bot.get("context")
    if ctx is None:
        raise RuntimeError("Context missing")
    return ctx


def _ctx_from_callback(callback: CallbackQuery) -> BotContext:
    ctx: Optional[BotContext] = callback.message.bot.get("context") if callback.message else None
    if ctx is None:
        raise RuntimeError("Context missing")
    return ctx


@router.callback_query(lambda c: c.data and c.data.startswith("game:"))
async def select_game(callback: CallbackQuery) -> None:
    game = callback.data.split(":", 1)[1]
    PENDING_GAME[callback.from_user.id] = game
    await callback.message.answer(
        "Выберите ставку:", reply_markup=bet_shortcuts()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("bet:"))
async def choose_bet(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    game = PENDING_GAME.get(user_id)
    if not game:
        await callback.answer("Сначала выберите игру", show_alert=True)
        return
    bet_data = callback.data.split(":", 1)[1]
    if bet_data == "custom":
        AWAITING_CUSTOM_BET[user_id] = game
        await callback.message.answer("Введите сумму ставки числом:")
        await callback.answer()
        return
    try:
        amount = int(bet_data)
    except ValueError:
        await callback.answer("Некорректная ставка", show_alert=True)
        return
    await _start_round(callback.message, user_id, game, amount)
    await callback.answer()


@router.message(lambda m: m.from_user.id in AWAITING_CUSTOM_BET)
async def custom_bet_handler(message: Message) -> None:
    if message.from_user.id not in AWAITING_CUSTOM_BET:
        return
    game = AWAITING_CUSTOM_BET.pop(message.from_user.id)
    try:
        amount = int(message.text)
    except (TypeError, ValueError):
        await message.answer("Введите корректную сумму")
        return
    await _start_round(message, message.from_user.id, game, amount)


async def _start_round(message: Message, user_id: int, game: str, bet: int) -> None:
    ctx = _ctx_from_message(message)
    try:
        await ctx.economy.place_bet(user_id, bet)
    except (InsufficientBalanceError, EconomyError) as exc:
        await message.answer(str(exc))
        return
    reply = message.answer
    PENDING_GAME.pop(user_id, None)
    if game == "coinflip":
        COINFLIP_BETS[user_id] = bet
        await reply(
            f"Ставка {bet} принята. Выберите сторону монеты:",
            reply_markup=coinflip_choice(),
        )
        return
    if game == "roulette":
        ROULETTE_BETS[user_id] = bet
        await reply(
            f"Ставка {bet} принята. Выберите цвет:",
            reply_markup=roulette_choice(),
        )
        return
    if game == "slots":
        result = await ctx.games.get("slots").play(GameContext(user_id=user_id, bet=bet))
        settle = await ctx.economy.settle_bet(
            user_id,
            bet,
            payout=result.payout,
            game="slots",
            state={"result": result.state},
        )
        progress = await _handle_progress(ctx, user_id, "slots", bet, result.payout)
        message_body = result.display + f"\nБаланс: {settle.balance}"
        if progress:
            message_body += f"\n\n{progress}"
        await reply(message_body, reply_markup=main_menu())
        return
    if game == "blackjack":
        blackjack = ctx.games.get("blackjack")
        round_state = blackjack.new_round(bet)
        BLACKJACK_SESSIONS[user_id] = round_state
        await reply(
            _render_blackjack(blackjack, round_state, hide_dealer=True),
            reply_markup=blackjack_actions(double_available=not round_state.doubled),
        )
        return
    if game == "dice":
        result = await ctx.games.get("dice").play(GameContext(user_id=user_id, bet=bet))
        settle = await ctx.economy.settle_bet(
            user_id,
            bet,
            payout=result.payout,
            game="dice",
            state=result.state,
        )
        progress = await _handle_progress(ctx, user_id, "dice", bet, result.payout)
        message_body = result.display + f"\nБаланс: {settle.balance}"
        if progress:
            message_body += f"\n\n{progress}"
        await reply(message_body, reply_markup=main_menu())
        return
    if game == "crash":
        result = await ctx.games.get("crash").play(GameContext(user_id=user_id, bet=bet))
        settle = await ctx.economy.settle_bet(
            user_id,
            bet,
            payout=result.payout,
            game="crash",
            state=result.state,
        )
        progress = await _handle_progress(ctx, user_id, "crash", bet, result.payout)
        message_body = result.display + f"\nБаланс: {settle.balance}"
        if progress:
            message_body += f"\n\n{progress}"
        await reply(message_body, reply_markup=main_menu())
        return
    await reply("Игра пока не поддерживается", reply_markup=main_menu())


@router.callback_query(lambda c: c.data and c.data.startswith("coin:"))
async def coinflip_choice_handler(callback: CallbackQuery) -> None:
    bet = COINFLIP_BETS.pop(callback.from_user.id, None)
    if bet is None:
        await callback.answer("Сначала сделайте ставку", show_alert=True)
        return
    choice = callback.data.split(":", 1)[1]
    ctx = _ctx_from_callback(callback)
    result = await ctx.games.get("coinflip").play(
        GameContext(user_id=callback.from_user.id, bet=bet), choice=choice
    )
    settle = await ctx.economy.settle_bet(
        callback.from_user.id,
        bet,
        payout=result.payout,
        game="coinflip",
        state=result.state,
    )
    progress = await _handle_progress(
        ctx, callback.from_user.id, "coinflip", bet, result.payout
    )
    message_body = result.display + f"\nБаланс: {settle.balance}"
    if progress:
        message_body += f"\n\n{progress}"
    await callback.message.answer(message_body, reply_markup=main_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("roulette:"))
async def roulette_choice_handler(callback: CallbackQuery) -> None:
    bet = ROULETTE_BETS.pop(callback.from_user.id, None)
    if bet is None:
        await callback.answer("Сначала сделайте ставку", show_alert=True)
        return
    choice = callback.data.split(":", 1)[1]
    ctx = _ctx_from_callback(callback)
    result = await ctx.games.get("roulette").play(
        GameContext(user_id=callback.from_user.id, bet=bet), choice=choice
    )
    settle = await ctx.economy.settle_bet(
        callback.from_user.id,
        bet,
        payout=result.payout,
        game="roulette",
        state=result.state,
    )
    progress = await _handle_progress(
        ctx, callback.from_user.id, "roulette", bet, result.payout
    )
    message_body = result.display + f"\nБаланс: {settle.balance}"
    if progress:
        message_body += f"\n\n{progress}"
    await callback.message.answer(message_body, reply_markup=main_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("bj:"))
async def blackjack_action(callback: CallbackQuery) -> None:
    round_state = BLACKJACK_SESSIONS.get(callback.from_user.id)
    if not round_state:
        await callback.answer("Начните новую игру", show_alert=True)
        return
    ctx = _ctx_from_callback(callback)
    blackjack = ctx.games.get("blackjack")
    action = callback.data.split(":", 1)[1]
    if action == "hit":
        blackjack.player_hit(round_state)
        if round_state.finished:
            await _finish_blackjack(callback, ctx, round_state)
        else:
            await callback.message.answer(
                _render_blackjack(blackjack, round_state, hide_dealer=True),
                reply_markup=blackjack_actions(double_available=not round_state.doubled),
            )
        await callback.answer()
        return
    if action == "double":
        if round_state.doubled:
            await callback.answer("Вы уже удвоили ставку", show_alert=True)
            return
        try:
            await ctx.economy.place_bet(callback.from_user.id, round_state.bet)
        except (EconomyError, InsufficientBalanceError) as exc:
            await callback.answer(str(exc), show_alert=True)
            return
        blackjack.player_double(round_state)
        await _finish_blackjack(callback, ctx, round_state)
        await callback.answer()
        return
    if action == "stand":
        blackjack.player_stand(round_state)
        await _finish_blackjack(callback, ctx, round_state)
        await callback.answer()
        return
    await callback.answer("Действие не поддерживается", show_alert=True)


async def _finish_blackjack(callback: CallbackQuery, ctx: BotContext, round_state: BlackjackRound) -> None:
    blackjack = ctx.games.get("blackjack")
    result = blackjack.finish_round(round_state)
    settle = await ctx.economy.settle_bet(
        callback.from_user.id,
        bet=round_state.bet,
        payout=result.payout,
        game="blackjack",
        state=result.state,
    )
    progress = await _handle_progress(
        ctx, callback.from_user.id, "blackjack", round_state.bet, result.payout
    )
    message_body = result.display + f"\nБаланс: {settle.balance}"
    if progress:
        message_body += f"\n\n{progress}"
    await callback.message.answer(message_body, reply_markup=main_menu())
    BLACKJACK_SESSIONS.pop(callback.from_user.id, None)


async def _handle_progress(
    ctx: BotContext, user_id: int, game: str, bet: int, payout: int
) -> str:
    update = await ctx.progression.record_round(user_id, game, bet, payout)
    sections = []
    if update.unlocked_achievements:
        lines = ["🏅 Новые достижения:"]
        lines.extend(
            f"• {ach.achievement.title}" for ach in update.unlocked_achievements
        )
        sections.append("\n".join(lines))
    if update.completed_missions:
        lines = ["🎯 Миссии выполнены:"]
        lines.extend(
            f"• {mission.mission.title} (+{mission.mission.reward} чипов, заберите в /missions)"
            for mission in update.completed_missions
        )
        sections.append("\n".join(lines))
    sections.append(
        "📈 Прогресс: уровень {lvl}, до следующего {xp} XP. Клуб: {tier} x{mult:.2f}".format(
            lvl=update.level,
            xp=update.xp_to_next,
            tier=update.loyalty_tier.name,
            mult=update.loyalty_tier.bonus_multiplier,
        )
    )
    return "\n\n".join(sections)


def _render_blackjack(blackjack: Blackjack, round_state: BlackjackRound, *, hide_dealer: bool) -> str:
    player_cards = " ".join(str(card) for card in round_state.player_hand)
    if hide_dealer:
        dealer_cards = f"{round_state.dealer_hand[0]} 🂠"
    else:
        dealer_cards = " ".join(str(card) for card in round_state.dealer_hand)
    value, _ = blackjack._hand_value(round_state.player_hand)  # type: ignore[attr-defined]
    return (
        "🃏 Блэкджек\n"
        f"Ваши карты ({value}): {player_cards}\n"
        f"Карты дилера: {dealer_cards}\n"
        "Выберите действие."
    )


__all__ = ["router"]
