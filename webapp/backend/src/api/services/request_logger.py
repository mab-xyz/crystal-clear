"""
Service for persisting API requests to multiple backends simultaneously.

Backends:
- LocalDiskBackend   – appends newline-delimited JSON to a daily file on disk.
- GitHubBackend      – commits a JSON file per request to the mab-xyz/database
                       repository via the GitHub Contents API.
- PostgresBackend    – stub; no table exists yet, logs a debug message only.
"""

import asyncio
import base64
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests as http_requests
from loguru import logger


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------


class RequestRecord:
    """Immutable snapshot of a single API request / response cycle."""

    def __init__(
        self,
        *,
        timestamp: datetime,
        method: str,
        path: str,
        query_string: str,
        headers: dict[str, str],
        request_body: bytes,
        status_code: int,
        response_time_ms: float,
    ) -> None:
        self.timestamp = timestamp
        self.method = method
        self.path = path
        self.query_string = query_string
        self.headers = headers
        self.request_body = request_body
        self.status_code = status_code
        self.response_time_ms = response_time_ms

    def to_dict(self) -> dict[str, Any]:
        body_str: str | None = None
        if self.request_body:
            try:
                body_str = self.request_body.decode("utf-8")
            except UnicodeDecodeError:
                body_str = self.request_body.hex()
        return {
            "timestamp": self.timestamp.isoformat(),
            "method": self.method,
            "path": self.path,
            "query_string": self.query_string,
            "headers": self.headers,
            "request_body": body_str,
            "status_code": self.status_code,
            "response_time_ms": round(self.response_time_ms, 2),
        }


# ---------------------------------------------------------------------------
# Abstract backend
# ---------------------------------------------------------------------------


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, record: RequestRecord) -> None:
        """Persist *record*.  Must not raise – log and swallow errors."""


# ---------------------------------------------------------------------------
# Local-disk backend
# ---------------------------------------------------------------------------


class LocalDiskBackend(StorageBackend):
    """Appends one JSON object per line to ``<log_dir>/YYYY-MM-DD.jsonl``."""

    def __init__(self, log_dir: str) -> None:
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, record: RequestRecord) -> None:
        date_str = record.timestamp.strftime("%Y-%m-%d")
        log_file = self._log_dir / f"{date_str}.jsonl"
        line = json.dumps(record.to_dict()) + "\n"
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._append_line, log_file, line)

    # ------------------------------------------------------------------
    # sync helper (runs in thread-pool executor)
    # ------------------------------------------------------------------

    @staticmethod
    def _append_line(log_file: Path, line: str) -> None:
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write(line)


# ---------------------------------------------------------------------------
# GitHub backend
# ---------------------------------------------------------------------------


class GitHubBackend(StorageBackend):
    """Commits one JSON file per request to a GitHub repository.

    File layout inside the repo::

        api_requests/YYYY/MM/DD/<HH-MM-SS>-<uuid8>.json
    """

    _API_ROOT = "https://api.github.com"

    def __init__(self, token: str, repo: str = "mab-xyz/database") -> None:
        self._token = token
        self._repo = repo

    async def save(self, record: RequestRecord) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._push, record)

    # ------------------------------------------------------------------
    # sync helper (runs in thread-pool executor)
    # ------------------------------------------------------------------

    def _push(self, record: RequestRecord) -> None:
        ts = record.timestamp
        uid = uuid.uuid4().hex[:8]
        file_path = (
            f"api_requests/{ts.strftime('%Y/%m/%d')}/"
            f"{ts.strftime('%H-%M-%S')}-{uid}.json"
        )
        content_bytes = json.dumps(record.to_dict(), indent=2).encode("utf-8")
        encoded = base64.b64encode(content_bytes).decode("utf-8")

        url = f"{self._API_ROOT}/repos/{self._repo}/contents/{file_path}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        payload = {
            "message": (
                f"log: {record.method} {record.path} "
                f"→ {record.status_code}"
            ),
            "content": encoded,
        }
        try:
            resp = http_requests.put(
                url, json=payload, headers=headers, timeout=10
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(
                f"GitHubBackend: failed to save request log "
                f"({record.method} {record.path}): {exc}"
            )


# ---------------------------------------------------------------------------
# Postgres backend (stub)
# ---------------------------------------------------------------------------


class PostgresBackend(StorageBackend):
    """Stub implementation – no table yet.

    Once a dedicated ``api_requests`` table is created this class should be
    updated to perform the actual INSERT via SQLModel / SQLAlchemy.
    """

    async def save(self, record: RequestRecord) -> None:
        # TODO: insert into api_requests table when schema is ready
        logger.debug(
            f"[postgres-stub] skipping persist for "
            f"{record.method} {record.path}"
        )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


class RequestLogger:
    """Fan-out dispatcher: saves a record to all backends concurrently.

    Failures in individual backends are logged and swallowed so that a
    storage outage never affects the API response.
    """

    def __init__(self, backends: list[StorageBackend]) -> None:
        self._backends = backends

    async def log(self, record: RequestRecord) -> None:
        results = await asyncio.gather(
            *[b.save(record) for b in self._backends],
            return_exceptions=True,
        )
        for backend, result in zip(self._backends, results):
            if isinstance(result, Exception):
                logger.warning(
                    f"RequestLogger: backend "
                    f"{backend.__class__.__name__} raised: {result}"
                )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_request_logger(
    *,
    log_dir: str,
    github_token: str | None,
    github_repo: str = "mab-xyz/database",
) -> RequestLogger:
    """Construct a :class:`RequestLogger` wired to the configured backends."""
    backends: list[StorageBackend] = [
        LocalDiskBackend(log_dir),
        PostgresBackend(),
    ]
    if github_token:
        backends.append(GitHubBackend(github_token, repo=github_repo))
    return RequestLogger(backends)
