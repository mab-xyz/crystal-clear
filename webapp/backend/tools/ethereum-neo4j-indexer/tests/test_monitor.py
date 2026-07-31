from datetime import UTC, datetime
from pathlib import Path

from eth_graph_indexer.monitor import (
    DiskSnapshot,
    Snapshot,
    calculate_blocks_per_second,
    format_bytes,
    format_number,
    format_rate,
    load_config,
    load_previous_sample,
    parse_env_file,
    render,
    save_sample,
    service_state_command,
)


def test_parse_env_file_strips_quotes_and_comments(tmp_path) -> None:
    path = tmp_path / "indexer.env"
    path.write_text(
        "\n".join(
            [
                "# comment",
                "INDEXER_DATABASE_URL='postgresql:///cc'",
                'POSTGRES_DATA_PATH="/var/lib/postgresql"',
                "ERIGON_RPC_URL=http://localhost:8545",
            ]
        ),
        encoding="utf-8",
    )

    values = parse_env_file(path)

    assert values["INDEXER_DATABASE_URL"] == "postgresql:///cc"
    assert values["POSTGRES_DATA_PATH"] == "/var/lib/postgresql"


def test_load_config_reads_env_file(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("INDEXER_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    path = tmp_path / "indexer.env"
    path.write_text(
        "INDEXER_DATABASE_URL=postgresql://indexer@db/cc\n"
        "POSTGRES_DATA_PATH=/postgres-data\n",
        encoding="utf-8",
    )

    config = load_config(
        path, checkpoint_id="default", service_name="indexer.service"
    )

    assert config.postgres_dsn == "postgresql://indexer@db/cc"
    assert config.postgres_data_path == Path("/postgres-data")
    assert config.user_service is False
    assert config.include_counts is False


def test_load_config_defaults_to_monitor_env_file(
    tmp_path, monkeypatch
) -> None:
    monitor_env = tmp_path / "monitor.env"
    monitor_env.write_text(
        "INDEXER_DATABASE_URL=postgresql:///monitor\n", encoding="utf-8"
    )
    monkeypatch.delenv("INDEXER_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(
        "eth_graph_indexer.monitor.DEFAULT_MONITOR_ENV_FILE",
        monitor_env,
    )
    monkeypatch.setattr(
        "eth_graph_indexer.monitor.DEFAULT_SERVICE_ENV_FILE",
        tmp_path / "service.env",
    )

    config = load_config(
        None, checkpoint_id="default", service_name="indexer.service"
    )

    assert config.postgres_dsn == "postgresql:///monitor"


def disk_snapshot() -> DiskSnapshot:
    return DiskSnapshot(
        data_path=Path("/var/lib/postgresql"),
        database_bytes=1024 * 1024 * 2,
        pair_table_bytes=1024,
        filesystem_total_bytes=100,
        filesystem_used_bytes=25,
        filesystem_free_bytes=75,
    )


def test_snapshot_lag_never_negative() -> None:
    snapshot = Snapshot(
        "active", 20, None, 10, 2, False, 20, disk_snapshot()
    )
    assert snapshot.lag == 0


def test_format_number() -> None:
    assert format_number(None) == "-"
    assert format_number(1234567) == "1,234,567"


def test_format_bytes() -> None:
    assert format_bytes(None) == "-"
    assert format_bytes(500) == "500 B"
    assert format_bytes(1536) == "1.5 KiB"


def test_format_rate() -> None:
    assert format_rate(None) == "-"
    assert format_rate(2.345) == "2.35 blocks/s"


def test_calculate_blocks_per_second() -> None:
    assert (
        calculate_blocks_per_second(
            (100, 10.0), checkpoint_block=130, timestamp=25.0
        )
        == 2
    )


def test_service_state_command_supports_user_services() -> None:
    assert service_state_command(
        "eth-graph-indexer.service",
        user_service=True,
    ) == [
        "systemctl",
        "--user",
        "is-active",
        "eth-graph-indexer.service",
    ]


def test_sample_state_round_trip(tmp_path) -> None:
    path = tmp_path / "state.json"
    save_sample(path, 123, 10.5)
    assert load_previous_sample(path) == (123, 10.5)


def test_render_includes_core_fields() -> None:
    snapshot = Snapshot(
        service_state="active",
        checkpoint_block=100,
        checkpoint_updated_at="2026-06-26T14:40:04Z",
        head_block=112,
        pair_count=30,
        pair_count_exact=False,
        max_pair_block=100,
        disk=disk_snapshot(),
        blocks_per_second=2.5,
    )

    output = render(
        snapshot,
        now=datetime(2026, 6, 26, 14, 40, 0, tzinfo=UTC),
    )

    assert "[OK] ACTIVE" in output
    assert "Checkpoint         100" in output
    assert "Lag                12 blocks" in output
    assert "Rate               2.50 blocks/s" in output
    assert "Directed pairs     30" in output
    assert "Count type         estimated" in output
    assert "Database           2.0 MiB" in output
