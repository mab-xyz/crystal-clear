"""Per-API-key usage counters: one Redis hash per UTC day (O(1) per request).

``usage:<YYYY-MM-DD>`` fields: ``<prefix>|total``, ``|scan``, ``|2xx``,
``|4xx``, ``|5xx``. Prefix = first 8 chars of the key (unique in the
``api_key`` table). Only authenticated, non-rate-limited requests count. Reading N days is N HGETALLs,
independent of traffic volume. Falls back to process memory without Redis.
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from loguru import logger

RETENTION_SECONDS = 100 * 24 * 3600
FIELDS = ("total", "scan", "2xx", "4xx", "5xx")


def day_of(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


class UsageStore:
    def __init__(
        self,
        redis: Any | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._redis = redis
        self._clock = clock
        self._mem: dict[str, dict[str, int]] = defaultdict(dict)
        self._warned = False

    async def record(self, prefix: str, *, scan: bool, status: int) -> None:
        day = day_of(self._clock())
        fields = ["total", f"{status // 100}xx"] + (["scan"] if scan else [])
        if self._redis is not None:
            key = f"usage:{day}"
            try:
                pipe = self._redis.pipeline()
                for f in fields:
                    pipe.hincrby(key, f"{prefix}|{f}", 1)
                pipe.expire(key, RETENTION_SECONDS)
                await pipe.execute()
                return
            except Exception as exc:  # noqa: BLE001 - never fail a request
                if not self._warned:
                    logger.warning("key usage redis unavailable: {}", exc)
                    self._warned = True
        bucket = self._mem[day]
        for f in fields:
            bucket[f"{prefix}|{f}"] = bucket.get(f"{prefix}|{f}", 0) + 1

    async def _day(self, day: str) -> dict[str, int]:
        if self._redis is not None:
            try:
                raw = await self._redis.hgetall(f"usage:{day}")
                return {
                    (k.decode() if isinstance(k, bytes) else k): int(v)
                    for k, v in raw.items()
                }
            except Exception:  # noqa: BLE001
                pass
        return dict(self._mem.get(day, {}))

    async def read(
        self, days: int, prefix: str | None = None
    ) -> dict[str, dict[str, Any]]:
        """{prefix: {total, scan, 2xx, 4xx, 5xx, by_day{day: total}}}."""
        today = datetime.fromtimestamp(self._clock(), tz=timezone.utc)
        out: dict[str, dict[str, Any]] = {}
        for i in range(max(1, days)):
            day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            for field, n in (await self._day(day)).items():
                p, _, f = field.partition("|")
                if prefix is not None and p != prefix:
                    continue
                entry = out.setdefault(
                    p, {**{k: 0 for k in FIELDS}, "by_day": {}}
                )
                entry[f] = entry.get(f, 0) + n
                if f == "total":
                    entry["by_day"][day] = n
        return out
