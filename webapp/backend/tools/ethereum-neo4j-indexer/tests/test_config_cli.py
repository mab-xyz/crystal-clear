import pytest

from eth_graph_indexer.cli import build_parser, build_rpc_client
from eth_graph_indexer.config import (
    POST_MERGE_START_BLOCK,
    IndexerConfig,
    parse_endpoint_concurrency,
    parse_rpc_urls,
)
from eth_graph_indexer.rpc import MultiJsonRpcClient


def test_config_defaults_to_first_post_merge_block() -> None:
    config = IndexerConfig(
        rpc_url="http://localhost:8545",
        postgres_dsn="postgresql://localhost/cc",
    )
    assert config.start_block == POST_MERGE_START_BLOCK


def test_ingest_parser_defaults_to_first_post_merge_block() -> None:
    args = build_parser().parse_args(["ingest"])
    assert args.start_block == POST_MERGE_START_BLOCK


def test_ingest_parser_accepts_follow_mode() -> None:
    args = build_parser().parse_args(
        ["ingest", "--follow", "true", "--poll-interval", "6"]
    )
    assert args.follow is True
    assert args.poll_interval == 6


def test_ingest_parser_accepts_postgres_dsn() -> None:
    args = build_parser().parse_args(
        [
            "ingest",
            "--postgres-dsn",
            "postgresql://indexer@localhost/cc",
        ]
    )
    assert args.postgres_dsn == "postgresql://indexer@localhost/cc"


def test_ingest_parser_defaults_to_four_concurrent_blocks() -> None:
    args = build_parser().parse_args(["ingest"])
    assert args.concurrent_blocks == 4


def test_parse_rpc_urls_accepts_comma_separated_values() -> None:
    assert parse_rpc_urls("http://a:8545, http://b:8545") == (
        "http://a:8545",
        "http://b:8545",
    )


def test_parser_accepts_multiple_rpc_urls() -> None:
    args = build_parser().parse_args(
        ["ingest", "--rpc-url", "http://a:8545,http://b:8545"]
    )
    assert parse_rpc_urls(args.rpc_url) == (
        "http://a:8545",
        "http://b:8545",
    )


def test_parse_endpoint_concurrency_accepts_comma_separated_values() -> None:
    assert parse_endpoint_concurrency("12, 20") == (12, 20)


def test_parser_accepts_endpoint_concurrency() -> None:
    args = build_parser().parse_args(
        ["ingest", "--endpoint-concurrency", "12,20"]
    )
    assert args.endpoint_concurrency == "12,20"


def test_build_rpc_client_uses_multi_client_for_multiple_urls() -> None:
    client = build_rpc_client(
        "http://a:8545,http://b:8545",
        timeout=1,
        max_retries=0,
        retry_backoff=0,
    )
    try:
        assert isinstance(client, MultiJsonRpcClient)
        assert [item.url for item in client.clients] == [
            "http://a:8545",
            "http://b:8545",
        ]
    finally:
        client.close()


def test_config_rejects_invalid_concurrent_blocks() -> None:
    with pytest.raises(ValueError, match="concurrent blocks"):
        IndexerConfig(
            rpc_url="http://localhost:8545",
            postgres_dsn="postgresql://localhost/cc",
            concurrent_blocks=0,
        )


def test_config_rejects_endpoint_concurrency_count_mismatch() -> None:
    with pytest.raises(ValueError, match="count must match"):
        IndexerConfig(
            rpc_url="http://a:8545,http://b:8545",
            endpoint_concurrency=(24,),
            postgres_dsn="postgresql://localhost/cc",
            concurrent_blocks=24,
        )


def test_config_rejects_endpoint_concurrency_sum_mismatch() -> None:
    with pytest.raises(ValueError, match="must sum to concurrent blocks"):
        IndexerConfig(
            rpc_url="http://a:8545,http://b:8545",
            endpoint_concurrency=(12, 20),
            postgres_dsn="postgresql://localhost/cc",
            concurrent_blocks=24,
        )


def test_config_rejects_follow_mode_with_end_block() -> None:
    with pytest.raises(ValueError, match="follow mode cannot be used"):
        IndexerConfig(
            rpc_url="http://localhost:8545",
            postgres_dsn="postgresql://localhost/cc",
            end_block=POST_MERGE_START_BLOCK,
            follow=True,
        )


@pytest.mark.parametrize("flag", ["--addresses", "--addresses-file"])
def test_ingest_parser_rejects_address_parameters(flag: str) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["ingest", flag, "0x" + "a" * 40])
