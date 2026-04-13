"""Integration tests for the request-logging HTTP middleware."""

import asyncio
import tempfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI

from src.api.services.request_logger import (
    RequestLogger,
    RequestRecord,
    build_request_logger,
)


def _build_app(logger: RequestLogger) -> FastAPI:
    """Build a minimal FastAPI app with the logging middleware attached."""
    import time

    app = FastAPI()

    def _sanitize_headers_for_logging(headers):
        sanitized = {}
        sensitive = {"authorization", "cookie", "set-cookie"}
        for key, value in headers:
            lower_key = key.lower()
            if lower_key in sensitive:
                continue
            if lower_key == "x-api-key":
                sanitized[key] = value[:8]
                continue
            sanitized[key] = value
        return sanitized

    # Mirror the middleware from main.py
    @app.middleware("http")
    async def log_requests_middleware(request, call_next):
        timestamp = datetime.now(tz=timezone.utc)
        start = time.monotonic()
        try:
            body = await request.body()
        except Exception:
            body = b""

        headers = _sanitize_headers_for_logging(list(request.headers.items()))

        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000.0
        record = RequestRecord(
            timestamp=timestamp,
            method=request.method,
            path=request.url.path,
            query_string=str(request.url.query),
            headers=headers,
            request_body=body,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
        )
        asyncio.create_task(logger.log(record))
        return response

    @app.get("/ping")
    async def ping():
        return {"pong": True}

    return app


class TestLoggingMiddleware:
    @pytest.mark.asyncio
    async def test_request_reaches_backend(self):
        """Middleware should call log() once per request."""
        captured: list[RequestRecord] = []

        async def _fake_log(record: RequestRecord):
            captured.append(record)

        with tempfile.TemporaryDirectory() as tmp:
            logger = build_request_logger(
                log_dir=tmp,
                github_token=None,
            )
        logger.log = _fake_log  # type: ignore[method-assign]

        app = _build_app(logger)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ping")

        assert resp.status_code == 200
        # Allow background task to complete
        await asyncio.sleep(0.05)
        assert len(captured) == 1
        assert captured[0].method == "GET"
        assert captured[0].path == "/ping"
        assert captured[0].status_code == 200

    @pytest.mark.asyncio
    async def test_sensitive_headers_are_stripped(self):
        """Authorization is stripped while x-api-key is truncated to a prefix."""
        captured: list[RequestRecord] = []

        async def _fake_log(record: RequestRecord):
            captured.append(record)

        with tempfile.TemporaryDirectory() as tmp:
            logger = build_request_logger(
                log_dir=tmp,
                github_token=None,
            )
        logger.log = _fake_log  # type: ignore[method-assign]

        app = _build_app(logger)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get(
                "/ping",
                headers={
                    "Authorization": "Bearer secret-token",
                    "X-API-Key": "my-key",
                    "X-Custom": "keep-me",
                },
            )

        await asyncio.sleep(0.05)
        assert len(captured) == 1
        headers = captured[0].headers
        assert "authorization" not in headers
        assert headers["x-api-key"] == "my-key"
        assert "x-custom" in headers

    @pytest.mark.asyncio
    async def test_api_key_is_truncated_to_first_8_characters(self):
        captured: list[RequestRecord] = []

        async def _fake_log(record: RequestRecord):
            captured.append(record)

        with tempfile.TemporaryDirectory() as tmp:
            logger = build_request_logger(
                log_dir=tmp,
                github_token=None,
            )
        logger.log = _fake_log  # type: ignore[method-assign]

        app = _build_app(logger)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get(
                "/ping",
                headers={"X-API-Key": "12345678abcdef"},
            )

        await asyncio.sleep(0.05)
        assert len(captured) == 1
        assert captured[0].headers["x-api-key"] == "12345678"

    @pytest.mark.asyncio
    async def test_request_body_is_captured(self):
        """POST body should be recorded in the RequestRecord."""
        captured: list[RequestRecord] = []

        async def _fake_log(record: RequestRecord):
            captured.append(record)

        with tempfile.TemporaryDirectory() as tmp:
            logger = build_request_logger(
                log_dir=tmp,
                github_token=None,
            )
        logger.log = _fake_log  # type: ignore[method-assign]

        app = _build_app(logger)

        @app.post("/echo")
        async def echo(request):
            body = await request.body()
            return {"received": body.decode()}

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/echo", content=b'{"tx": "0xabc"}')

        await asyncio.sleep(0.05)
        assert len(captured) == 1
        assert b"0xabc" in captured[0].request_body
