"""Bounded pool of risk engines so Ledger scans can run in parallel.

One ``CrystalClearRiskEngine`` serializes simulations (it patches shared SDK
state under a lock), so parallelism = N engines, each used by one request at
a time. ``size`` bounds concurrent simulations; extra requests wait up to
``timeout`` seconds and then get ``PoolBusy`` (-> 5xx, retryable).
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable


class PoolBusy(Exception):
    """No engine became free within the queue timeout."""


class EnginePool:
    def __init__(
        self, factory: Callable[[], Any], size: int, timeout: float
    ) -> None:
        self._factory = factory
        self._size = max(1, size)
        self._timeout = timeout
        self._idle: list[Any] = []
        self._created = 0
        self._sem: asyncio.Semaphore | None = None

    def _semaphore(self) -> asyncio.Semaphore:
        # created lazily so it binds to the serving event loop
        if self._sem is None:
            self._sem = asyncio.Semaphore(self._size)
        return self._sem

    @property
    def size(self) -> int:
        return self._size

    async def acquire(self) -> Any:
        sem = self._semaphore()
        try:
            await asyncio.wait_for(sem.acquire(), self._timeout)
        except asyncio.TimeoutError as exc:
            raise PoolBusy("all simulation slots busy") from exc
        if self._idle:
            return self._idle.pop()
        try:
            engine = await asyncio.to_thread(self._factory)
        except BaseException:
            sem.release()
            raise
        self._created += 1
        return engine

    def release(self, engine: Any) -> None:
        self._idle.append(engine)
        self._semaphore().release()

    async def run(self, fn: Callable[[Any], Any]) -> Any:
        """Run ``fn(engine)`` in a worker thread holding one engine."""
        engine = await self.acquire()
        try:
            return await asyncio.to_thread(fn, engine)
        finally:
            self.release(engine)


def default_pool() -> EnginePool:
    from src.api.core.config import settings
    from src.api.integrations.crystal_clear_adapter import (
        CrystalClearRiskEngine,
        get_risk_engine,
    )

    first = [get_risk_engine()]  # reuse the app singleton for slot #1

    def factory() -> Any:
        return first.pop() if first else CrystalClearRiskEngine()

    return EnginePool(
        factory,
        settings.ledger_max_concurrency,
        settings.ledger_queue_timeout_seconds,
    )


_pool: EnginePool | None = None


def get_ledger_pool() -> EnginePool:
    """FastAPI dependency (overridable in tests)."""
    global _pool
    if _pool is None:
        _pool = default_pool()
    return _pool
