"""Handlers for missions, achievements and loyalty."""
from __future__ import annotations

from typing import Optional

from aiogram import Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..keyboards import main_menu
from ..utils.context import BotContext

router = Router()


def _ctx(dispatcher: Dispatcher) -> BotContext:
    ctx: Optional[BotContext] = dispatcher.data.get("context")  # type: ignore[assignment]
    if ctx is None:
        raise RuntimeError("Context missing")
    return ctx


def _missions_keyboard(missions) -> InlineKeyboardMarkup:
    buttons = []
    for mission in missions:
        if mission.completed_at and not mission.claimed_at:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"🎯 {mission.mission.title}",
                        callback_data=f"mission:claim:{mission.mission.code}",
                    )
                ]
            )
    buttons.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _missions_text(missions) -> str:
    lines = ["🔥 Активные миссии:"]
    for mission in missions:
        progress = f"{mission.progress}/{mission.mission.target}"
        if mission.claimed_at:
            status = "✅ Получена"
        elif mission.completed_at:
            status = "⚡ Готова к получению"
        else:
            status = "⌛ В процессе"
        lines.append(
            f"• {mission.mission.title} — {mission.mission.description}\n"
            f"  Прогресс: {progress}. Награда: {mission.mission.reward}. {status}"
        )
    return "\n".join(lines)


@router.message(Command("missions"))
async def cmd_missions(message: Message, dispatcher: Dispatcher) -> None:
    ctx = _ctx(dispatcher)
    overview = await ctx.progression.get_profile(message.from_user.id)
    keyboard = _missions_keyboard(overview.missions)
    await message.answer(_missions_text(overview.missions), reply_markup=keyboard)


@router.message(Command("achievements"))
async def cmd_achievements(message: Message, dispatcher: Dispatcher) -> None:
    ctx = _ctx(dispatcher)
    overview = await ctx.progression.get_profile(message.from_user.id)
    if not overview.achievements:
        await message.answer("Пока нет открытых достижений. Играйте, чтобы открыть новые!", reply_markup=main_menu())
        return
    lines = ["🏅 Полученные достижения:"]
    for ach in overview.achievements:
        lines.append(f"• {ach.achievement.title} — {ach.achievement.description}")
    await message.answer("\n".join(lines), reply_markup=main_menu())


@router.callback_query(lambda c: c.data == "menu:missions")
async def menu_missions(callback: CallbackQuery, dispatcher: Dispatcher) -> None:
    ctx = _ctx(dispatcher)
    overview = await ctx.progression.get_profile(callback.from_user.id)
    keyboard = _missions_keyboard(overview.missions)
    await callback.message.answer(_missions_text(overview.missions), reply_markup=keyboard)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("mission:claim:"))
async def claim_mission(callback: CallbackQuery, dispatcher: Dispatcher) -> None:
    ctx = _ctx(dispatcher)
    code = callback.data.split(":", 2)[2]
    try:
        mission, claimed = await ctx.progression.claim_mission(callback.from_user.id, code)
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    if not claimed:
        await callback.answer("Награда уже получена", show_alert=True)
        return
    result = await ctx.economy.grant_reward(
        callback.from_user.id,
        mission.reward,
        reason="mission",
        meta={"mission": mission.code},
    )
    await callback.message.answer(
        f"🎉 Награда за миссию «{mission.title}» получена! +{mission.reward} чипов."
        f"\nТекущий баланс: {result.balance}",
        reply_markup=main_menu(),
    )
    await callback.answer("Награда начислена")


__all__ = ["router"]
