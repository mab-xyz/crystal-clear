"""Terminal monitor for the Ethereum PostgreSQL interaction-pair indexer."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
import psycopg

DEFAULT_MONITOR_ENV_FILE = Path("/etc/eth-graph-indexer-monitor.env")
DEFAULT_SERVICE_ENV_FILE = Path("/etc/eth-graph-indexer.env")
DEFAULT_SERVICE = "eth-graph-indexer.service"
DEFAULT_POSTGRES_DATA_PATH = Path("/var/lib/postgresql")
DEFAULT_STATE_FILE = Path("~/.cache/eth-graph-indexer-monitor/state.json")


@dataclass(frozen=True, slots=True)
class MonitorConfig:
    postgres_dsn: str
    rpc_url: str | None
    checkpoint_id: str
    service_name: str
    user_service: bool
    postgres_data_path: Path
    state_file: Path
    include_counts: bool = False


@dataclass(frozen=True, slots=True)
class DiskSnapshot:
    data_path: Path
    database_bytes: int | None
    pair_table_bytes: int | None
    filesystem_total_bytes: int | None
    filesystem_used_bytes: int | None
    filesystem_free_bytes: int | None
    error: str | None = None

    @property
    def filesystem_used_ratio(self) -> float | None:
        if not self.filesystem_total_bytes:
            return None
        return self.filesystem_used_bytes / self.filesystem_total_bytes


@dataclass(frozen=True, slots=True)
class Snapshot:
    service_state: str
    checkpoint_block: int | None
    checkpoint_updated_at: str | None
    head_block: int | None
    pair_count: int | None
    pair_count_exact: bool
    max_pair_block: int | None
    disk: DiskSnapshot
    blocks_per_second: float | None = None
    error: str | None = None

    @property
    def lag(self) -> int | None:
        if self.head_block is None or self.checkpoint_block is None:
            return None
        return max(self.head_block - self.checkpoint_block, 0)


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def load_config(
    env_file: Path | None,
    *,
    checkpoint_id: str,
    service_name: str,
    user_service: bool = False,
    postgres_data_path: Path | None = None,
    state_file: Path | None = None,
    include_counts: bool = False,
) -> MonitorConfig:
    values = dict(os.environ)
    if env_file is None:
        env_file = (
            DEFAULT_MONITOR_ENV_FILE
            if DEFAULT_MONITOR_ENV_FILE.exists()
            else DEFAULT_SERVICE_ENV_FILE
        )
    if env_file.exists():
        values.update(parse_env_file(env_file))
    postgres_dsn = values.get("INDEXER_DATABASE_URL") or values.get(
        "DATABASE_URL"
    )
    if not postgres_dsn:
        raise ValueError(
            "INDEXER_DATABASE_URL or DATABASE_URL is required in "
            f"environment or {env_file}"
        )
    return MonitorConfig(
        postgres_dsn=postgres_dsn,
        rpc_url=values.get("ERIGON_RPC_URL"),
        checkpoint_id=checkpoint_id,
        service_name=service_name,
        user_service=user_service,
        postgres_data_path=postgres_data_path
        or Path(
            values.get("POSTGRES_DATA_PATH", DEFAULT_POSTGRES_DATA_PATH)
        ),
        state_file=(state_file or DEFAULT_STATE_FILE).expanduser(),
        include_counts=include_counts,
    )


def service_state_command(service_name: str, *, user_service: bool) -> list[str]:
    command = ["systemctl"]
    if user_service:
        command.append("--user")
    command.extend(["is-active", service_name])
    return command


def get_service_state(service_name: str, *, user_service: bool = False) -> str:
    try:
        result = subprocess.run(
            service_state_command(service_name, user_service=user_service),
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception as exc:
        return f"unknown ({exc})"
    state = result.stdout.strip() or result.stderr.strip()
    return state or f"unknown ({result.returncode})"


def get_head_block(rpc_url: str | None) -> int | None:
    if not rpc_url:
        return None
    response = httpx.post(
        rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber"},
        timeout=5,
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result")
    return int(result, 16) if isinstance(result, str) else None


def get_disk_snapshot(
    data_path: Path,
    *,
    database_bytes: int | None = None,
    pair_table_bytes: int | None = None,
) -> DiskSnapshot:
    try:
        usage = shutil.disk_usage(data_path)
        return DiskSnapshot(
            data_path=data_path,
            database_bytes=database_bytes,
            pair_table_bytes=pair_table_bytes,
            filesystem_total_bytes=usage.total,
            filesystem_used_bytes=usage.used,
            filesystem_free_bytes=usage.free,
        )
    except OSError as exc:
        return DiskSnapshot(
            data_path=data_path,
            database_bytes=database_bytes,
            pair_table_bytes=pair_table_bytes,
            filesystem_total_bytes=None,
            filesystem_used_bytes=None,
            filesystem_free_bytes=None,
            error=str(exc),
        )


def load_previous_sample(path: Path) -> tuple[int, float] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        block = payload.get("checkpoint_block")
        timestamp = payload.get("timestamp")
        if isinstance(block, int) and isinstance(timestamp, int | float):
            return block, float(timestamp)
    except (OSError, json.JSONDecodeError):
        return None
    return None


def save_sample(path: Path, checkpoint_block: int | None, timestamp: float) -> None:
    if checkpoint_block is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "checkpoint_block": checkpoint_block,
                    "timestamp": timestamp,
                }
            ),
            encoding="utf-8",
        )
    except OSError:
        return


def calculate_blocks_per_second(
    previous: tuple[int, float] | None,
    *,
    checkpoint_block: int | None,
    timestamp: float,
) -> float | None:
    if previous is None or checkpoint_block is None:
        return None
    previous_block, previous_timestamp = previous
    elapsed = timestamp - previous_timestamp
    if elapsed <= 0:
        return None
    return max(checkpoint_block - previous_block, 0) / elapsed


def collect_snapshot(config: MonitorConfig) -> Snapshot:
    timestamp = time.time()
    previous = load_previous_sample(config.state_file)
    service_state = get_service_state(
        config.service_name,
        user_service=config.user_service,
    )
    disk = get_disk_snapshot(config.postgres_data_path)
    head_block: int | None = None
    error: str | None = None
    try:
        head_block = get_head_block(config.rpc_url)
    except Exception as exc:
        error = f"RPC head check failed: {exc}"

    try:
        with psycopg.connect(config.postgres_dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT last_processed_block, updated_at
                    FROM public.indexer_checkpoints
                    WHERE id = %s
                    """,
                    (config.checkpoint_id,),
                )
                checkpoint = cursor.fetchone()
                cursor.execute(
                    """
                    SELECT
                        pg_database_size(current_database()),
                        COALESCE(sum(pg_total_relation_size(tree.relid)), 0),
                        COALESCE(sum(classes.reltuples), 0)::bigint
                    FROM pg_partition_tree(
                        'public.pair_ranges'::regclass
                    ) AS tree
                    JOIN pg_class AS classes ON classes.oid = tree.relid
                    WHERE tree.isleaf
                    """
                )
                storage = cursor.fetchone()
                if config.include_counts:
                    cursor.execute(
                        "SELECT count(*) FROM public.pair_ranges"
                    )
                    count_record = cursor.fetchone()
                else:
                    count_record = None
    except Exception as exc:
        return Snapshot(
            service_state=service_state,
            checkpoint_block=None,
            checkpoint_updated_at=None,
            head_block=head_block,
            pair_count=None,
            pair_count_exact=False,
            max_pair_block=None,
            disk=disk,
            blocks_per_second=None,
            error=f"PostgreSQL check failed: {exc}",
        )

    checkpoint_block = int(checkpoint[0]) if checkpoint else None
    checkpoint_updated_at = (
        checkpoint[1].isoformat() if checkpoint and checkpoint[1] else None
    )
    database_bytes = int(storage[0]) if storage else None
    pair_table_bytes = int(storage[1]) if storage else None
    estimated_pair_count = int(storage[2]) if storage else None
    pair_count = (
        int(count_record[0]) if count_record else estimated_pair_count
    )
    disk = get_disk_snapshot(
        config.postgres_data_path,
        database_bytes=database_bytes,
        pair_table_bytes=pair_table_bytes,
    )
    blocks_per_second = calculate_blocks_per_second(
        previous,
        checkpoint_block=checkpoint_block,
        timestamp=timestamp,
    )
    save_sample(config.state_file, checkpoint_block, timestamp)
    return Snapshot(
        service_state=service_state,
        checkpoint_block=checkpoint_block,
        checkpoint_updated_at=checkpoint_updated_at,
        head_block=head_block,
        pair_count=pair_count,
        pair_count_exact=count_record is not None,
        max_pair_block=checkpoint_block,
        disk=disk,
        blocks_per_second=blocks_per_second,
        error=error,
    )


