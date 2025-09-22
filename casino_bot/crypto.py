"""Stub integration with CryptoBot payment provider."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Invoice:
    url: str
    amount_usd: float
    amount_tokens: int


class CryptoBotClient:
    """Simplified CryptoBot integration mock."""

    def __init__(self, token: Optional[str]) -> None:
        self.token = token

    async def create_invoice(self, *, amount_usd: float) -> Invoice:
        if amount_usd <= 0:
            raise ValueError("Amount must be positive")
        # In production this would call CryptoBot API. We simulate conversion 1 USD = 100 chips.
        tokens = int(amount_usd * 100)
        fake_url = f"https://t.me/CryptoBot?start=FAKE_INVOICE_{tokens}"
        return Invoice(url=fake_url, amount_usd=amount_usd, amount_tokens=tokens)


__all__ = ["CryptoBotClient", "Invoice"]
