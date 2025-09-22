"""Economy and wallet management services."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Union

from ..storage import CasinoStorage, Transaction


class EconomyError(Exception):
    """Base class for economy related errors."""


class InsufficientBalanceError(EconomyError):
    """Raised when balance is not enough for an operation."""


class BetLimitError(EconomyError):
    """Raised when bet size is out of allowed range."""


@dataclass(slots=True)
class WalletSnapshot:
    balance: int
    last_daily_bonus: Optional[datetime]


@dataclass(slots=True)
class TransactionResult:
    transaction: Transaction
    balance: int


class EconomyService:
    """High level wallet operations."""

    def __init__(self, storage: CasinoStorage, *, min_bet: int, max_bet: int) -> None:
        self.storage = storage
        self.min_bet = min_bet
        self.max_bet = max_bet

    async def ensure_user(self, telegram_id: int, username: Optional[str], start_bonus: int) -> WalletSnapshot:
        user = await self.storage.get_user(telegram_id)
        if user is None:
            user = await self.storage.create_user(telegram_id, username, start_bonus)
            await self.storage.record_transaction(
                telegram_id, "bonus", start_bonus, {"reason": "start_bonus"}
            )
        await self.storage.ensure_user_stats(telegram_id)
        last_bonus = await self.storage.get_daily_bonus_timestamp(telegram_id)
        return WalletSnapshot(balance=user.balance, last_daily_bonus=last_bonus)

    async def get_wallet(self, telegram_id: int) -> WalletSnapshot:
        user = await self.storage.get_user(telegram_id)
        if user is None:
            raise EconomyError("User not registered")
        await self.storage.ensure_user_stats(telegram_id)
        last_bonus = await self.storage.get_daily_bonus_timestamp(telegram_id)
        return WalletSnapshot(balance=user.balance, last_daily_bonus=last_bonus)

    async def grant_daily_bonus(self, telegram_id: int, amount: int) -> TransactionResult:
        last_claim = await self.storage.get_daily_bonus_timestamp(telegram_id)
        now = datetime.utcnow()
        if last_claim and now - last_claim < timedelta(hours=24):
            raise EconomyError("Бонус доступен раз в 24 часа")
        await self.storage.update_balance(telegram_id, amount)
        await self.storage.set_daily_bonus_timestamp(telegram_id, now)
        transaction = await self.storage.record_transaction(
            telegram_id, "bonus", amount, {"reason": "daily"}
        )
        wallet = await self.get_wallet(telegram_id)
        return TransactionResult(transaction=transaction, balance=wallet.balance)

    async def deposit(
        self, telegram_id: int, amount: int, meta: Optional[Dict[str, str]] = None
    ) -> TransactionResult:
        await self.storage.update_balance(telegram_id, amount)
        transaction = await self.storage.record_transaction(
            telegram_id, "deposit", amount, meta or {}
        )
        wallet = await self.get_wallet(telegram_id)
        return TransactionResult(transaction=transaction, balance=wallet.balance)

    async def grant_reward(
        self, telegram_id: int, amount: int, *, reason: str, meta: Optional[Dict[str, str]] = None
    ) -> TransactionResult:
        await self.storage.update_balance(telegram_id, amount)
        payload = {"reason": reason}
        if meta:
            payload.update(meta)
        transaction = await self.storage.record_transaction(
            telegram_id, "bonus", amount, payload
        )
        wallet = await self.get_wallet(telegram_id)
        return TransactionResult(transaction=transaction, balance=wallet.balance)

    async def withdraw(self, telegram_id: int, amount: int, address: str) -> TransactionResult:
        wallet = await self.get_wallet(telegram_id)
        if wallet.balance < amount:
            raise InsufficientBalanceError("Недостаточно чипов для вывода")
        await self.storage.update_balance(telegram_id, -amount)
        transaction = await self.storage.record_transaction(
            telegram_id, "withdrawal", -amount, {"address": address}
        )
        wallet = await self.get_wallet(telegram_id)
        return TransactionResult(transaction=transaction, balance=wallet.balance)

    def _check_bet_limits(self, amount: int) -> None:
        if amount < self.min_bet:
            raise BetLimitError(f"Минимальная ставка {self.min_bet} чипов")
        if amount > self.max_bet:
            raise BetLimitError(f"Максимальная ставка {self.max_bet} чипов")

    async def place_bet(self, telegram_id: int, amount: int) -> Transaction:
        self._check_bet_limits(amount)
        wallet = await self.get_wallet(telegram_id)
        if wallet.balance < amount:
            raise InsufficientBalanceError("Недостаточно чипов для ставки")
        await self.storage.update_balance(telegram_id, -amount)
        return await self.storage.record_transaction(
            telegram_id, "bet", -amount, {}
        )

    async def settle_bet(
        self,
        telegram_id: int,
        bet: int,
        payout: int,
        *,
        game: str,
        state: Dict[str, Union[int, float, str]],
    ) -> TransactionResult:
        if payout < 0:
            raise ValueError("Payout cannot be negative")
        if payout:
            await self.storage.update_balance(telegram_id, payout)
        transaction = await self.storage.record_transaction(
            telegram_id,
            "win" if payout > bet else "refund" if payout == bet else "loss",
            payout if payout else 0,
            {"game": game, **state},
        )
        round_meta = {"payout": payout, "bet": bet, "net": payout - bet, **state}
        await self.storage.record_game_round(
            telegram_id,
            game=game,
            bet=bet,
            payout=payout,
            state=round_meta,
        )
        wallet = await self.get_wallet(telegram_id)
        return TransactionResult(transaction=transaction, balance=wallet.balance)
