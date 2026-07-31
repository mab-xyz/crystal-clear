"""Command-line entrypoint."""

from __future__ import annotations

import argparse
import logging
import os
import sys

from .config import (
    POST_MERGE_START_BLOCK,
    IndexerConfig,
    parse_bool,
    parse_endpoint_concurrency,
    parse_rpc_urls,
)
from .ingest import Ingestor
from .logging_config import configure_logging
from .rpc import JsonRpcClient, MultiJsonRpcClient, RpcClient

LOGGER = logging.getLogger(__name__)


def _boolean(value: str) -> bool:
    try:
        return parse_bool(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eth-graph-indexer")
    subparsers = parser.add_subparsers(dest="command", required=True)
    ingest = subparsers.add_parser(
        "ingest", help="Index an Ethereum block range"
    )
    ingest.add_argument(
        "--rpc-url",
        default=os.getenv(
            "ERIGON_RPC_URLS",
            os.getenv("ERIGON_RPC_URL", "http://localhost:8545"),
        ),
        help=(
            "Ethereum JSON-RPC URL. Use a comma-separated list to load-balance "
            "across multiple endpoints."
        ),
    )
    ingest.add_argument(
        "--postgres-dsn",
        default=os.getenv("INDEXER_DATABASE_URL", os.getenv("DATABASE_URL")),
        help=(
            "PostgreSQL connection string. Defaults to INDEXER_DATABASE_URL, "
            "then DATABASE_URL."
        ),
    )
    ingest.add_argument(
        "--start-block",
        type=int,
        default=POST_MERGE_START_BLOCK,
        help=(
            "First block to index when no checkpoint is used "
            f"(default: {POST_MERGE_START_BLOCK}, first post-Merge block)"
        ),
    )
    ingest.add_argument("--end-block", type=int)
    ingest.add_argument("--batch-size", type=int, default=1000)
    ingest.add_argument("--receipt-batch-size", type=int, default=100)
    ingest.add_argument("--commit-batch-size", type=int, default=10)
    ingest.add_argument("--concurrent-blocks", type=int, default=4)
    ingest.add_argument(
        "--endpoint-concurrency",
        default=os.getenv("ERIGON_ENDPOINT_CONCURRENCY"),
        help=(
            "Comma-separated worker counts aligned with the --rpc-url list, "
            "for example '12,20'. The values must sum to "
            "--concurrent-blocks."
        ),
    )
    ingest.add_argument(
        "--trace-mode",
        choices=["none", "trace_block", "debug_traceBlockByNumber"],
        default="trace_block",
    )
    ingest.add_argument("--resume", type=_boolean, default=True)
    ingest.add_argument(
        "--continue-on-error", type=_boolean, default=False
    )
    ingest.add_argument(
        "--continue-on-trace-error", type=_boolean, default=False
    )
    ingest.add_argument("--follow", type=_boolean, default=False)
    ingest.add_argument("--poll-interval", type=float, default=12.0)
    ingest.add_argument("--request-timeout", type=float, default=60.0)
    ingest.add_argument("--max-retries", type=int, default=4)
    ingest.add_argument("--retry-backoff", type=float, default=0.5)
    ingest.add_argument("--progress-interval", type=int, default=10)
    ingest.add_argument("--checkpoint-id", default="default")
    ingest.add_argument("--log-level", default="INFO")
    ingest.add_argument("--json-logs", type=_boolean, default=False)
    return parser


def build_rpc_client(
    rpc_url: str,
    *,
    timeout: float,
    max_retries: int,
    retry_backoff: float,
) -> RpcClient:
    clients = tuple(
        JsonRpcClient(
            url,
            timeout=timeout,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
        )
        for url in parse_rpc_urls(rpc_url)
    )
    if len(clients) == 1:
        return clients[0]
    return MultiJsonRpcClient(clients)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level, json_logs=args.json_logs)
    try:
        if not args.postgres_dsn:
            raise ValueError(
                "PostgreSQL DSN is required; pass --postgres-dsn or set "
                "INDEXER_DATABASE_URL"
            )
        config = IndexerConfig(
            rpc_url=args.rpc_url,
            endpoint_concurrency=parse_endpoint_concurrency(
                args.endpoint_concurrency
            ),
            postgres_dsn=args.postgres_dsn,
            start_block=args.start_block,
            end_block=args.end_block,
            batch_size=args.batch_size,
            receipt_batch_size=args.receipt_batch_size,
            commit_batch_size=args.commit_batch_size,
            concurrent_blocks=args.concurrent_blocks,
            trace_mode=args.trace_mode,
            resume=args.resume,
            continue_on_error=args.continue_on_error,
            continue_on_trace_error=args.continue_on_trace_error,
            follow=args.follow,
            poll_interval=args.poll_interval,
            request_timeout=args.request_timeout,
            max_retries=args.max_retries,
            retry_backoff=args.retry_backoff,
            progress_interval=args.progress_interval,
            checkpoint_id=args.checkpoint_id,
        )
        with build_rpc_client(
            config.rpc_url,
            timeout=config.request_timeout,
            max_retries=config.max_retries,
            retry_backoff=config.retry_backoff,
        ) as rpc:
            from .postgres_store import PostgresStore

            with PostgresStore(config.postgres_dsn) as store:
                Ingestor(config, rpc, store).run()
        return 0
    except (ValueError, RuntimeError) as exc:
        LOGGER.error("%s", exc)
        return 2
    except KeyboardInterrupt:
        LOGGER.warning("Interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
