from pathlib import Path

from eth_graph_indexer.external_pair_aggregation import (
    AggregateConfig,
    AggregateState,
    LoadConfig,
    LoadState,
    connect_sqlite,
    fetch_sqlite_rows,
    flush_pair_rows,
    load_once,
    load_state,
    partition_index,
    resolve_source_paths,
    run_repartition,
    RepartitionConfig,
    RepartitionState,
)


def test_load_state_ignores_unknown_keys(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        """
        {
          "last_pair_id": "abc",
          "sqlite_rows_loaded": 3,
          "unknown_field": "ignored"
        }
        """,
        encoding="utf-8",
    )

    state = load_state(path, LoadState)

    assert state.last_pair_id == "abc"
    assert state.sqlite_rows_loaded == 3


def test_flush_pair_rows_merges_ranges(tmp_path: Path) -> None:
    conn = connect_sqlite(tmp_path / "pairs.sqlite3", cache_mb=64)
    try:
        flush_pair_rows(
            conn,
            [
                ("p1", b"a" * 20, b"b" * 20, 12, 12),
                ("p1", b"a" * 20, b"b" * 20, 10, 18),
            ],
        )

        rows = fetch_sqlite_rows(conn, after_pair_id="", limit=10)

        assert rows == [
            {
                "pairId": "p1",
                "source": b"a" * 20,
                "target": b"b" * 20,
                "firstBlockNumber": 10,
                "lastBlockNumber": 18,
            }
        ]
    finally:
        conn.close()


def test_load_once_updates_cursor_and_counts(tmp_path: Path, monkeypatch) -> None:
    conn = connect_sqlite(tmp_path / "pairs.sqlite3", cache_mb=64)
    flush_pair_rows(
        conn,
        [
            ("p1", b"a" * 20, b"b" * 20, 10, 18),
            ("p2", b"c" * 20, b"d" * 20, 20, 25),
        ],
    )
    config = LoadConfig(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="secret",
        env_file=tmp_path / "env",
        log_level="INFO",
        json_logs=False,
        sqlite_path=tmp_path / "pairs.sqlite3",
        state_file=tmp_path / "load-state.json",
        neo4j_batch_size=1,
    )
    state = LoadState()
    writes: list[list[dict[str, object]]] = []

    def fake_upsert(_driver, rows):
        writes.append(rows)

    monkeypatch.setattr(
        "eth_graph_indexer.external_pair_aggregation.upsert_neo4j_rows",
        fake_upsert,
    )

    try:
        worked = load_once(object(), conn, config, state)
        assert worked is True
        assert state.last_pair_id == "p1"
        assert state.sqlite_rows_loaded == 1
        assert len(writes) == 1
        assert writes[0][0]["firstBlockNumber"] == 10
    finally:
        conn.close()


def test_partition_index_is_stable() -> None:
    pair_id = "0x01:0x02"
    assert partition_index(pair_id, 16) == partition_index(pair_id, 16)


def test_resolve_source_paths_sorts_matches(tmp_path: Path) -> None:
    a = tmp_path / "b.sqlite3"
    b = tmp_path / "a.sqlite3"
    a.write_text("", encoding="utf-8")
    b.write_text("", encoding="utf-8")

    resolved = resolve_source_paths((str(tmp_path / "*.sqlite3"),))

    assert resolved == [b, a]


def test_run_repartition_writes_partitioned_rows(tmp_path: Path) -> None:
    source = connect_sqlite(tmp_path / "source.sqlite3", cache_mb=64)
    flush_pair_rows(
        source,
        [
            ("p1", b"a" * 20, b"b" * 20, 10, 12),
            ("p2", b"c" * 20, b"d" * 20, 20, 21),
        ],
    )
    source.close()

    config = RepartitionConfig(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="secret",
        env_file=tmp_path / "env",
        log_level="INFO",
        json_logs=False,
        source_glob=(str(tmp_path / "source.sqlite3"),),
        output_dir=tmp_path / "out",
        state_file=tmp_path / "repartition-state.json",
        partitions=4,
        read_batch_size=10,
        write_batch_size=10,
        sqlite_cache_mb=64,
    )

    rc = run_repartition(config)

    assert rc == 0
    state = load_state(config.state_file, RepartitionState)
    assert state.finished is True
    total_rows = 0
    for path in sorted((tmp_path / "out").glob("*.sqlite3")):
        conn = connect_sqlite(path, cache_mb=64)
        total_rows += len(fetch_sqlite_rows(conn, after_pair_id="", limit=10))
        conn.close()
    assert total_rows == 2
