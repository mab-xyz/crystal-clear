"""Resumable migration from per-block interactions to per-pair ranges."""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .logging_config import configure_logging
from .models import address_bytes_to_hex
from .neo4j_store import RELATIONSHIP_CONSTRAINT_QUERY

LOGGER = logging.getLogger(__name__)

DEFAULT_STATE_FILE = Path("/mnt/nvme/javier/neo4j/migrate-pair-schema-state.json")

LEGACY_BLOCK_INDEX_QUERY = """
CREATE INDEX interaction_legacy_block_idx IF NOT EXISTS
FOR ()-[r:INTERACTION]-() ON (r.blockNumber)
""".strip()

FETCH_NEXT_BLOCK_QUERY = """
MATCH ()-[r:INTERACTION]->()
WHERE r.blockNumber >= $min_block
RETURN r.blockNumber AS blockNumber
ORDER BY blockNumber
LIMIT 1
""".strip()

AGGREGATE_QUERY = """
UNWIND $block_numbers AS blockNumber
MATCH ()-[r:INTERACTION]->()
WHERE r.blockNumber = blockNumber
WITH startNode(r).address AS source,
     endNode(r).address AS target,
     min(r.blockNumber) AS firstBlockNumber,
     max(r.blockNumber) AS lastBlockNumber
RETURN source, target, firstBlockNumber, lastBlockNumber
ORDER BY source, target
""".strip()

