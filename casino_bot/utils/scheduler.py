"""Utility helpers for periodic async tasks."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Dict


class AsyncScheduler:
    """Minimalist scheduler for recurring async tasks."""

    def __init__(self) -> None:
        self._tasks: Dict[str, asyncio.Task] = {}

    def schedule(self, name: str, interval: float, coro_factory: Callable[[], Awaitable[None]]) -> None:
        if name in self._tasks:
            raise ValueError(f"Task {name} already scheduled")

        async def runner() -> None:
            while True:
                await coro_factory()
                await asyncio.sleep(interval)

        self._tasks[name] = asyncio.create_task(runner())

    async def stop(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()


__all__ = ["AsyncScheduler"]
