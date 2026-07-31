from __future__ import annotations

from contextlib import contextmanager

import pytest

from eth_graph_indexer.models import BlockWrite, InteractionEdge
from eth_graph_indexer.postgres_store import PAIR_UPSERT_QUERY, PostgresStore

SOURCE = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
TARGET = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


class FakeCursor:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection
        self.row = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, query, params=None):
        normalized = " ".join(str(query).split())
        self.connection.executions.append((normalized, params))
        if "FROM public.indexer_checkpoints" in normalized:
            self.row = self.connection.checkpoint
        elif normalized.startswith("INSERT INTO public.indexer_checkpoints"):
            assert params is not None
            self.connection.checkpoint = (params[1], params[2])
            self.row = None
        elif normalized == "SELECT 1":
            self.row = (1,)
        else:
            self.row = None

    def executemany(self, query, rows):
        normalized = " ".join(str(query).split())
        pending = list(rows)
        self.connection.executemany_calls.append((normalized, pending))
        for source, target, first_block, last_block in pending:
            key = (source, target)
            existing = self.connection.pairs.get(key)
            if existing is not None:
                first_block = min(existing[0], first_block)
                last_block = max(existing[1], last_block)
            self.connection.pairs[key] = (first_block, last_block)

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, checkpoint=None) -> None:
        self.checkpoint = checkpoint
        self.pairs = {}
        self.executions = []
        self.executemany_calls = []
        self.transactions = 0
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    @contextmanager
    def transaction(self):
        self.transactions += 1
        yield

    def close(self):
        self.closed = True


def make_block(number: int, *, block_hash: str | None = None) -> BlockWrite:
    edge = InteractionEdge(
        tx_hash="0x" + "1" * 64,
        block_number=number,
        from_address=SOURCE,
        to_address=TARGET,
        interaction_type="external",
        value_wei="0",
    )
    return BlockWrite([edge], number, block_hash or f"0xblock{number}")


def test_store_aggregates_ranges_and_advances_checkpoint_atomically() -> None:
    connection = FakeConnection(checkpoint=(9, "0xblock9"))
    store = PostgresStore("unused", connection=connection)

    assert store.write_blocks(
        [make_block(10), make_block(11)],
        checkpoint_id="default",
        batch_size=100,
    ) == (2, 1)

    key = (bytes.fromhex(SOURCE[2:]), bytes.fromhex(TARGET[2:]))
    assert connection.pairs[key] == (10, 11)
    assert connection.checkpoint == (11, "0xblock11")
    assert connection.transactions == 1


def test_store_replay_expands_range_without_moving_checkpoint_backwards() -> None:
    connection = FakeConnection(checkpoint=(11, "0xblock11"))
    store = PostgresStore("unused", connection=connection)

    store.write_blocks(
        [make_block(10), make_block(11)],
        checkpoint_id="default",
        batch_size=1,
    )

    assert connection.checkpoint == (11, "0xblock11")


def test_store_rejects_checkpoint_gap() -> None:
    store = PostgresStore(
        "unused", connection=FakeConnection(checkpoint=(9, "0xblock9"))
    )
    with pytest.raises(RuntimeError, match="checkpoint gap"):
        store.write_blocks(
            [make_block(11)], checkpoint_id="default", batch_size=100
        )


def test_store_rejects_skipped_block() -> None:
    store = PostgresStore(
        "unused", connection=FakeConnection(checkpoint=(9, "0xblock9"))
    )
    with pytest.raises(RuntimeError, match="skipped PostgreSQL block"):
        store.write_blocks(
            [make_block(10, block_hash="ERROR_SKIPPED")],
            checkpoint_id="default",
            batch_size=100,
        )


def test_pair_upsert_is_idempotent_range_merge() -> None:
    normalized = " ".join(PAIR_UPSERT_QUERY.split())
    assert "ON CONFLICT (source, target) DO UPDATE" in normalized
    assert "LEAST(" in normalized
    assert "GREATEST(" in normalized