UPSERT_QUERY = """
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

DELETE_QUERY = """
UNWIND $block_numbers AS blockNumber
MATCH ()-[r:INTERACTION]->()
WHERE r.blockNumber = blockNumber
WITH r
LIMIT $limit
DELETE r
RETURN count(*) AS deleted
""".strip()

DROP_LEGACY_BLOCK_INDEX_QUERY = """
DROP INDEX interaction_legacy_block_idx IF EXISTS
""".strip()

DROP_LEGACY_CONSTRAINT_QUERY = """
DROP CONSTRAINT interaction_unique IF EXISTS
""".strip()

LEGACY_REMAINING_QUERY = """
MATCH ()-[r:INTERACTION]->()
WHERE r.blockNumber IS NOT NULL
RETURN count(r) AS remaining
""".strip()


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


@dataclass(frozen=True, slots=True)
class MigrationConfig:
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    source_batch_size: int
    write_batch_size: int
    delete_batch_size: int
    state_file: Path
    start_block: int | None
    end_block: int | None
    loop: bool
    sleep_seconds: float
    finalize: bool
    dry_run: bool
    skip_delete: bool
    index_poll_seconds: float
    log_level: str
    json_logs: bool


@dataclass(slots=True)
class MigrationState:
    last_source_hex: str | None = None
    last_legacy_block_number: int | None = None
    source_batches_completed: int = 0
    source_addresses_completed: int = 0
    legacy_blocks_completed: int = 0
    aggregated_rows_written: int = 0
    legacy_relationships_deleted: int = 0
    finished: bool = False


def load_config(argv: list[str] | None = None) -> MigrationConfig:
    parser = argparse.ArgumentParser(
        prog="eth-graph-indexer-migrate-pair-schema"
    )
    parser.add_argument(
        "--env-file",
        default="/mnt/nvme/javier/neo4j/eth-graph-indexer.env",
    )
    parser.add_argument(
        "--state-file",
        default=str(DEFAULT_STATE_FILE),
    )
    parser.add_argument("--source-batch-size", type=int, default=512)
    parser.add_argument("--write-batch-size", type=int, default=2000)
    parser.add_argument("--delete-batch-size", type=int, default=50000)
    parser.add_argument("--start-block", type=int)
    parser.add_argument("--end-block", type=int)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-delete", action="store_true")
    parser.add_argument("--index-poll-seconds", type=float, default=30.0)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--json-logs", action="store_true")
    args = parser.parse_args(argv)

    values = dict(os.environ)
    env_file = Path(args.env_file)
    if env_file.exists():
        values.update(parse_env_file(env_file))
    password = values.get("NEO4J_PASSWORD")
    if not password:
        raise ValueError(f"NEO4J_PASSWORD is required in {env_file}")
    return MigrationConfig(
        neo4j_uri=values.get("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=values.get("NEO4J_USER", "neo4j"),
        neo4j_password=password,
        source_batch_size=args.source_batch_size,
        write_batch_size=args.write_batch_size,
        delete_batch_size=args.delete_batch_size,
        state_file=Path(args.state_file),
        start_block=args.start_block,
        end_block=args.end_block,
        loop=args.loop,
        sleep_seconds=args.sleep_seconds,
        finalize=args.finalize,
        dry_run=args.dry_run,
        skip_delete=args.skip_delete,
        index_poll_seconds=args.index_poll_seconds,
        log_level=args.log_level,
        json_logs=args.json_logs,
    )


def load_state(path: Path) -> MigrationState:
    if not path.exists():
        return MigrationState()
    payload = json.loads(path.read_text(encoding="utf-8"))
    allowed = {field.name for field in MigrationState.__dataclass_fields__.values()}
    normalized = {key: value for key, value in payload.items() if key in allowed}
    return MigrationState(**normalized)


def save_state(path: Path, state: MigrationState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(state), indent=2, sort_keys=True),
        encoding="utf-8",
    )


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


def iter_aggregated_rows(driver: Any, block_numbers: list[int]):
    with driver.session() as session:
        result = session.run(
            AGGREGATE_QUERY,
            block_numbers=block_numbers,
            fetch_size=1000,
        )
        for record in result:
            source = bytes(record["source"])
            target = bytes(record["target"])
            source_hex = address_bytes_to_hex(source)
            target_hex = address_bytes_to_hex(target)
            yield {
                "source": source,
                "target": target,
                "pairId": f"{source_hex}:{target_hex}",
                "firstBlockNumber": int(record["firstBlockNumber"]),
                "lastBlockNumber": int(record["lastBlockNumber"]),
            }


def upsert_rows(driver: Any, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    def write(tx: Any) -> None:
        tx.run(UPSERT_QUERY, rows=rows).consume()

    with driver.session() as session:
        session.execute_write(write)


def delete_legacy_rows(
    driver: Any,
    *,
    block_numbers: list[int],
    delete_batch_size: int,
) -> int:
    total_deleted = 0
    with driver.session() as session:
        while True:
            record = session.run(
                DELETE_QUERY,
                block_numbers=block_numbers,
                limit=delete_batch_size,
            ).single()
            deleted = int(record["deleted"] or 0)
            total_deleted += deleted
            if deleted == 0:
                break
    return total_deleted


def count_remaining_legacy(driver: Any) -> int:
    with driver.session() as session:
        record = session.run(LEGACY_REMAINING_QUERY).single()
        return int(record["remaining"])


def drop_legacy_constraint(driver: Any) -> None:
    driver.execute_query(DROP_LEGACY_CONSTRAINT_QUERY)


def drop_legacy_block_index(driver: Any) -> None:
    driver.execute_query(DROP_LEGACY_BLOCK_INDEX_QUERY)


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


def wait_for_index_online(
    driver: Any, *, name: str, poll_seconds: float
) -> None:
    while True:
        records, _, _ = driver.execute_query(
            """
            SHOW INDEXES YIELD name, state, populationPercent
            WHERE name = $name
            RETURN name, state, populationPercent
            """,
            name=name,
        )
        if records and records[0]["state"] == "ONLINE":
            return
        state = records[0]["state"] if records else "MISSING"
        percent = records[0]["populationPercent"] if records else None
        LOGGER.info(
            "Waiting for index to come online",
            extra={
                "index_name": name,
                "state": state,
                "population_percent": percent,
                "poll_seconds": poll_seconds,
            },
        )
        time.sleep(poll_seconds)


def migrate_once(driver: Any, config: MigrationConfig, state: MigrationState) -> bool:
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
        LOGGER.info("Migration scan completed")
        return False

    rows: list[dict[str, Any]] = []
    written = 0
    for row in iter_aggregated_rows(driver, block_numbers):
        rows.append(row)
        if len(rows) >= config.write_batch_size:
            if not config.dry_run:
                upsert_rows(driver, rows)
            written += len(rows)
            rows = []
    if rows:
        if not config.dry_run:
            upsert_rows(driver, rows)
        written += len(rows)

    deleted = 0
    if not config.dry_run and not config.skip_delete:
        deleted = delete_legacy_rows(
            driver,
            block_numbers=block_numbers,
            delete_batch_size=config.delete_batch_size,
        )

    state.last_legacy_block_number = block_numbers[-1]
    state.source_batches_completed += 1
    state.source_addresses_completed += len(block_numbers)
    state.legacy_blocks_completed += len(block_numbers)
    state.aggregated_rows_written += written
    state.legacy_relationships_deleted += deleted
    save_state(config.state_file, state)
    LOGGER.info(
        "Migrated source batch",
        extra={
            "last_legacy_block_number": state.last_legacy_block_number,
            "source_batch_size": len(block_numbers),
            "aggregated_rows_written": written,
            "legacy_relationships_deleted": deleted,
            "source_batches_completed": state.source_batches_completed,
            "legacy_blocks_completed": state.legacy_blocks_completed,
            "source_addresses_completed": state.source_addresses_completed,
            "total_rows_written": state.aggregated_rows_written,
            "total_legacy_deleted": state.legacy_relationships_deleted,
            "dry_run": config.dry_run,
            "skip_delete": config.skip_delete,
        },
    )
    return True


def main(argv: list[str] | None = None) -> int:
    config = load_config(argv)
    configure_logging(config.log_level, json_logs=config.json_logs)
    state = load_state(config.state_file)
    try:
        from neo4j import GraphDatabase
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "neo4j package is required; install dependencies with "
            "`python -m pip install -e .`"
        ) from exc
    driver = GraphDatabase.driver(
        config.neo4j_uri,
        auth=(config.neo4j_user, config.neo4j_password),
    )
    try:
        driver.verify_connectivity()
        LOGGER.info(
            "Starting pair-schema migration",
            extra={
                "source_batch_size": config.source_batch_size,
                "write_batch_size": config.write_batch_size,
                "delete_batch_size": config.delete_batch_size,
                "state_file": str(config.state_file),
                "start_block": config.start_block,
                "end_block": config.end_block,
                "loop": config.loop,
                "dry_run": config.dry_run,
                "skip_delete": config.skip_delete,
            },
        )
        ensure_new_constraint(driver)
        ensure_legacy_scan_index(driver)
        wait_for_index_online(
            driver,
            name="interaction_legacy_block_idx",
            poll_seconds=config.index_poll_seconds,
        )
        did_work = False
        while True:
            batch_worked = migrate_once(driver, config, state)
            did_work = did_work or batch_worked
            if not config.loop or state.finished or not batch_worked:
                break
            time.sleep(config.sleep_seconds)
        if state.finished and config.finalize and not config.dry_run:
            if config.skip_delete:
                LOGGER.warning(
                    "Skip-delete mode left legacy rows in place; not finalizing"
                )
                return 0 if did_work or state.finished else 1
            remaining = count_remaining_legacy(driver)
            if remaining == 0:
                drop_legacy_constraint(driver)
                drop_legacy_block_index(driver)
                LOGGER.info("Dropped legacy interaction id constraint")
            else:
                LOGGER.warning(
                    "Legacy rows remain; not dropping old constraint",
                    extra={"remaining_legacy_relationships": remaining},
                )
        return 0 if did_work or state.finished else 1
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
