from pathlib import Path

from eth_graph_indexer.migrate_pair_schema import (
    MigrationConfig,
    MigrationState,
    load_state,
    migrate_once,
)


def test_load_state_ignores_unknown_keys(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        """
        {
          "last_legacy_block_number": 12,
          "source_batches_completed": 3,
          "unknown_field": "ignored"
        }
        """,
        encoding="utf-8",
    )

    state = load_state(path)

    assert state.last_legacy_block_number == 12
    assert state.source_batches_completed == 3


def test_migrate_once_updates_block_cursor_and_counters(
    tmp_path: Path, monkeypatch
) -> None:
    config = MigrationConfig(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="secret",
        source_batch_size=2,
        write_batch_size=10,
        delete_batch_size=100,
        state_file=tmp_path / "state.json",
        start_block=None,
        end_block=None,
        loop=False,
        sleep_seconds=0.0,
        finalize=False,
        dry_run=False,
        skip_delete=False,
        index_poll_seconds=0.0,
        log_level="INFO",
        json_logs=False,
    )
    state = MigrationState()

    monkeypatch.setattr(
        "eth_graph_indexer.migrate_pair_schema.fetch_source_batch",
        lambda _driver, *, after_block, start_block, end_block, limit: [100, 101],
    )
    monkeypatch.setattr(
        "eth_graph_indexer.migrate_pair_schema.iter_aggregated_rows",
        lambda _driver, block_numbers: iter(
            [
                {
                    "source": b"\x01" * 20,
                    "target": b"\x02" * 20,
                    "pairId": "0x01:0x02",
                    "firstBlockNumber": 100,
                    "lastBlockNumber": 101,
                }
            ]
        ),
    )

    writes: list[list[dict[str, object]]] = []

    def fake_upsert_rows(_driver, rows):
        writes.append(rows)

    monkeypatch.setattr(
        "eth_graph_indexer.migrate_pair_schema.upsert_rows",
        fake_upsert_rows,
    )
    monkeypatch.setattr(
        "eth_graph_indexer.migrate_pair_schema.delete_legacy_rows",
        lambda _driver, *, block_numbers, delete_batch_size: 7,
    )

    worked = migrate_once(object(), config, state)

    assert worked is True
    assert len(writes) == 1
    assert state.last_legacy_block_number == 101
    assert state.source_batches_completed == 1
    assert state.source_addresses_completed == 2
    assert state.legacy_blocks_completed == 2
    assert state.aggregated_rows_written == 1
    assert state.legacy_relationships_deleted == 7


def test_migrate_once_skips_delete_when_configured(
    tmp_path: Path, monkeypatch
) -> None:
    config = MigrationConfig(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="secret",
        source_batch_size=2,
        write_batch_size=10,
        delete_batch_size=100,
        state_file=tmp_path / "state.json",
        start_block=None,
        end_block=None,
        loop=False,
        sleep_seconds=0.0,
        finalize=False,
        dry_run=False,
        skip_delete=True,
        index_poll_seconds=0.0,
        log_level="INFO",
        json_logs=False,
    )
    state = MigrationState()

    monkeypatch.setattr(
        "eth_graph_indexer.migrate_pair_schema.fetch_source_batch",
        lambda _driver, *, after_block, start_block, end_block, limit: [100, 101],
    )
    monkeypatch.setattr(
        "eth_graph_indexer.migrate_pair_schema.iter_aggregated_rows",
        lambda _driver, block_numbers: iter(
            [
                {
                    "source": b"\x01" * 20,
                    "target": b"\x02" * 20,
                    "pairId": "0x01:0x02",
                    "firstBlockNumber": 100,
                    "lastBlockNumber": 101,
                }
            ]
        ),
    )
    monkeypatch.setattr(
        "eth_graph_indexer.migrate_pair_schema.upsert_rows",
        lambda _driver, rows: None,
    )

    def fail_delete(*_args, **_kwargs):
        raise AssertionError("delete should not run")

    monkeypatch.setattr(
        "eth_graph_indexer.migrate_pair_schema.delete_legacy_rows",
        fail_delete,
    )

    worked = migrate_once(object(), config, state)

    assert worked is True
    assert state.aggregated_rows_written == 1
    assert state.legacy_relationships_deleted == 0
