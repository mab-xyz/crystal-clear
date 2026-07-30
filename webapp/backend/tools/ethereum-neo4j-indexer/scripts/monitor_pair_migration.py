#!/usr/bin/env python3
"""Hourly monitor for the pair-schema migration."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from neo4j import GraphDatabase

DEFAULT_URI = "bolt://localhost:7687"
DEFAULT_USER = "neo4j"
DEFAULT_PASSWORD = "otbw919EJHu7EgTZlXrt6X0UiM1dIMZs"
DEFAULT_SERVICE = "eth-graph-migrate-pair-schema.service"
DEFAULT_STATE_FILE = Path("/mnt/nvme/javier/neo4j/migrate-pair-schema-state.json")

INDEX_QUERY = (
    "SHOW INDEXES YIELD name, state, populationPercent "
    "RETURN name, state, populationPercent"
)

TRANSACTION_QUERY = """
SHOW TRANSACTIONS
YIELD transactionId, currentQuery, elapsedTime, status
RETURN transactionId, currentQuery, elapsedTime, status
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval-seconds", type=int, default=3600)
    parser.add_argument("--iterations", type=int, default=0)
    parser.add_argument("--service", default=DEFAULT_SERVICE)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--neo4j-uri", default=DEFAULT_URI)
    parser.add_argument("--neo4j-user", default=DEFAULT_USER)
    parser.add_argument("--neo4j-password", default=DEFAULT_PASSWORD)
    return parser.parse_args()


def get_service_summary(service: str) -> dict[str, str]:
    cmd = [
        "systemctl",
        "--user",
        "show",
        service,
        "-p",
        "ActiveState",
        "-p",
        "SubState",
        "-p",
        "ExecMainPID",
        "-p",
        "MemoryCurrent",
        "-p",
        "CPUUsageNSec",
        "-p",
        "ActiveEnterTimestamp",
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, check=False, timeout=5
    )
    summary: dict[str, str] = {
        "systemctl_returncode": str(result.returncode),
    }
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        summary[key] = value
    if result.stderr.strip():
        summary["stderr"] = result.stderr.strip()
    return summary


def load_state(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - best effort monitor
        return {"error": str(exc)}


def get_neo4j_summary(uri: str, user: str, password: str) -> dict[str, object]:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver:
        indexes, _, _ = driver.execute_query(INDEX_QUERY)
        index_row = next(
            (
                dict(row)
                for row in indexes
                if row["name"] == "interaction_pair_unique"
            ),
            None,
        )
        transactions, _, _ = driver.execute_query(TRANSACTION_QUERY)
        migration_tx = None
        for row in transactions:
            query = (row.get("currentQuery") or "").strip()
            if "r.blockNumber" in query and "$after_block" in query:
                migration_tx = {
                    "transactionId": row.get("transactionId"),
                    "elapsedTime": str(row.get("elapsedTime")),
                    "status": row.get("status"),
                }
                break
    return {
        "interaction_pair_unique": index_row,
        "migration_transaction": migration_tx,
    }


def emit_snapshot(args: argparse.Namespace) -> None:
    snapshot = {
        "timestamp": datetime.now(UTC).isoformat(),
        "service": get_service_summary(args.service),
        "state_file": load_state(args.state_file),
        "neo4j": get_neo4j_summary(
            args.neo4j_uri, args.neo4j_user, args.neo4j_password
        ),
    }
    print(json.dumps(snapshot, sort_keys=True), flush=True)


def main() -> int:
    args = parse_args()
    remaining = args.iterations
    while True:
        emit_snapshot(args)
        if remaining == 1:
            return 0
        if remaining > 1:
            remaining -= 1
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    sys.exit(main())
