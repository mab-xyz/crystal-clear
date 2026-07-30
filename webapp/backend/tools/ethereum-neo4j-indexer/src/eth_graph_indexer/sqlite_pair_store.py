"""Live, gap-checked pair range updates across partitioned SQLite shards."""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol

from .checkpoint import Checkpoint
from .models import BlockWrite, InteractionEdge

LOGGER = logging.getLogger(__name__)

PAIR_UPSERT_QUERY = """
INSERT INTO pair_ranges (
    pair_id, source, target, first_block_number, last_block_number
) VALUES (?, ?, ?, ?, ?)
ON CONFLICT(pair_id) DO UPDATE SET
    first_block_number = min(
        pair_ranges.first_block_number,
        excluded.first_block_number
    ),
    last_block_number = max(
        pair_ranges.last_block_number,
        excluded.last_block_number
    )
""".strip()

CHECKPOINT_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS indexer_checkpoints (
    id TEXT PRIMARY KEY,
    last_processed_block INTEGER NOT NULL,
    last_processed_block_hash TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
""".strip()

CHECKPOINT_UPSERT_QUERY = """
INSERT INTO indexer_checkpoints (
    id, last_processed_block, last_processed_block_hash, updated_at
) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
ON CONFLICT(id) DO UPDATE SET
    last_processed_block = excluded.last_processed_block,
    last_processed_block_hash = excluded.last_processed_block_hash,
    updated_at = CURRENT_TIMESTAMP
""".strip()


class WritableStore(Protocol):
    def verify_connectivity(self) -> None: ...

    def ensure_schema(self) -> None: ...

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None: ...

    def write_blocks(
        self,
        blocks: list[BlockWrite],
        *,
        checkpoint_id: str,
        batch_size: int,
    ) -> tuple[int, int]: ...


def partition_index(pair_id: str, partitions: int) -> int:
    digest = hashlib.blake2b(
        pair_id.encode("ascii"), digest_size=8
    ).digest()
    return int.from_bytes(digest, "big") % partitions


def aggregate_records(
    blocks: Iterable[BlockWrite],
) -> dict[str, tuple[str, bytes, bytes, int, int]]:
    records: dict[str, tuple[str, bytes, bytes, int, int]] = {}
    for block in blocks:
        for edge in block.edges:
            record = edge.to_record()
            pair_id = record["pairId"]
            existing = records.get(pair_id)
            first_block = int(record["firstBlockNumber"])
            last_block = int(record["lastBlockNumber"])
            if existing is not None:
                first_block = min(existing[3], first_block)
                last_block = max(existing[4], last_block)
            records[pair_id] = (
                pair_id,
                record["from"],
                record["to"],
                first_block,
                last_block,
            )
    return records


class SQLitePairStore:
    def __init__(
        self,
        shard_dir: Path,
        *,
        partitions: int = 16,
        bootstrap_checkpoint: Checkpoint | None = None,
        checkpoint_id: str = "default",
    ) -> None:
        if partitions < 1:
            raise ValueError("SQLite partitions must be positive")
        self.shard_dir = shard_dir.resolve()
        self.partitions = partitions
        self.bootstrap_checkpoint = bootstrap_checkpoint
        self.checkpoint_id = checkpoint_id
        self.shard_paths = tuple(
            self.shard_dir / f"part-{index:02d}.sqlite3"
            for index in range(partitions)
        )

    def __enter__(self) -> SQLitePairStore:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    @staticmethod
    def _connect(path: Path) -> sqlite3.Connection:
        conn = sqlite3.connect(path, timeout=60)
        conn.execute("PRAGMA busy_timeout = 60000")
        conn.execute("PRAGMA synchronous = FULL")
        return conn

    def verify_connectivity(self) -> None:
        missing = [str(path) for path in self.shard_paths if not path.is_file()]
        if missing:
            raise RuntimeError(f"missing SQLite shards: {', '.join(missing)}")
        for path in self.shard_paths:
            with self._connect(path) as conn:
                conn.execute("SELECT 1 FROM pair_ranges LIMIT 1").fetchone()

    def ensure_schema(self) -> None:
        for path in self.shard_paths:
            with self._connect(path) as conn:
                journal_mode = conn.execute("PRAGMA journal_mode = WAL").fetchone()
                if not journal_mode or str(journal_mode[0]).lower() != "wal":
                    raise RuntimeError(f"could not enable WAL mode for {path}")
                conn.execute(CHECKPOINT_TABLE_QUERY)

        checkpoints = self._read_checkpoints(self.checkpoint_id)
        if all(checkpoint is None for checkpoint in checkpoints):
            if self.bootstrap_checkpoint is None:
                raise RuntimeError(
                    "SQLite checkpoint is uninitialized; provide a bootstrap "
                    "block and hash"
                )
            self._bootstrap(self.checkpoint_id, self.bootstrap_checkpoint)
        elif any(checkpoint is None for checkpoint in checkpoints):
            raise RuntimeError("SQLite checkpoint is missing from some shards")

    def _bootstrap(self, checkpoint_id: str, checkpoint: Checkpoint) -> None:
        for path in self.shard_paths:
            with self._connect(path) as conn:
                conn.execute(
                    CHECKPOINT_UPSERT_QUERY,
                    (
                        checkpoint_id,
                        checkpoint.last_processed_block,
                        checkpoint.last_processed_block_hash,
                    ),
                )
        LOGGER.info(
            "Bootstrapped SQLite pair checkpoints",
            extra={
                "checkpoint_id": checkpoint_id,
                "block_number": checkpoint.last_processed_block,
                "partitions": self.partitions,
            },
        )

    def _read_checkpoint(
        self, path: Path, checkpoint_id: str
    ) -> Checkpoint | None:
        with self._connect(path) as conn:
            row = conn.execute(
                """
                SELECT last_processed_block, last_processed_block_hash
                FROM indexer_checkpoints
                WHERE id = ?
                """,
                (checkpoint_id,),
            ).fetchone()
        if row is None:
            return None
        return Checkpoint(int(row[0]), str(row[1]))

    def _read_checkpoints(
        self, checkpoint_id: str
    ) -> list[Checkpoint | None]:
        return [
            self._read_checkpoint(path, checkpoint_id)
            for path in self.shard_paths
        ]

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        checkpoints = self._read_checkpoints(checkpoint_id)
        present = [checkpoint for checkpoint in checkpoints if checkpoint]
        if not present:
            return None
        if len(present) != self.partitions:
            raise RuntimeError("SQLite checkpoint is missing from some shards")
        earliest = min(present, key=lambda checkpoint: checkpoint.last_processed_block)
        matching_hashes = {
            checkpoint.last_processed_block_hash
            for checkpoint in present
            if checkpoint.last_processed_block == earliest.last_processed_block
        }
        if len(matching_hashes) != 1:
            raise RuntimeError("SQLite checkpoint hashes disagree across shards")
        if any(checkpoint != earliest for checkpoint in present):
            LOGGER.warning(
                "SQLite shard checkpoints differ; replaying from earliest",
                extra={
                    "earliest_block": earliest.last_processed_block,
                    "latest_block": max(
                        checkpoint.last_processed_block
                        for checkpoint in present
                    ),
                },
            )
        return earliest

    @staticmethod
    def _validate_blocks(blocks: list[BlockWrite]) -> None:
        expected = list(range(blocks[0].block_number, blocks[-1].block_number + 1))
        actual = [block.block_number for block in blocks]
        if actual != expected:
            raise RuntimeError(
                f"refusing non-contiguous SQLite block batch: {actual}"
            )
        if any(block.block_hash == "ERROR_SKIPPED" for block in blocks):
            raise RuntimeError("refusing to checkpoint a skipped SQLite block")

    @staticmethod
    def _validate_checkpoint_advance(
        checkpoint: Checkpoint | None, blocks: list[BlockWrite]
    ) -> None:
        if checkpoint is None:
            raise RuntimeError("SQLite checkpoint is uninitialized")
        first_block = blocks[0].block_number
        if first_block > checkpoint.last_processed_block + 1:
            raise RuntimeError(
                "refusing SQLite checkpoint gap: "
                f"current={checkpoint.last_processed_block} next={first_block}"
            )

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

    def write_blocks(
        self,
        blocks: list[BlockWrite],
        *,
        checkpoint_id: str,
        batch_size: int,
    ) -> tuple[int, int]:
        del batch_size
        if not blocks:
            return 0, 0
        self._validate_blocks(blocks)
        records = aggregate_records(blocks)
        records_by_partition: dict[
            int, list[tuple[str, bytes, bytes, int, int]]
        ] = {index: [] for index in range(self.partitions)}
        for pair_id, record in records.items():
            records_by_partition[
                partition_index(pair_id, self.partitions)
            ].append(record)

        final_block = blocks[-1]
        for index, path in enumerate(self.shard_paths):
            conn = self._connect(path)
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    """
                    SELECT last_processed_block, last_processed_block_hash
                    FROM indexer_checkpoints
                    WHERE id = ?
                    """,
                    (checkpoint_id,),
                ).fetchone()
                checkpoint = (
                    None
                    if row is None
                    else Checkpoint(int(row[0]), str(row[1]))
                )
                self._validate_checkpoint_advance(checkpoint, blocks)
                conn.executemany(PAIR_UPSERT_QUERY, records_by_partition[index])
                if (
                    checkpoint is None
                    or final_block.block_number
                    > checkpoint.last_processed_block
                ):
                    conn.execute(
                        CHECKPOINT_UPSERT_QUERY,
                        (
                            checkpoint_id,
                            final_block.block_number,
                            final_block.block_hash,
                        ),
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

        touched = {
            address
            for record in records.values()
            for address in (record[1], record[2])
        }
        return len(touched), len(records)


class MirroredStore:
    """Write SQLite first, then Neo4j, and resume from the older checkpoint."""

    def __init__(self, primary: WritableStore, mirror: SQLitePairStore) -> None:
        self.primary = primary
        self.mirror = mirror

    def verify_connectivity(self) -> None:
        self.primary.verify_connectivity()
        self.mirror.verify_connectivity()

    def ensure_schema(self) -> None:
        self.primary.ensure_schema()
        self.mirror.ensure_schema()

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        primary = self.primary.get_checkpoint(checkpoint_id)
        mirror = self.mirror.get_checkpoint(checkpoint_id)
        if primary is None:
            return mirror
        if mirror is None:
            return primary
        if (
            primary.last_processed_block == mirror.last_processed_block
            and primary.last_processed_block_hash
            != mirror.last_processed_block_hash
        ):
            raise RuntimeError(
                "Neo4j and SQLite checkpoint hashes disagree at block "
                f"{primary.last_processed_block}"
            )
        return min(
            (primary, mirror),
            key=lambda checkpoint: checkpoint.last_processed_block,
        )

    def write_block(self, **kwargs: Any) -> tuple[int, int]:
        self.mirror.write_block(**kwargs)
        return self.primary.write_block(**kwargs)

    def write_blocks(
        self,
        blocks: list[BlockWrite],
        *,
        checkpoint_id: str,
        batch_size: int,
    ) -> tuple[int, int]:
        self.mirror.write_blocks(
            blocks,
            checkpoint_id=checkpoint_id,
            batch_size=batch_size,
        )
        return self.primary.write_blocks(
            blocks,
            checkpoint_id=checkpoint_id,
            batch_size=batch_size,
        )
