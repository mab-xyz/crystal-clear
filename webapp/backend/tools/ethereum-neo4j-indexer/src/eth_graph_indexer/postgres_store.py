"""PostgreSQL pair-range and checkpoint storage."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .checkpoint import Checkpoint
from .models import BlockWrite, InteractionEdge

PAIR_UPSERT_QUERY = """
INSERT INTO public.pair_ranges (
    source, target, first_block_number, last_block_number
) VALUES (%s, %s, %s, %s)
ON CONFLICT (source, target) DO UPDATE SET
    first_block_number = LEAST(
        pair_ranges.first_block_number,
        EXCLUDED.first_block_number
    ),
    last_block_number = GREATEST(
        pair_ranges.last_block_number,
        EXCLUDED.last_block_number
    )
""".strip()

CHECKPOINT_SELECT_QUERY = """
SELECT last_processed_block, last_processed_block_hash
FROM public.indexer_checkpoints
WHERE id = %s
""".strip()

CHECKPOINT_LOCK_QUERY = CHECKPOINT_SELECT_QUERY + " FOR UPDATE"

CHECKPOINT_UPSERT_QUERY = """
INSERT INTO public.indexer_checkpoints (
    id, last_processed_block, last_processed_block_hash, updated_at
) VALUES (%s, %s, %s, clock_timestamp())
ON CONFLICT (id) DO UPDATE SET
    last_processed_block = EXCLUDED.last_processed_block,
    last_processed_block_hash = EXCLUDED.last_processed_block_hash,
    updated_at = clock_timestamp()
""".strip()


def aggregate_records(
    blocks: Iterable[BlockWrite],
) -> dict[tuple[bytes, bytes], tuple[bytes, bytes, int, int]]:
    records: dict[tuple[bytes, bytes], tuple[bytes, bytes, int, int]] = {}
    for block in blocks:
        for edge in block.edges:
            record = edge.to_record()
            source = bytes(record["from"])
            target = bytes(record["to"])
            key = (source, target)
            first_block = int(record["firstBlockNumber"])
            last_block = int(record["lastBlockNumber"])
            existing = records.get(key)
            if existing is not None:
                first_block = min(existing[2], first_block)
                last_block = max(existing[3], last_block)
            records[key] = (source, target, first_block, last_block)
    return records


class PostgresStore:
    def __init__(self, dsn: str, *, connection: Any | None = None) -> None:
        if connection is not None:
            self._connection = connection
            return
        try:
            import psycopg
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "psycopg is required to use PostgresStore; install the project "
                "dependencies with `python -m pip install -e .`"
            ) from exc
        self._connection = psycopg.connect(dsn, autocommit=True)

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> PostgresStore:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def verify_connectivity(self) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

    def ensure_schema(self) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT source, target, first_block_number, last_block_number
                FROM public.pair_ranges
                LIMIT 0
                """
            )
            cursor.execute(
                """
                SELECT id, last_processed_block, last_processed_block_hash,
                       updated_at
                FROM public.indexer_checkpoints
                LIMIT 0
                """
            )

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        with self._connection.cursor() as cursor:
            cursor.execute(CHECKPOINT_SELECT_QUERY, (checkpoint_id,))
            row = cursor.fetchone()
        if row is None:
            return None
        return Checkpoint(int(row[0]), str(row[1]))

    def write_block(
        self,
        *,
        edges: list[InteractionEdge],
        block_number: int,
        block_hash: str,
        checkpoint_id: str,
        batch_size: int,
    ) -> tuple[int, int]:
        return self.write_blocks(
            [BlockWrite(edges, block_number, block_hash)],
            checkpoint_id=checkpoint_id,
            batch_size=batch_size,
        )

    @staticmethod
    def _validate_blocks(blocks: list[BlockWrite]) -> None:
        expected = list(range(blocks[0].block_number, blocks[-1].block_number + 1))
        actual = [block.block_number for block in blocks]
        if actual != expected:
            raise RuntimeError(
                f"refusing non-contiguous PostgreSQL block batch: {actual}"
            )
        if any(block.block_hash == "ERROR_SKIPPED" for block in blocks):
            raise RuntimeError("refusing to checkpoint a skipped PostgreSQL block")

    @staticmethod
    def _validate_checkpoint_advance(
        checkpoint: Checkpoint | None, blocks: list[BlockWrite]
    ) -> None:
        if checkpoint is None:
            return
        first_block = blocks[0].block_number
        if first_block > checkpoint.last_processed_block + 1:
            raise RuntimeError(
                "refusing PostgreSQL checkpoint gap: "
                f"current={checkpoint.last_processed_block} next={first_block}"
            )
        for block in blocks:
            if block.block_number != checkpoint.last_processed_block:
                continue
            if block.block_hash != checkpoint.last_processed_block_hash:
                raise RuntimeError(
                    "PostgreSQL checkpoint hash disagrees at block "
                    f"{block.block_number}"
                )

    def write_blocks(
        self,
        blocks: list[BlockWrite],
        *,
        checkpoint_id: str,
        batch_size: int,
    ) -> tuple[int, int]:
        if not blocks:
            return 0, 0
        if batch_size < 1:
            raise ValueError("batch size must be positive")
        self._validate_blocks(blocks)
        records = list(aggregate_records(blocks).values())
        final_block = blocks[-1]

        with self._connection.transaction():
            with self._connection.cursor() as cursor:
                cursor.execute(CHECKPOINT_LOCK_QUERY, (checkpoint_id,))
                row = cursor.fetchone()
                checkpoint = (
                    None if row is None else Checkpoint(int(row[0]), str(row[1]))
                )
                self._validate_checkpoint_advance(checkpoint, blocks)

                for offset in range(0, len(records), batch_size):
                    cursor.executemany(
                        PAIR_UPSERT_QUERY,
                        records[offset : offset + batch_size],
                    )

                if (
                    checkpoint is None
                    or final_block.block_number > checkpoint.last_processed_block
                ):
                    cursor.execute(
                        CHECKPOINT_UPSERT_QUERY,
                        (
                            checkpoint_id,
                            final_block.block_number,
                            final_block.block_hash,
                        ),
                    )

        touched = {
            address
            for source, target, _first, _last in records
            for address in (source, target)
        }
        return len(touched), len(records)


__all__ = [
    "CHECKPOINT_SELECT_QUERY",
    "CHECKPOINT_UPSERT_QUERY",
    "PAIR_UPSERT_QUERY",
    "PostgresStore",
    "aggregate_records",
]
