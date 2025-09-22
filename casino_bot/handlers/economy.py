"""Handlers for economy-related commands."""
from __future__ import annotations

from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ..keyboards import main_menu
from ..utils.context import BotContext
from ..services.economy import EconomyError, InsufficientBalanceError
from .common import _format_profile

router = Router()


def _ctx(message: Message) -> BotContext:
    ctx: Optional[BotContext] = message.bot.get("context")
    if ctx is None:
        raise RuntimeError("Context missing")
    return ctx


def _ctx_from_callback(callback: CallbackQuery) -> BotContext:
    ctx: Optional[BotContext] = callback.message.bot.get("context") if callback.message else None
    if ctx is None:
        raise RuntimeError("Context missing")
    return ctx


@router.message(Command("daily"))
async def cmd_daily(message: Message) -> None:
    ctx = _ctx(message)
    try:
        result = await ctx.economy.grant_daily_bonus(message.from_user.id, ctx.daily_bonus)
    except EconomyError as exc:
        await message.answer(str(exc))
        return
    await message.answer(
        f"🎁 Начислено {ctx.daily_bonus} чипов! Текущий баланс: {result.balance}",
        reply_markup=main_menu(),
    )


@router.message(Command("deposit"))
async def cmd_deposit(message: Message) -> None:
    ctx = _ctx(message)
    parts = message.text.split(maxsplit=1) if message.text else []
    amount = 10.0
    if len(parts) == 2:
        try:
            amount = float(parts[1])
        except ValueError:
            await message.answer("Укажите сумму в долларах, например `/deposit 15`.", parse_mode="Markdown")
            return
    invoice = await ctx.crypto.create_invoice(amount_usd=amount)
    await message.answer(
        "Пополнение происходит через CryptoBot. Это демо-ссылка, деньги не списываются.\n"
        f"Сумма: {invoice.amount_usd}$ → {invoice.amount_tokens} чипов\n"
        f"[Открыть счёт]({invoice.url})",
        parse_mode="Markdown",
    )


@router.message(Command("withdraw"))
async def cmd_withdraw(message: Message) -> None:
    ctx = _ctx(message)
    if not message.text:
        await message.answer("Используйте `/withdraw <amount> <wallet>`.", parse_mode="Markdown")
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Укажите сумму и адрес кошелька: `/withdraw 100 TON_ADDRESS`.", parse_mode="Markdown")
        return
    try:
        amount = int(parts[1])
    except ValueError:
        await message.answer("Сумма должна быть числом.")
        return
    address = parts[2]
    try:
        result = await ctx.economy.withdraw(message.from_user.id, amount, address)
    except InsufficientBalanceError as exc:
        await message.answer(str(exc))
        return
    await message.answer(
        "Запрос на вывод зарегистрирован. Оператор свяжется с вами в течение 24 часов."
        f"\nСписание: {amount} чипов. Остаток: {result.balance}",
    )


@router.callback_query(lambda c: c.data == "menu:daily")
async def menu_daily(callback: CallbackQuery) -> None:
    ctx = _ctx_from_callback(callback)
    try:
        result = await ctx.economy.grant_daily_bonus(callback.from_user.id, ctx.daily_bonus)
    except EconomyError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.message.answer(
        f"🎁 Начислено {ctx.daily_bonus} чипов! Баланс: {result.balance}",
        reply_markup=main_menu(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "menu:deposit")
async def menu_deposit(callback: CallbackQuery) -> None:
    ctx = _ctx_from_callback(callback)
    invoice = await ctx.crypto.create_invoice(amount_usd=10.0)
    await callback.message.answer(
        "Пополнение доступно через CryptoBot. Выберите сумму командой `/deposit <usd>`."
        f"\nПример: {invoice.amount_usd}$ → {invoice.amount_tokens} чипов.",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "menu:profile")
async def menu_profile(callback: CallbackQuery) -> None:
    ctx = _ctx_from_callback(callback)
    text = await _format_profile(ctx, callback.from_user.id)
    await callback.message.answer(text, reply_markup=main_menu())
    await callback.answer()
