import pytest

from eth_graph_indexer.cli import build_parser
from eth_graph_indexer.config import IndexerConfig, POST_MERGE_START_BLOCK


def test_config_defaults_to_first_post_merge_block() -> None:
    config = IndexerConfig(
        rpc_url="http://localhost:8545",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="secret",
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


def test_ingest_parser_defaults_to_four_concurrent_blocks() -> None:
    args = build_parser().parse_args(["ingest"])
    assert args.concurrent_blocks == 4


def test_config_rejects_invalid_concurrent_blocks() -> None:
    with pytest.raises(ValueError, match="concurrent blocks"):
        IndexerConfig(
            rpc_url="http://localhost:8545",
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="secret",
            concurrent_blocks=0,
        )


def test_config_rejects_follow_mode_with_end_block() -> None:
    with pytest.raises(ValueError, match="follow mode cannot be used"):
        IndexerConfig(
            rpc_url="http://localhost:8545",
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="secret",
            end_block=POST_MERGE_START_BLOCK,
            follow=True,
        )


@pytest.mark.parametrize("flag", ["--addresses", "--addresses-file"])
def test_ingest_parser_rejects_address_parameters(flag: str) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["ingest", flag, "0x" + "a" * 40])
