"""External aggregation pipeline for pair-schema migration."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator
import hashlib

from .logging_config import configure_logging
from .models import address_bytes_to_hex
from .migrate_pair_schema import (
    DEFAULT_STATE_FILE,
    FETCH_NEXT_BLOCK_QUERY,
    LEGACY_BLOCK_INDEX_QUERY,
    parse_env_file,
    wait_for_index_online,
)
from .neo4j_store import RELATIONSHIP_CONSTRAINT_QUERY

LOGGER = logging.getLogger(__name__)

DEFAULT_SQLITE_PATH = Path("/mnt/nvme/javier/neo4j/pair-aggregation.sqlite3")

FETCH_LEGACY_ROWS_QUERY = """
UNWIND $block_numbers AS blockNumber
MATCH ()-[r:INTERACTION]->()
WHERE r.blockNumber = blockNumber
RETURN startNode(r).address AS source,
       endNode(r).address AS target,
       r.blockNumber AS blockNumber
""".strip()

CREATE_SQLITE_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS pair_ranges (
    pair_id TEXT PRIMARY KEY,
    source BLOB NOT NULL,
    target BLOB NOT NULL,
    first_block_number INTEGER NOT NULL,
    last_block_number INTEGER NOT NULL
)
""".strip()

UPSERT_SQLITE_PAIR_QUERY = """
INSERT INTO pair_ranges (
    pair_id,
    source,
    target,
    first_block_number,
    last_block_number
)
VALUES (?, ?, ?, ?, ?)
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

FETCH_SQLITE_ROWS_QUERY = """
SELECT pair_id, source, target, first_block_number, last_block_number
FROM pair_ranges
WHERE pair_id > ?
ORDER BY pair_id
LIMIT ?
""".strip()

COUNT_SQLITE_ROWS_QUERY = """
SELECT count(*) AS count FROM pair_ranges
""".strip()

UPSERT_NEO4J_QUERY = """
UNWIND $rows AS row
MATCH (source:Address {address: row.source})
MATCH (target:Address {address: row.target})
MERGE (source)-[rel:INTERACTION {pairId: row.pairId}]->(target)
ON CREATE SET rel.firstBlockNumber = row.firstBlockNumber,
              rel.lastBlockNumber = row.lastBlockNumber
ON MATCH SET rel.firstBlockNumber = CASE
                  WHEN rel.firstBlockNumber IS NULL
                       OR row.firstBlockNumber < rel.firstBlockNumber
                  THEN row.firstBlockNumber
                  ELSE rel.firstBlockNumber
              END,
              rel.lastBlockNumber = CASE
                  WHEN rel.lastBlockNumber IS NULL
                       OR row.lastBlockNumber > rel.lastBlockNumber
                  THEN row.lastBlockNumber
                  ELSE rel.lastBlockNumber
              END
