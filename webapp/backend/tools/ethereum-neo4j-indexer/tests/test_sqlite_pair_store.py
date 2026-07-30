from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from eth_graph_indexer.checkpoint import Checkpoint
from eth_graph_indexer.models import BlockWrite, InteractionEdge
from eth_graph_indexer.pair_server import PairShardStore
from eth_graph_indexer.sqlite_pair_store import (
    SQLitePairStore,
    partition_index,
)

SOURCE = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
TARGET = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def create_shards(path: Path, partitions: int) -> None:
    for index in range(partitions):
        with sqlite3.connect(path / f"part-{index:02d}.sqlite3") as conn:
            conn.execute(
                """
                CREATE TABLE pair_ranges (
                    pair_id TEXT PRIMARY KEY,
                    source BLOB NOT NULL,
                    target BLOB NOT NULL,
                    first_block_number INTEGER NOT NULL,
                    last_block_number INTEGER NOT NULL
                )
                """
            )


def make_block(number: int, *, block_hash: str | None = None) -> BlockWrite:
    edge = InteractionEdge(
        tx_hash="0x" + str(number) * 64,
        block_number=number,
        from_address=SOURCE,
        to_address=TARGET,
        interaction_type="external",
        value_wei="0",
    )
    return BlockWrite([edge], number, block_hash or f"0xblock{number}")


def make_store(path: Path, partitions: int = 2) -> SQLitePairStore:
    create_shards(path, partitions)
    store = SQLitePairStore(
        path,
        partitions=partitions,
        bootstrap_checkpoint=Checkpoint(9, "0xblock9"),
    )
    store.verify_connectivity()
    store.ensure_schema()
    return store


def test_writes_ranges_and_advances_every_shard_checkpoint(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)

    assert store.write_blocks(
        [make_block(10), make_block(11)],
        checkpoint_id="default",
        batch_size=100,
    ) == (2, 1)

    pair_id = f"{SOURCE}:{TARGET}"
    partition = partition_index(pair_id, 2)
    with sqlite3.connect(tmp_path / f"part-{partition:02d}.sqlite3") as conn:
        assert conn.execute(
            """
            SELECT first_block_number, last_block_number
            FROM pair_ranges WHERE pair_id = ?
            """,
            (pair_id,),
        ).fetchone() == (10, 11)
    for index in range(2):
        with sqlite3.connect(tmp_path / f"part-{index:02d}.sqlite3") as conn:
            assert conn.execute(
                """
                SELECT last_processed_block, last_processed_block_hash
                FROM indexer_checkpoints WHERE id = 'default'
                """
            ).fetchone() == (11, "0xblock11")


def test_rejects_checkpoint_gap(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(RuntimeError, match="checkpoint gap"):
        store.write_blocks(
            [make_block(11)],
            checkpoint_id="default",
            batch_size=100,
        )


def test_rejects_skipped_block(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(RuntimeError, match="skipped SQLite block"):
        store.write_blocks(
            [make_block(10, block_hash="ERROR_SKIPPED")],
            checkpoint_id="default",
            batch_size=100,
        )


def test_http_store_observes_wal_backed_updates(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    reader = PairShardStore(tmp_path, 2)
    assert reader.lookup(SOURCE, TARGET).first_block_number is None

    store.write_blocks(
        [make_block(10)], checkpoint_id="default", batch_size=100
    )

    result = reader.lookup(SOURCE, TARGET)
    assert result.first_block_number == 10
    assert result.last_block_number == 10
