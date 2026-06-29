"""Synchronous JSON-RPC client with batching and retry support."""

from __future__ import annotations

import itertools
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Iterable

import httpx

LOGGER = logging.getLogger(__name__)


class JsonRpcError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        method: str | None = None,
        code: int | None = None,
        data: Any = None,
    ) -> None:
        super().__init__(message)
        self.method = method
        self.code = code
        self.data = data


@dataclass(frozen=True, slots=True)
class RpcCall:
    method: str
    params: list[Any]


class JsonRpcClient:
    def __init__(
        self,
        url: str,
        *,
        timeout: float = 60.0,
        max_retries: int = 4,
        retry_backoff: float = 0.5,
        client: httpx.Client | None = None,
    ) -> None:
        self.url = url
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self._ids = itertools.count(1)
        self._id_lock = threading.Lock()
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> JsonRpcClient:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _post(self, payload: dict | list[dict]) -> Any:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.post(self.url, json=payload)
                response.raise_for_status()
                return response.json()
            except (
                httpx.HTTPError,
                ValueError,
            ) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                delay = self.retry_backoff * (2**attempt)
                LOGGER.warning(
                    "RPC request failed; retrying",
                    extra={"attempt": attempt + 1, "delay_seconds": delay},
                )
                time.sleep(delay)
        raise JsonRpcError(
            f"RPC request to {self.url} failed after "
            f"{self.max_retries + 1} attempts: {last_error}"
        ) from last_error

    @staticmethod
    def _result(response: Any, *, method: str) -> Any:
        if not isinstance(response, dict):
            raise JsonRpcError(
                f"{method} returned a malformed JSON-RPC response", method=method
            )
        error = response.get("error")
        if error:
            raise JsonRpcError(
                f"{method} failed: {error.get('message', 'unknown RPC error')}",
                method=method,
                code=error.get("code"),
                data=error.get("data"),
            )
        if "result" not in response:
            raise JsonRpcError(
                f"{method} response has no result field", method=method
            )
        return response["result"]

    def call(self, method: str, params: list[Any] | None = None) -> Any:
        request_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or [],
        }
        return self._result(self._post(payload), method=method)

    def batch_call(self, calls: Iterable[RpcCall]) -> list[Any]:
        pending = list(calls)
        if not pending:
            return []
        requests = []
        methods_by_id: dict[int, str] = {}
        for call in pending:
            request_id = self._next_id()
            methods_by_id[request_id] = call.method
            requests.append(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": call.method,
                    "params": call.params,
                }
            )
        raw = self._post(requests)
        if not isinstance(raw, list):
            raise JsonRpcError("batch call returned a non-list response")
        by_id = {
            item.get("id"): item for item in raw if isinstance(item, dict)
        }
        results: list[Any] = []
        for request in requests:
            request_id = request["id"]
            response = by_id.get(request_id)
            if response is None:
                raise JsonRpcError(
                    f"batch response omitted request id {request_id}",
                    method=methods_by_id[request_id],
                )
            results.append(
                self._result(response, method=methods_by_id[request_id])
            )
        return results

    def _next_id(self) -> int:
        with self._id_lock:
            return next(self._ids)