""".strip()


@dataclass(frozen=True, slots=True)
class CommonConfig:
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    env_file: Path
    log_level: str
    json_logs: bool


@dataclass(frozen=True, slots=True)
class AggregateConfig(CommonConfig):
    sqlite_path: Path
    state_file: Path
    source_batch_size: int
    sqlite_batch_size: int
    start_block: int | None
    end_block: int | None
    loop: bool
    sleep_seconds: float
    index_poll_seconds: float
    sqlite_cache_mb: int


@dataclass(frozen=True, slots=True)
class LoadConfig(CommonConfig):
    sqlite_path: Path
    state_file: Path
    neo4j_batch_size: int


@dataclass(frozen=True, slots=True)
class RepartitionConfig(CommonConfig):
    source_glob: tuple[str, ...]
    output_dir: Path
    state_file: Path
    partitions: int
    read_batch_size: int
    write_batch_size: int
    sqlite_cache_mb: int


@dataclass(slots=True)
class AggregateState:
    last_legacy_block_number: int | None = None
    source_batches_completed: int = 0
    legacy_blocks_completed: int = 0
    legacy_rows_scanned: int = 0
    pair_rows_upserted: int = 0
    finished: bool = False


@dataclass(slots=True)
class LoadState:
    last_pair_id: str = ""
    sqlite_rows_loaded: int = 0
    finished: bool = False


@dataclass(slots=True)
class RepartitionState:
    source_index: int = 0
    last_pair_id: str = ""
    source_rows_read: int = 0
    rows_repartitioned: int = 0
    finished: bool = False


def load_common_values(env_file: Path) -> tuple[str, str, str]:
    values = dict(os.environ)
    if env_file.exists():
        values.update(parse_env_file(env_file))
    password = values.get("NEO4J_PASSWORD")
    if not password:
        raise ValueError(f"NEO4J_PASSWORD is required in {env_file}")
    return (
        values.get("NEO4J_URI", "bolt://localhost:7687"),
        values.get("NEO4J_USER", "neo4j"),
        password,
    )


def parse_args(
    argv: list[str] | None = None,
) -> AggregateConfig | LoadConfig | RepartitionConfig:
    parser = argparse.ArgumentParser(
        prog="eth-graph-indexer-external-pair-aggregation"
    )
    parser.add_argument(
        "--env-file",
        default="/mnt/nvme/javier/neo4j/eth-graph-indexer.env",
    )
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--json-logs", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)

    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("--sqlite-path", default=str(DEFAULT_SQLITE_PATH))
    aggregate.add_argument(
        "--state-file",
        default=str(DEFAULT_STATE_FILE.with_name("external-aggregate-state.json")),
    )
    aggregate.add_argument("--source-batch-size", type=int, default=512)
    aggregate.add_argument("--sqlite-batch-size", type=int, default=100000)
    aggregate.add_argument("--start-block", type=int)
    aggregate.add_argument("--end-block", type=int)
    aggregate.add_argument("--loop", action="store_true")
    aggregate.add_argument("--sleep-seconds", type=float, default=1.0)
    aggregate.add_argument("--index-poll-seconds", type=float, default=30.0)
    aggregate.add_argument("--sqlite-cache-mb", type=int, default=4096)

    load = subparsers.add_parser("load")
    load.add_argument("--sqlite-path", default=str(DEFAULT_SQLITE_PATH))
    load.add_argument(
        "--state-file",
        default=str(DEFAULT_STATE_FILE.with_name("external-load-state.json")),
    )
    load.add_argument("--neo4j-batch-size", type=int, default=5000)

    repartition = subparsers.add_parser("repartition")
    repartition.add_argument(
        "--source-glob",
        action="append",
        required=True,
        help="Glob pattern for source sqlite shards; can be passed multiple times.",
    )
    repartition.add_argument(
        "--output-dir",
        required=True,
    )
    repartition.add_argument(
        "--state-file",
        default=str(
            DEFAULT_STATE_FILE.with_name("external-repartition-state.json")
        ),
    )
    repartition.add_argument("--partitions", type=int, default=16)
    repartition.add_argument("--read-batch-size", type=int, default=50000)
    repartition.add_argument("--write-batch-size", type=int, default=100000)
    repartition.add_argument("--sqlite-cache-mb", type=int, default=2048)

    args = parser.parse_args(argv)
    env_file = Path(args.env_file)
    neo4j_uri, neo4j_user, neo4j_password = load_common_values(env_file)
    common = {
        "neo4j_uri": neo4j_uri,
        "neo4j_user": neo4j_user,
        "neo4j_password": neo4j_password,
        "env_file": env_file,
        "log_level": args.log_level,
        "json_logs": args.json_logs,
    }
    if args.command == "aggregate":
        return AggregateConfig(
            sqlite_path=Path(args.sqlite_path),
            state_file=Path(args.state_file),
            source_batch_size=args.source_batch_size,
            sqlite_batch_size=args.sqlite_batch_size,
            start_block=args.start_block,
            end_block=args.end_block,
            loop=args.loop,
            sleep_seconds=args.sleep_seconds,
            index_poll_seconds=args.index_poll_seconds,
            sqlite_cache_mb=args.sqlite_cache_mb,
            **common,
        )
    if args.command == "load":
        return LoadConfig(
            sqlite_path=Path(args.sqlite_path),
            state_file=Path(args.state_file),
            neo4j_batch_size=args.neo4j_batch_size,
            **common,
        )
    return RepartitionConfig(
        source_glob=tuple(args.source_glob),
        output_dir=Path(args.output_dir),
        state_file=Path(args.state_file),
        partitions=args.partitions,
        read_batch_size=args.read_batch_size,
        write_batch_size=args.write_batch_size,
        sqlite_cache_mb=args.sqlite_cache_mb,
        **common,
    )


def load_state(
    path: Path,
    cls: type[AggregateState] | type[LoadState] | type[RepartitionState],
) -> Any:
    if not path.exists():
        return cls()
    payload = json.loads(path.read_text(encoding="utf-8"))
    allowed = {field.name for field in cls.__dataclass_fields__.values()}
    normalized = {key: value for key, value in payload.items() if key in allowed}
    return cls(**normalized)


def save_state(
    path: Path, state: AggregateState | LoadState | RepartitionState
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(state), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def connect_sqlite(path: Path, *, cache_mb: int) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute(f"PRAGMA cache_size = {-cache_mb * 1024}")
    conn.execute("PRAGMA mmap_size = 268435456")
    conn.execute(CREATE_SQLITE_TABLE_QUERY)
    conn.commit()
    return conn


def ensure_new_constraint(driver: Any) -> None:
    constraints, _, _ = driver.execute_query(
        """
        SHOW CONSTRAINTS YIELD name
        WHERE name = 'interaction_pair_unique'
        RETURN name
        """
    )
    if constraints:
        return
    indexes, _, _ = driver.execute_query(
        """
        SHOW INDEXES YIELD name
        WHERE name = 'interaction_pair_unique'
        RETURN name
        """
    )
    if indexes:
        return
    driver.execute_query(RELATIONSHIP_CONSTRAINT_QUERY)


def ensure_legacy_scan_index(driver: Any) -> None:
    driver.execute_query(LEGACY_BLOCK_INDEX_QUERY)


def fetch_source_batch(
    driver: Any,
    *,
    after_block: int | None,
    start_block: int | None,
    end_block: int | None,
    limit: int,
) -> list[int]:
    block_numbers: list[int] = []
    next_min_block = 0 if after_block is None else after_block + 1
    if start_block is not None:
        next_min_block = max(next_min_block, start_block)
    with driver.session() as session:
        while len(block_numbers) < limit:
            if end_block is not None and next_min_block > end_block:
                break
            record = session.run(
                FETCH_NEXT_BLOCK_QUERY,
                min_block=next_min_block,
            ).single()
            if record is None:
                break
            block_number = int(record["blockNumber"])
            if end_block is not None and block_number > end_block:
                break
            block_numbers.append(block_number)
            next_min_block = block_number + 1
    return block_numbers


def iter_legacy_rows(driver: Any, block_numbers: list[int]) -> Iterator[dict[str, Any]]:
    with driver.session() as session:
        result = session.run(
            FETCH_LEGACY_ROWS_QUERY,
            block_numbers=block_numbers,
            fetch_size=2000,
        )
        for record in result:
            source = bytes(record["source"])
            target = bytes(record["target"])
            source_hex = address_bytes_to_hex(source)
            target_hex = address_bytes_to_hex(target)
            yield {
                "pairId": f"{source_hex}:{target_hex}",
                "source": source,
                "target": target,
                "blockNumber": int(record["blockNumber"]),
            }


def flush_pair_rows(
    conn: sqlite3.Connection,
    rows: list[tuple[str, bytes, bytes, int, int]],
) -> None:
    if not rows:
        return
    conn.executemany(UPSERT_SQLITE_PAIR_QUERY, rows)
    conn.commit()


def aggregate_once(
    driver: Any,
    conn: sqlite3.Connection,
    config: AggregateConfig,
    state: AggregateState,
) -> bool:
    block_numbers = fetch_source_batch(
        driver,
        after_block=state.last_legacy_block_number,
        start_block=config.start_block,
        end_block=config.end_block,
        limit=config.source_batch_size,
    )
    if not block_numbers:
        state.finished = True
        save_state(config.state_file, state)
        LOGGER.info("External aggregation scan completed")
        return False

    batch_rows: list[tuple[str, bytes, bytes, int, int]] = []
    scanned = 0
    upserted = 0
    for row in iter_legacy_rows(driver, block_numbers):
        scanned += 1
        block_number = row["blockNumber"]
        batch_rows.append(
            (
                row["pairId"],
                row["source"],
                row["target"],
                block_number,
                block_number,
            )
        )
        if len(batch_rows) >= config.sqlite_batch_size:
            flush_pair_rows(conn, batch_rows)
            upserted += len(batch_rows)
            batch_rows = []
    if batch_rows:
        flush_pair_rows(conn, batch_rows)
        upserted += len(batch_rows)

    state.last_legacy_block_number = block_numbers[-1]
    state.source_batches_completed += 1
    state.legacy_blocks_completed += len(block_numbers)
    state.legacy_rows_scanned += scanned
    state.pair_rows_upserted += upserted
    save_state(config.state_file, state)
    LOGGER.info(
        "Aggregated legacy batch externally",
        extra={
            "last_legacy_block_number": state.last_legacy_block_number,
            "source_batch_size": len(block_numbers),
            "legacy_rows_scanned": scanned,
            "pair_rows_upserted": upserted,
            "source_batches_completed": state.source_batches_completed,
            "legacy_blocks_completed": state.legacy_blocks_completed,
            "total_legacy_rows_scanned": state.legacy_rows_scanned,
            "total_pair_rows_upserted": state.pair_rows_upserted,
        },
    )
    return True


def fetch_sqlite_rows(
    conn: sqlite3.Connection, *, after_pair_id: str, limit: int
) -> list[dict[str, Any]]:
    cursor = conn.execute(FETCH_SQLITE_ROWS_QUERY, (after_pair_id, limit))
    rows = []
    for pair_id, source, target, first_block, last_block in cursor.fetchall():
        rows.append(
            {
                "pairId": pair_id,
                "source": source,
                "target": target,
                "firstBlockNumber": int(first_block),
                "lastBlockNumber": int(last_block),
            }
        )
    return rows


def iter_sqlite_rows(
    conn: sqlite3.Connection, *, after_pair_id: str, limit: int
) -> list[dict[str, Any]]:
    cursor = conn.execute(
        FETCH_SQLITE_ROWS_QUERY,
        (after_pair_id, limit),
    )
    rows = []
    for pair_id, source, target, first_block, last_block in cursor.fetchall():
        rows.append(
            {
                "pairId": pair_id,
                "source": source,
                "target": target,
                "firstBlockNumber": int(first_block),
                "lastBlockNumber": int(last_block),
            }
        )
    return rows


def resolve_source_paths(patterns: tuple[str, ...]) -> list[Path]:
    import glob

    paths: set[Path] = set()
    for pattern in patterns:
        for match in glob.glob(pattern):
            path = Path(match)
            if path.is_file():
                paths.add(path)
    return sorted(paths)


def partition_index(pair_id: str, partitions: int) -> int:
    digest = hashlib.blake2b(
        pair_id.encode("ascii"), digest_size=8
    ).digest()
    return int.from_bytes(digest, "big") % partitions


def partition_filename(index: int) -> str:
    return f"part-{index:02d}.sqlite3"


def open_partition_conns(
    output_dir: Path, *, partitions: int, cache_mb: int
) -> dict[int, sqlite3.Connection]:
    conns: dict[int, sqlite3.Connection] = {}
    for index in range(partitions):
        conns[index] = connect_sqlite(
            output_dir / partition_filename(index),
            cache_mb=cache_mb,
        )
    return conns


def flush_partition_buffers(
    conns: dict[int, sqlite3.Connection],
    buffers: dict[int, list[tuple[str, bytes, bytes, int, int]]],
) -> int:
    total = 0
    for index, rows in buffers.items():
        if not rows:
            continue
        flush_pair_rows(conns[index], rows)
        total += len(rows)
        rows.clear()
    return total


def upsert_neo4j_rows(driver: Any, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    def write(tx: Any) -> None:
        tx.run(UPSERT_NEO4J_QUERY, rows=rows).consume()

    with driver.session() as session:
        session.execute_write(write)


def load_once(
    driver: Any,
    conn: sqlite3.Connection,
    config: LoadConfig,
    state: LoadState,
) -> bool:
    rows = fetch_sqlite_rows(
        conn,
        after_pair_id=state.last_pair_id,
        limit=config.neo4j_batch_size,
    )
    if not rows:
        state.finished = True
        save_state(config.state_file, state)
        LOGGER.info("External pair load completed")
        return False

    upsert_neo4j_rows(driver, rows)
    state.last_pair_id = rows[-1]["pairId"]
    state.sqlite_rows_loaded += len(rows)
    save_state(config.state_file, state)
    LOGGER.info(
        "Loaded aggregated pair batch",
        extra={
            "last_pair_id": state.last_pair_id,
            "sqlite_rows_loaded": len(rows),
            "total_sqlite_rows_loaded": state.sqlite_rows_loaded,
        },
    )
    return True


def count_sqlite_pairs(conn: sqlite3.Connection) -> int:
    return int(conn.execute(COUNT_SQLITE_ROWS_QUERY).fetchone()[0])


def run_aggregate(config: AggregateConfig) -> int:
    try:
        from neo4j import GraphDatabase
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "neo4j package is required; install dependencies with "
            "`python -m pip install -e .`"
        ) from exc

    state = load_state(config.state_file, AggregateState)
    conn = connect_sqlite(config.sqlite_path, cache_mb=config.sqlite_cache_mb)
    driver = GraphDatabase.driver(
        config.neo4j_uri,
        auth=(config.neo4j_user, config.neo4j_password),
    )
    try:
        driver.verify_connectivity()
        ensure_legacy_scan_index(driver)
        wait_for_index_online(
            driver,
            name="interaction_legacy_block_idx",
            poll_seconds=config.index_poll_seconds,
        )
        LOGGER.info(
            "Starting external pair aggregation",
            extra={
                "sqlite_path": str(config.sqlite_path),
                "state_file": str(config.state_file),
                "start_block": config.start_block,
                "end_block": config.end_block,
                "source_batch_size": config.source_batch_size,
                "sqlite_batch_size": config.sqlite_batch_size,
                "loop": config.loop,
            },
        )
        did_work = False
        while True:
            batch_worked = aggregate_once(driver, conn, config, state)
            did_work = did_work or batch_worked
            if not config.loop or state.finished or not batch_worked:
                break
            time.sleep(config.sleep_seconds)
        LOGGER.info(
            "External aggregation snapshot",
            extra={"sqlite_pairs": count_sqlite_pairs(conn)},
        )
        return 0 if did_work or state.finished else 1
    finally:
        driver.close()
        conn.close()


def run_load(config: LoadConfig) -> int:
    try:
        from neo4j import GraphDatabase
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "neo4j package is required; install dependencies with "
            "`python -m pip install -e .`"
        ) from exc

    state = load_state(config.state_file, LoadState)
    conn = connect_sqlite(config.sqlite_path, cache_mb=1024)
    driver = GraphDatabase.driver(
        config.neo4j_uri,
        auth=(config.neo4j_user, config.neo4j_password),
    )
    try:
        driver.verify_connectivity()
        ensure_new_constraint(driver)
        LOGGER.info(
            "Starting aggregated pair load",
            extra={
                "sqlite_path": str(config.sqlite_path),
                "state_file": str(config.state_file),
                "neo4j_batch_size": config.neo4j_batch_size,
                "sqlite_pairs": count_sqlite_pairs(conn),
            },
        )
        did_work = False
        while True:
            batch_worked = load_once(driver, conn, config, state)
            did_work = did_work or batch_worked
            if state.finished or not batch_worked:
                break
        return 0 if did_work or state.finished else 1
    finally:
        driver.close()
        conn.close()


def run_repartition(config: RepartitionConfig) -> int:
    sources = resolve_source_paths(config.source_glob)
    if not sources:
        raise RuntimeError("No source sqlite files matched --source-glob")
    state = load_state(config.state_file, RepartitionState)
    conns = open_partition_conns(
        config.output_dir,
        partitions=config.partitions,
        cache_mb=config.sqlite_cache_mb,
    )
    try:
        LOGGER.info(
            "Starting sqlite repartition",
            extra={
                "sources": [str(path) for path in sources],
                "output_dir": str(config.output_dir),
                "partitions": config.partitions,
                "read_batch_size": config.read_batch_size,
                "write_batch_size": config.write_batch_size,
            },
        )
        buffers: dict[int, list[tuple[str, bytes, bytes, int, int]]] = {
            index: [] for index in range(config.partitions)
        }
        while state.source_index < len(sources):
            source_path = sources[state.source_index]
            source_conn = sqlite3.connect(source_path)
            try:
                while True:
                    rows = iter_sqlite_rows(
                        source_conn,
                        after_pair_id=state.last_pair_id,
                        limit=config.read_batch_size,
                    )
                    if not rows:
                        state.source_index += 1
                        state.last_pair_id = ""
                        save_state(config.state_file, state)
                        LOGGER.info(
                            "Repartitioned source sqlite",
                            extra={
                                "source_path": str(source_path),
                                "source_index": state.source_index,
                                "rows_repartitioned": state.rows_repartitioned,
                            },
                        )
                        break
                    for row in rows:
                        index = partition_index(
                            row["pairId"], config.partitions
                        )
                        buffers[index].append(
                            (
                                row["pairId"],
                                row["source"],
                                row["target"],
                                row["firstBlockNumber"],
                                row["lastBlockNumber"],
                            )
                        )
                    state.last_pair_id = rows[-1]["pairId"]
                    state.source_rows_read += len(rows)
                    if sum(len(buf) for buf in buffers.values()) >= config.write_batch_size:
                        state.rows_repartitioned += flush_partition_buffers(
                            conns, buffers
                        )
                    save_state(config.state_file, state)
            finally:
                source_conn.close()
        state.rows_repartitioned += flush_partition_buffers(conns, buffers)
        state.finished = True
        save_state(config.state_file, state)
        LOGGER.info(
            "Completed sqlite repartition",
            extra={
                "rows_repartitioned": state.rows_repartitioned,
                "sources_processed": state.source_index,
                "partitions": config.partitions,
            },
        )
        return 0
    finally:
        for conn in conns.values():
            conn.close()


def main(argv: list[str] | None = None) -> int:
    config = parse_args(argv)
    configure_logging(config.log_level, json_logs=config.json_logs)
    if isinstance(config, AggregateConfig):
        return run_aggregate(config)
    if isinstance(config, RepartitionConfig):
        return run_repartition(config)
    return run_load(config)


if __name__ == "__main__":
    raise SystemExit(main())
