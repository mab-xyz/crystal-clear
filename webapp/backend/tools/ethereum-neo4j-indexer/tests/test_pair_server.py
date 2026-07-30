from __future__ import annotations

import json
import sqlite3
from http.client import HTTPConnection
from pathlib import Path
from threading import Thread

import pytest

from eth_graph_indexer.pair_server import (
    PairHTTPServer,
    PairShardStore,
    make_pair_id,
    normalize_address,
    partition_index,
)

SOURCE = "0x0000000000000000000000000000000000000001"
TARGET = "0x0000000000000000000000000000000000000002"


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


def test_normalize_address() -> None:
    assert normalize_address(SOURCE.upper()) == SOURCE
    with pytest.raises(ValueError, match="40 hexadecimal"):
        normalize_address("0x1234")
    with pytest.raises(ValueError, match="hexadecimal"):
        normalize_address("0x" + "z" * 40)


def test_lookup_and_block_comparison(tmp_path: Path) -> None:
    partitions = 2
    create_shards(tmp_path, partitions)
    pair_id = make_pair_id(SOURCE, TARGET)
    partition = partition_index(pair_id, partitions)
    with sqlite3.connect(tmp_path / f"part-{partition:02d}.sqlite3") as conn:
        conn.execute(
            "INSERT INTO pair_ranges VALUES (?, ?, ?, ?, ?)",
            (pair_id, bytes.fromhex(SOURCE[2:]), bytes.fromhex(TARGET[2:]), 10, 20),
        )

    store = PairShardStore(tmp_path, partitions)
    result = store.lookup(SOURCE, TARGET)

    assert result.first_block_number == 10
    assert result.last_block_number == 20
    assert not result.seen_at_or_before(9)
    assert result.seen_at_or_before(10)


def test_missing_pair_is_not_seen(tmp_path: Path) -> None:
    create_shards(tmp_path, 2)
    result = PairShardStore(tmp_path, 2).lookup(SOURCE, TARGET)
    assert result.first_block_number is None
    assert not result.seen_at_or_before(100)


def test_batch_route_preserves_order_and_missing_pairs(tmp_path: Path) -> None:
    create_shards(tmp_path, 2)
    pair_id = make_pair_id(SOURCE, TARGET)
    partition = partition_index(pair_id, 2)
    with sqlite3.connect(tmp_path / f"part-{partition:02d}.sqlite3") as conn:
        conn.execute(
            "INSERT INTO pair_ranges VALUES (?, ?, ?, ?, ?)",
            (pair_id, bytes.fromhex(SOURCE[2:]), bytes.fromhex(TARGET[2:]), 10, 20),
        )

    server = PairHTTPServer(("127.0.0.1", 0), PairShardStore(tmp_path, 2))
    thread = Thread(target=server.serve_forever)
    thread.start()
    connection = HTTPConnection(*server.server_address, timeout=5)
    request_body = json.dumps(
        {
            "block": 10,
            "pairs": [
                {"source": SOURCE, "target": TARGET},
                {"source": TARGET, "target": SOURCE},
                {"source": SOURCE, "target": TARGET},
            ],
        }
    )
    try:
        connection.request(
            "POST",
            "/v1/pair-seen/batch",
            body=request_body,
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        response_body = json.loads(response.read())
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join()

    assert response.status == 200
    assert response_body["count"] == 3
    assert [
        result["seenAtOrBeforeBlock"] for result in response_body["results"]
    ] == [True, False, True]
    assert response_body["results"][0]["firstBlockNumber"] == 10
