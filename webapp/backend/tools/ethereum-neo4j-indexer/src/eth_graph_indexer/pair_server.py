from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sqlite3
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

LOGGER = logging.getLogger(__name__)
MAX_BATCH_SIZE = 10_000
MAX_REQUEST_BYTES = 2_000_000
SQLITE_QUERY_CHUNK_SIZE = 500
DEFAULT_SHARD_DIR = Path(
    "/mnt/nvme/javier/neo4j/repartitioned-pair-shards"
)


def normalize_address(value: str) -> str:
    address = value.strip().lower()
    if address.startswith("0x"):
        address = address[2:]
    if len(address) != 40:
        raise ValueError("address must contain exactly 40 hexadecimal digits")
    try:
        bytes.fromhex(address)
    except ValueError as exc:
        raise ValueError("address must be hexadecimal") from exc
    return f"0x{address}"


def make_pair_id(source: str, target: str) -> str:
    return f"{normalize_address(source)}:{normalize_address(target)}"


def partition_index(pair_id: str, partitions: int) -> int:
    digest = hashlib.blake2b(
        pair_id.encode("ascii"), digest_size=8
    ).digest()
    return int.from_bytes(digest, "big") % partitions


@dataclass(frozen=True, slots=True)
class PairResult:
    pair_id: str
    partition: int
    first_block_number: int | None
    last_block_number: int | None

    def seen_at_or_before(self, block_number: int) -> bool:
        return (
            self.first_block_number is not None
            and self.first_block_number <= block_number
        )


class PairShardStore:
    def __init__(self, shard_dir: Path, partitions: int = 16) -> None:
        if partitions < 1:
            raise ValueError("partitions must be positive")
        self.shard_dir = shard_dir.resolve()
        self.partitions = partitions
        self.shard_paths = tuple(
            self.shard_dir / f"part-{index:02d}.sqlite3"
            for index in range(partitions)
        )
        missing = [str(path) for path in self.shard_paths if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"missing SQLite shards: {', '.join(missing)}")

    def lookup(self, source: str, target: str) -> PairResult:
        return self.lookup_many([(source, target)])[0]

    def lookup_many(self, pairs: list[tuple[str, str]]) -> list[PairResult]:
        pair_ids = [make_pair_id(source, target) for source, target in pairs]
        by_partition: dict[int, list[str]] = {}
        for pair_id in dict.fromkeys(pair_ids):
            partition = partition_index(pair_id, self.partitions)
            by_partition.setdefault(partition, []).append(pair_id)

        found: dict[str, tuple[int, int]] = {}
        for partition, partition_pair_ids in by_partition.items():
            path = self.shard_paths[partition]
            uri = f"file:{path}?mode=ro"
            with sqlite3.connect(uri, uri=True, timeout=5) as conn:
                conn.execute("PRAGMA query_only = ON")
                for offset in range(
                    0, len(partition_pair_ids), SQLITE_QUERY_CHUNK_SIZE
                ):
                    chunk = partition_pair_ids[
                        offset : offset + SQLITE_QUERY_CHUNK_SIZE
                    ]
                    placeholders = ",".join("?" for _ in chunk)
                    rows = conn.execute(
                        f"""
                        SELECT pair_id, first_block_number, last_block_number
                        FROM pair_ranges
                        WHERE pair_id IN ({placeholders})
                        """,
                        chunk,
                    )
                    found.update(
                        (str(row[0]), (int(row[1]), int(row[2])))
                        for row in rows
                    )

        results = []
        for pair_id in pair_ids:
            partition = partition_index(pair_id, self.partitions)
            block_range = found.get(pair_id)
            results.append(
                PairResult(
                    pair_id=pair_id,
                    partition=partition,
                    first_block_number=(
                        None if block_range is None else block_range[0]
                    ),
                    last_block_number=(
                        None if block_range is None else block_range[1]
                    ),
                )
            )
        return results


