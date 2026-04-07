import time
from collections import deque
from typing import Any

from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.types import RPCEndpoint, RPCResponse

HEALTH_WINDOW = 20
FAST_THRESHOLD_SECONDS = 0.1


class RpcHealthTracker:
    """
    Tracks per-URL health as the ratio of requests that completed
    successfully in under FAST_THRESHOLD_SECONDS, over a sliding
    window of the last HEALTH_WINDOW requests.
    """

    def __init__(self) -> None:
        self._windows: dict[str, deque[bool]] = {}

    def record(self, url: str, fast: bool) -> None:
        if url not in self._windows:
            self._windows[url] = deque(maxlen=HEALTH_WINDOW)
        self._windows[url].append(fast)

    def health_ratio(self, url: str) -> float:
        """Return health ratio in [0, 1]. Returns 0.5 when no data yet."""
        window = self._windows.get(url)
        if not window:
            return 0.5
        return sum(window) / len(window)


tracker = RpcHealthTracker()


class TrackedHTTPProvider(HTTPProvider):
    """
    Web3 HTTPProvider that records each request's timing to RpcHealthTracker.
    """

    def __init__(self, url: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(url, *args, **kwargs)
        self._tracked_url = url

    def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        start = time.monotonic()
        try:
            response = super().make_request(method, params)
            elapsed = time.monotonic() - start
            tracker.record(self._tracked_url, elapsed < FAST_THRESHOLD_SECONDS)
            return response
        except Exception:
            tracker.record(self._tracked_url, False)
            raise


def make_tracked_w3(url: str) -> Web3:
    return Web3(TrackedHTTPProvider(url))
