"""Tests for src/api/services/request_logger.py."""

import asyncio
import base64
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.api.services.request_logger import (
    GitHubBackend,
    LocalDiskBackend,
    PostgresBackend,
    RequestLogger,
    RequestRecord,
    build_request_logger,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(**overrides) -> RequestRecord:
    defaults = dict(
        timestamp=datetime(2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc),
        method="GET",
        path="/v1/analysis/0xabc/risk",
        query_string="",
        headers={"content-type": "application/json"},
        request_body=b'{"key": "value"}',
        status_code=200,
        response_time_ms=42.5,
    )
    defaults.update(overrides)
    return RequestRecord(**defaults)


# ---------------------------------------------------------------------------
# RequestRecord
# ---------------------------------------------------------------------------


class TestRequestRecord:
    def test_to_dict_utf8_body(self):
        record = _make_record(request_body=b'{"hello": "world"}')
        d = record.to_dict()
        assert d["request_body"] == '{"hello": "world"}'

    def test_to_dict_binary_body_hex_fallback(self):
        record = _make_record(request_body=b"\xff\xfe\x00")
        d = record.to_dict()
        assert d["request_body"] == "fffe00"

    def test_to_dict_empty_body(self):
        record = _make_record(request_body=b"")
        d = record.to_dict()
        assert d["request_body"] is None

    def test_to_dict_fields(self):
        record = _make_record()
        d = record.to_dict()
        assert d["method"] == "GET"
        assert d["path"] == "/v1/analysis/0xabc/risk"
        assert d["status_code"] == 200
        assert d["response_time_ms"] == 42.5
        assert "timestamp" in d

    def test_to_dict_response_time_rounded(self):
        record = _make_record(response_time_ms=123.456789)
        d = record.to_dict()
        assert d["response_time_ms"] == 123.46


# ---------------------------------------------------------------------------
# LocalDiskBackend
# ---------------------------------------------------------------------------


class TestLocalDiskBackend:
    def test_creates_log_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "nested", "logs")
            backend = LocalDiskBackend(target)
            assert Path(target).is_dir()

    def test_saves_jsonl_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = LocalDiskBackend(tmp)
            record = _make_record()
            asyncio.run(backend.save(record))

            log_file = Path(tmp) / "2024-06-15.jsonl"
            assert log_file.exists()
            lines = log_file.read_text().splitlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["method"] == "GET"
            assert data["status_code"] == 200

    def test_appends_multiple_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = LocalDiskBackend(tmp)
            asyncio.run(backend.save(_make_record()))
            asyncio.run(backend.save(_make_record(method="POST")))

            log_file = Path(tmp) / "2024-06-15.jsonl"
            lines = log_file.read_text().splitlines()
            assert len(lines) == 2

    def test_different_dates_different_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = LocalDiskBackend(tmp)
            r1 = _make_record(
                timestamp=datetime(2024, 6, 15, tzinfo=timezone.utc)
            )
            r2 = _make_record(
                timestamp=datetime(2024, 6, 16, tzinfo=timezone.utc)
            )
            asyncio.run(backend.save(r1))
            asyncio.run(backend.save(r2))

            assert (Path(tmp) / "2024-06-15.jsonl").exists()
            assert (Path(tmp) / "2024-06-16.jsonl").exists()


# ---------------------------------------------------------------------------
# GitHubBackend
# ---------------------------------------------------------------------------


class TestGitHubBackend:
    def test_successful_push(self):
        backend = GitHubBackend(token="tok", repo="org/db")
        record = _make_record()

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None

        with patch(
            "src.api.services.request_logger.http_requests.put",
            return_value=mock_response,
        ) as mock_put:
            asyncio.run(backend.save(record))

        mock_put.assert_called_once()
        call_kwargs = mock_put.call_args
        url = call_kwargs[0][0]
        payload = call_kwargs[1]["json"]

        assert "org/db" in url
        assert "api_requests/2024/06/15/" in url
        assert payload["message"].startswith("log: GET")
        # content must be valid base64-encoded JSON
        decoded = base64.b64decode(payload["content"]).decode("utf-8")
        data = json.loads(decoded)
        assert data["method"] == "GET"

    def test_uses_bearer_token(self):
        backend = GitHubBackend(token="my-secret-token", repo="org/db")
        record = _make_record()

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None

        with patch(
            "src.api.services.request_logger.http_requests.put",
            return_value=mock_response,
        ) as mock_put:
            asyncio.run(backend.save(record))

        headers = mock_put.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer my-secret-token"

    def test_swallows_http_error(self):
        """A network error must not propagate out of save()."""
        backend = GitHubBackend(token="tok", repo="org/db")
        record = _make_record()

        with patch(
            "src.api.services.request_logger.http_requests.put",
            side_effect=Exception("network down"),
        ):
            # Should not raise
            asyncio.run(backend.save(record))

    def test_file_path_contains_datetime(self):
        backend = GitHubBackend(token="tok", repo="org/db")
        record = _make_record(
            timestamp=datetime(2025, 1, 7, 9, 5, 3, tzinfo=timezone.utc)
        )

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None

        with patch(
            "src.api.services.request_logger.http_requests.put",
            return_value=mock_response,
        ) as mock_put:
            asyncio.run(backend.save(record))

        url = mock_put.call_args[0][0]
        assert "2025/01/07" in url
        assert "09-05-03" in url


# ---------------------------------------------------------------------------
# PostgresBackend
# ---------------------------------------------------------------------------


class TestPostgresBackend:
    def test_save_does_not_raise(self):
        backend = PostgresBackend()
        record = _make_record()
        # Must complete without raising
        asyncio.run(backend.save(record))


# ---------------------------------------------------------------------------
# RequestLogger dispatcher
# ---------------------------------------------------------------------------


class TestRequestLogger:
    def test_calls_all_backends(self):
        calls = []

        class _FakeBackend(LocalDiskBackend):
            def __init__(self, name):
                self._name = name

            async def save(self, record):
                calls.append(self._name)

        logger = RequestLogger([_FakeBackend("a"), _FakeBackend("b")])
        asyncio.run(logger.log(_make_record()))
        assert calls == ["a", "b"]

    def test_failed_backend_does_not_prevent_others(self):
        from src.api.services.request_logger import StorageBackend

        results = []

        class BrokenB(StorageBackend):
            async def save(self, record):
                raise RuntimeError("boom")

        class GoodB(StorageBackend):
            async def save(self, record):
                results.append("ok")

        rl = RequestLogger([BrokenB(), GoodB()])
        asyncio.run(rl.log(_make_record()))
        assert results == ["ok"]


# ---------------------------------------------------------------------------
# build_request_logger factory
# ---------------------------------------------------------------------------


class TestBuildRequestLogger:
    def test_without_github_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            rl = build_request_logger(
                log_dir=tmp,
                github_token=None,
            )
        backend_types = [type(b).__name__ for b in rl._backends]
        assert "LocalDiskBackend" in backend_types
        assert "PostgresBackend" in backend_types
        assert "GitHubBackend" not in backend_types

    def test_with_github_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            rl = build_request_logger(
                log_dir=tmp,
                github_token="tok",
                github_repo="org/db",
            )
        backend_types = [type(b).__name__ for b in rl._backends]
        assert "GitHubBackend" in backend_types

    def test_github_backend_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            rl = build_request_logger(
                log_dir=tmp,
                github_token="tok",
                github_repo="custom/repo",
            )
        github_backends = [
            b for b in rl._backends if type(b).__name__ == "GitHubBackend"
        ]
        assert len(github_backends) == 1
        assert github_backends[0]._repo == "custom/repo"