def result_payload(result: PairResult, block_number: int) -> dict[str, Any]:
    source, target = result.pair_id.split(":", 1)
    return {
        "source": source,
        "target": target,
        "pairId": result.pair_id,
        "block": block_number,
        "seenAtOrBeforeBlock": result.seen_at_or_before(block_number),
        "firstBlockNumber": result.first_block_number,
        "lastBlockNumber": result.last_block_number,
    }


class PairRequestHandler(BaseHTTPRequestHandler):
    server_version = "EthGraphPairServer/1"

    @property
    def store(self) -> PairShardStore:
        return self.server.store  # type: ignore[attr-defined, no-any-return]

    def send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        if urlsplit(self.path).path not in {
            "/v1/pair-seen",
            "/v1/pair-seen/batch",
        }:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        request = urlsplit(self.path)
        if request.path == "/health":
            self.send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "partitions": self.store.partitions,
                    "shardDirectory": str(self.store.shard_dir),
                },
            )
            return
        if request.path != "/v1/pair-seen":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        query = parse_qs(request.query, keep_blank_values=True)
        try:
            source = query["source"][0]
            target = query["target"][0]
            block_number = int(query["block"][0])
            if block_number < 0:
                raise ValueError("block must be non-negative")
            result = self.store.lookup(source, target)
        except (KeyError, IndexError):
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "source, target, and block are required"},
            )
            return
        except ValueError as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except sqlite3.Error:
            LOGGER.exception("SQLite pair lookup failed")
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "pair lookup failed"},
            )
            return

        self.send_json(
            HTTPStatus.OK,
            result_payload(result, block_number),
        )

    def do_POST(self) -> None:  # noqa: N802
        if urlsplit(self.path).path != "/v1/pair-seen/batch":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        if content_length < 1:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "JSON body required"})
            return
        if content_length > MAX_REQUEST_BYTES:
            self.send_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": f"request body exceeds {MAX_REQUEST_BYTES} bytes"},
            )
            return

        try:
            payload = json.loads(self.rfile.read(content_length))
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")
            block_number = payload.get("block")
            if (
                not isinstance(block_number, int)
                or isinstance(block_number, bool)
                or block_number < 0
            ):
                raise ValueError("block must be a non-negative integer")
            raw_pairs = payload.get("pairs")
            if not isinstance(raw_pairs, list) or not raw_pairs:
                raise ValueError("pairs must be a non-empty array")
            if len(raw_pairs) > MAX_BATCH_SIZE:
                raise ValueError(
                    f"batch exceeds the maximum of {MAX_BATCH_SIZE} pairs"
                )

            pairs: list[tuple[str, str]] = []
            for index, pair in enumerate(raw_pairs):
                if not isinstance(pair, dict):
                    raise ValueError(f"pairs[{index}] must be an object")
                source = pair.get("source")
                target = pair.get("target")
                if not isinstance(source, str) or not isinstance(target, str):
                    raise ValueError(
                        f"pairs[{index}] source and target must be strings"
                    )
                pairs.append((source, target))
            results = self.store.lookup_many(pairs)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON body"})
            return
        except ValueError as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except sqlite3.Error:
            LOGGER.exception("SQLite batch pair lookup failed")
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "pair lookup failed"},
            )
            return

        self.send_json(
            HTTPStatus.OK,
            {
                "block": block_number,
                "count": len(results),
                "results": [
                    result_payload(result, block_number) for result in results
                ],
            },
        )

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.client_address[0], format % args)


class PairHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        store: PairShardStore,
    ) -> None:
        self.store = store
        super().__init__(server_address, PairRequestHandler)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve read-only pair/block lookups from SQLite shards"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--shard-dir", type=Path, default=DEFAULT_SHARD_DIR)
    parser.add_argument("--partitions", type=int, default=16)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    store = PairShardStore(args.shard_dir, args.partitions)
    server = PairHTTPServer((args.host, args.port), store)
    LOGGER.info(
        "Serving pair lookups on http://%s:%d from %s",
        args.host,
        args.port,
        store.shard_dir,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
