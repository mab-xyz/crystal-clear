from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import TextClause

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


@lru_cache(maxsize=32)
def _pair_lookup_statement(pair_count: int) -> TextClause:
    values = ", ".join(
        (
            f"(CAST(:source_{index} AS bytea), "
            f"CAST(:target_{index} AS bytea), {index})"
        )
        for index in range(pair_count)
    )
    return text(
        f"""
        WITH requested(source, target, ordinal) AS (
            VALUES {values}
        )
        SELECT requested.ordinal
        FROM requested
        WHERE EXISTS (
            SELECT 1
            FROM public.pair_ranges AS pair_range
            WHERE pair_range.source = requested.source
              AND pair_range.target = requested.target
              AND pair_range.first_block_number <= :block
        )
        """
    )


class PostgresInteractionHistory:
    """Batch reader for directed historical interaction pairs."""

    def __init__(self, *, batch_size: int | None = None) -> None:
        self._batch_size = max(
            1,
            batch_size
            if batch_size is not None
            else settings.pair_history_batch_size,
        )

    def has_pairs_seen(
        self,
        session: Session,
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
        found = dict.fromkeys(ordered_pairs, False)
        for offset in range(0, len(ordered_pairs), self._batch_size):
            batch = ordered_pairs[offset : offset + self._batch_size]
            params: dict[str, object] = {"block": block}
            for index, (source, target) in enumerate(batch):
                params[f"source_{index}"] = bytes.fromhex(source[2:])
                params[f"target_{index}"] = bytes.fromhex(target[2:])

            seen_ordinals = session.execute(
                _pair_lookup_statement(len(batch)),
                params,
            ).scalars()
            for ordinal in seen_ordinals:
                found[batch[int(ordinal)]] = True
        return found


_postgres_history: PostgresInteractionHistory | None = None


def get_postgres_interaction_history() -> PostgresInteractionHistory:
    global _postgres_history
    if _postgres_history is None:
        _postgres_history = PostgresInteractionHistory()
    return _postgres_history


__all__ = [
    "PairKey",
    "PostgresInteractionHistory",
    "get_postgres_interaction_history",
]
