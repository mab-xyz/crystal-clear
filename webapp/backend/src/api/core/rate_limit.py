"""Fixed-window rate limiting (per minute), shared across workers via Redis.

Falls back to per-process counters if Redis is unavailable (fail open: the
API must not go down because the limiter's store did).

Identity: API key hash when a key is presented, else client IP. Requests that
end in 401 count against the client IP so rotating fake keys cannot dodge the
per-key limits. ``/r/<id>`` is limited per IP (it is unauthenticated by
design: the user opens it from the device).
"""

from __future__ import annotations

import hashlib
import re
import time
from typing import Any, Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger

from src.api.core.config import settings

WINDOW_SECONDS = 60
EXEMPT_PATHS = {"/", "/health", "/ping"}
_SCAN = re.compile(r"^/[^/]+/scan/")
_LOCAL_PROXY_HOSTS = {"127.0.0.1", "::1"}


class RateLimiter:
    def __init__(
        self,
        redis: Any | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._redis = redis
        self._clock = clock
        self._mem: dict[tuple[str, int], int] = {}
        self._warned = False

    def _window(self) -> tuple[int, int]:
        now = int(self._clock())
        wid = now // WINDOW_SECONDS
        return wid, (wid + 1) * WINDOW_SECONDS - now

    def _prune(self, wid: int) -> None:
        if len(self._mem) > 10_000:
            self._mem = {k: v for k, v in self._mem.items() if k[1] >= wid}

    async def hit(self, key: str, limit: int) -> tuple[bool, int]:
        """Count one request. Returns (allowed, retry_after_seconds)."""
        wid, retry = self._window()
        count = None
        if self._redis is not None:
            rkey = f"rl:{key}:{wid}"
            try:
                count = int(await self._redis.incr(rkey))
                if count == 1:
                    await self._redis.expire(rkey, WINDOW_SECONDS + 5)
            except Exception as exc:  # noqa: BLE001 - fail open to memory
                if not self._warned:
                    logger.warning("rate limiter redis unavailable: {}", exc)
                    self._warned = True
        if count is None:
            self._prune(wid)
            count = self._mem.get((key, wid), 0) + 1
            self._mem[(key, wid)] = count
        return count <= limit, retry

    async def count(self, key: str) -> int:
        wid, _ = self._window()
        if self._redis is not None:
            try:
                return int(await self._redis.get(f"rl:{key}:{wid}") or 0)
            except Exception:  # noqa: BLE001
                pass
        return self._mem.get((key, wid), 0)


_limiter: RateLimiter | None = None


def get_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        redis = None
        try:
            from redis import asyncio as aioredis

            redis = aioredis.from_url(settings.cache_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("rate limiter without redis: {}", exc)
        _limiter = RateLimiter(redis)
    return _limiter


def client_ip(request: Request) -> str:
    host = request.client.host if request.client else "unknown"
    if host in _LOCAL_PROXY_HOSTS:  # behind our own nginx
        return request.headers.get("x-real-ip") or host
    return host


def _limited(retry_after: int) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"code": 429, "message": "Rate limit exceeded"},
        headers={"Retry-After": str(max(retry_after, 1))},
    )


async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if not settings.rate_limit_enabled or path in EXEMPT_PATHS:
        return await call_next(request)
    if path.startswith("/health"):
        return await call_next(request)

    limiter = get_limiter()
    ip = client_ip(request)
    api_key = request.headers.get(settings.api_key_header)

    if await limiter.count(f"authfail:{ip}") >= settings.rate_limit_authfail_per_min:
        return _limited(WINDOW_SECONDS)

    if path.startswith("/r/"):
        bucket, ident, limit = "report", f"ip:{ip}", settings.rate_limit_report_per_min
    else:
        ident = (
            "key:" + hashlib.sha256(api_key.encode()).hexdigest()[:16]
            if api_key
            else f"ip:{ip}"
        )
        if _SCAN.match(path):
            bucket, limit = "scan", settings.rate_limit_scan_per_min
        else:
            bucket = "default"
            limit = (
                settings.rate_limit_default_per_min
                if api_key
                else settings.rate_limit_anon_per_min
            )
    allowed, retry = await limiter.hit(f"{bucket}:{ident}", limit)
    if not allowed:
        return _limited(retry)

    response = await call_next(request)
    if response.status_code == 401:
        await limiter.hit(f"authfail:{ip}", settings.rate_limit_authfail_per_min)
    return response
