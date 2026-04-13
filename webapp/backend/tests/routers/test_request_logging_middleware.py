"""Integration tests for the request-logging HTTP middleware."""

import asyncio
import tempfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.services.request_logger import (
    RequestLogger,
    RequestRecord,
    build_request_logger,
)


def _build_app(logger: RequestLogger) -> FastAPI:
    """Build a minimal FastAPI app with the logging middleware attached."""
    import time

    app = FastAPI()

    # Mirror the middleware from main.py
    @app.middleware("http")
    async def log_requests_middleware(request, call_next):
        timestamp = datetime.now(tz=timezone.utc)
        start = time.monotonic()
        try:
            body = await request.body()
        except Exception:
            body = b""

        _SENSITIVE = {"authorization", "x-api-key", "cookie", "set-cookie"}
        headers = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in _SENSITIVE
        }

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
    def test_request_reaches_backend(self):
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
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/ping")

        assert resp.status_code == 200
        # Wait briefly for the background task
        asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.05))
        assert len(captured) == 1
        assert captured[0].method == "GET"
        assert captured[0].path == "/ping"
        assert captured[0].status_code == 200

    def test_sensitive_headers_are_stripped(self):
        """Authorization and x-api-key headers must not be stored."""
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
        client = TestClient(app, raise_server_exceptions=False)
        client.get(
            "/ping",
            headers={
                "Authorization": "Bearer secret-token",
                "X-API-Key": "my-key",
                "X-Custom": "keep-me",
            },
        )

        asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.05))
        assert len(captured) == 1
        headers = captured[0].headers
        assert "authorization" not in headers
        assert "x-api-key" not in headers
        assert "x-custom" in headers

    def test_request_body_is_captured(self):
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

        client = TestClient(app, raise_server_exceptions=False)
        client.post("/echo", content=b'{"tx": "0xabc"}')

        asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.05))
        assert len(captured) == 1
        assert b"0xabc" in captured[0].request_body