def format_number(value: int | None) -> str:
    return "-" if value is None else f"{value:,}"


def format_bytes(value: int | None) -> str:
    if value is None:
        return "-"
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.1f} {unit}"
        amount /= 1024


def format_ratio(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:.1f}%"


def format_rate(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f} blocks/s"


def status_badge(service_state: str, error: str | None) -> str:
    if error:
        return "[WARN]"
    if service_state == "active":
        return "[OK]"
    return "[DOWN]"


def progress_bar(value: float | None, width: int = 24) -> str:
    if value is None:
        return "[" + "?" * width + "]"
    bounded = min(max(value, 0), 1)
    filled = round(bounded * width)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def box(title: str, rows: list[str], width: int) -> list[str]:
    inner = max(width - 4, 40)
    title_text = f" {title} "
    top = "+" + title_text.ljust(inner, "-") + "+"
    bottom = "+" + "-" * inner + "+"
    body = [f"| {row.ljust(inner - 2)} |" for row in rows]
    return [top, *body, bottom]


def field(label: str, value: str) -> str:
    return f"{label:<18} {value}"


def render(snapshot: Snapshot, *, now: datetime | None = None) -> str:
    timestamp = (now or datetime.now(UTC)).astimezone().isoformat(
        timespec="seconds"
    )
    columns = max(shutil.get_terminal_size((100, 28)).columns, 80)
    width = min(columns, 110)
    badge = status_badge(snapshot.service_state, snapshot.error)
    lag = format_number(snapshot.lag)
    disk = snapshot.disk
    rows = [
        "=" * width,
        "Ethereum PostgreSQL Pair Indexer".center(width),
        "=" * width,
        f"{badge} {snapshot.service_state.upper()}   {timestamp}",
    ]
    rows.extend(
        box(
            "Progress",
            [
                field("Checkpoint", format_number(snapshot.checkpoint_block)),
                field("Chain head", format_number(snapshot.head_block)),
                field("Lag", f"{lag} blocks"),
                field("Rate", format_rate(snapshot.blocks_per_second)),
                field("Updated", snapshot.checkpoint_updated_at or "-"),
                field(
                    "Max indexed block",
                    format_number(snapshot.max_pair_block),
                ),
            ],
            width,
        )
    )
    rows.extend(
        box(
            "Pair ranges",
            [
                field(
                    "Directed pairs",
                    format_number(snapshot.pair_count),
                ),
                field(
                    "Count type",
                    "exact" if snapshot.pair_count_exact else "estimated",
                ),
            ],
            width,
        )
    )
    disk_rows = [
        field("PostgreSQL path", str(disk.data_path)),
        field("Database", format_bytes(disk.database_bytes)),
        field("Pair partitions", format_bytes(disk.pair_table_bytes)),
        field(
            "Filesystem",
            (
                f"{format_bytes(disk.filesystem_used_bytes)} / "
                f"{format_bytes(disk.filesystem_total_bytes)} "
                f"({format_ratio(disk.filesystem_used_ratio)})"
            ),
        ),
        field(
            "Free",
            f"{format_bytes(disk.filesystem_free_bytes)} "
            f"{progress_bar(disk.filesystem_used_ratio)}",
        ),
    ]
    if disk.error:
        disk_rows.append(field("Disk error", disk.error))
    rows.extend(box("Storage", disk_rows, width))
    if snapshot.error:
        rows.extend(box("Warnings", [snapshot.error], width))
    rows.append("Press Ctrl-C to exit.".center(width))
    return "\n".join(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eth-graph-indexer-monitor")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--checkpoint-id", default="default")
    parser.add_argument("--service-name", default=DEFAULT_SERVICE)
    parser.add_argument(
        "--user-service",
        action="store_true",
        help="Check the indexer with systemctl --user instead of systemctl.",
    )
    parser.add_argument("--postgres-data-path", type=Path)
    parser.add_argument("--state-file", type=Path)
    parser.add_argument(
        "--counts",
        action="store_true",
        help="Count pair rows exactly; can be very slow on large databases.",
    )
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--once", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.interval <= 0:
        print("interval must be positive", file=sys.stderr)
        return 2
    try:
        config = load_config(
            args.env_file,
            checkpoint_id=args.checkpoint_id,
            service_name=args.service_name,
            user_service=args.user_service,
            postgres_data_path=args.postgres_data_path,
            state_file=args.state_file,
            include_counts=args.counts,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        while True:
            snapshot = collect_snapshot(config)
            output = render(snapshot)
            if args.once:
                print(output)
                return 0 if snapshot.error is None else 1
            print("\033[2J\033[H" + output, end="", flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
