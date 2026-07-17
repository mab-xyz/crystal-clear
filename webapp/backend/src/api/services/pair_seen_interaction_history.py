from __future__ import annotations

import json
from collections.abc import Iterable
from urllib.request import Request, urlopen

from src.api.core.config import settings

PairKey = tuple[str, str]


def _normalize_address(address: str | None) -> str | None:
    if not address:
        return None
    value = address.strip().lower()
    if not value.startswith("0x") or len(value) != 42:
        return None
    try:
        bytes.fromhex(value[2:])
    except ValueError:
        return None
    return value


class PairSeenInteractionHistory:
    """Batch client for the directed historical pair service."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        batch_size: int | None = None,
    ) -> None:
        self._url = (
            base_url or settings.pair_seen_service_url
        ).rstrip("/") + "/v1/pair-seen/batch"
        self._timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.pair_seen_timeout_seconds
        )
        self._batch_size = max(
            1,
            batch_size
            if batch_size is not None
            else settings.pair_seen_batch_size,
        )

    def has_pairs_seen(
        self,
        entries: Iterable[PairKey],
        *,
        block: int,
    ) -> dict[PairKey, bool]:
        if block < 0:
            raise ValueError("history block must be non-negative")

        normalized_pairs: set[PairKey] = set()
        for source, target in entries:
            source_norm = _normalize_address(source)
            target_norm = _normalize_address(target)
            if not source_norm or not target_norm:
                raise ValueError(f"invalid interaction pair: {source} -> {target}")
            normalized_pairs.add((source_norm, target_norm))

        ordered_pairs = sorted(normalized_pairs)
        found: dict[PairKey, bool] = {}
        for offset in range(0, len(ordered_pairs), self._batch_size):
            batch = ordered_pairs[offset : offset + self._batch_size]
            found.update(self._request_batch(batch, block=block))

        missing = normalized_pairs.difference(found)
        if missing:
            raise RuntimeError(
                f"pair-seen response omitted {len(missing)} requested pair(s)"
            )
        return found

    def _request_batch(
        self,
        pairs: list[PairKey],
        *,
        block: int,
    ) -> dict[PairKey, bool]:
        payload = json.dumps(
            {
                "block": block,
                "pairs": [
                    {"source": source, "target": target}
                    for source, target in pairs
                ],
            }
        ).encode("utf-8")
        request = Request(
            self._url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self._timeout_seconds) as response:
            body = json.load(response)

        results = body.get("results")
        if not isinstance(results, list):
            raise RuntimeError("pair-seen response has no results list")

        found: dict[PairKey, bool] = {}
        for item in results:
            if not isinstance(item, dict):
                raise RuntimeError("pair-seen result is not an object")
            source = _normalize_address(item.get("source"))
            target = _normalize_address(item.get("target"))
            seen = item.get("seenAtOrBeforeBlock")
            if not source or not target or not isinstance(seen, bool):
                raise RuntimeError("pair-seen result is malformed")
            found[(source, target)] = seen
        return found


_pair_seen_history: PairSeenInteractionHistory | None = None


def get_pair_seen_interaction_history() -> PairSeenInteractionHistory:
    global _pair_seen_history
    if _pair_seen_history is None:
        _pair_seen_history = PairSeenInteractionHistory()
    return _pair_seen_history


__all__ = [
    "PairKey",
    "PairSeenInteractionHistory",
    "get_pair_seen_interaction_history",
]
