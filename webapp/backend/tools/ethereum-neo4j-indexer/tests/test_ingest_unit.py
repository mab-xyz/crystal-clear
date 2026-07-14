import time
from dataclasses import dataclass

from eth_graph_indexer.checkpoint import resolve_start_block
from eth_graph_indexer.config import IndexerConfig
from eth_graph_indexer.ingest import (
    Ingestor,
    needs_receipts,
    parse_external_interactions,
)
from eth_graph_indexer.models import BlockData
from eth_graph_indexer.traces import parse_parity_traces

A = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
B = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
C = "0xcccccccccccccccccccccccccccccccccccccccc"
TX1 = "0x" + "1" * 64
TX2 = "0x" + "2" * 64


def test_parses_external_transaction() -> None:
    block = BlockData(
        10,
        "0xblock",
        ({"hash": TX1, "from": A, "to": B, "value": "0x2a"},),
    )
    edges = parse_external_interactions(block, {})
    assert len(edges) == 1
    assert edges[0].from_address == A
    assert edges[0].to_address == B
    assert edges[0].value_wei == "42"
    assert edges[0].interaction_type == "external"


def test_parses_contract_creation_receipt() -> None:
    block = BlockData(
        10,
        "0xblock",
        ({"hash": TX1, "from": A, "to": None, "value": "0x0"},),
    )
    receipts = {TX1: {"transactionHash": TX1, "contractAddress": C}}
    edge = parse_external_interactions(block, receipts)[0]
    assert edge.to_address == C
    assert edge.interaction_type == "contract_creation"


def test_failed_contract_creation_has_no_edge() -> None:
    block = BlockData(
        10,
        "0xblock",
        ({"hash": TX1, "from": A, "to": None, "value": "0x0"},),
    )
    receipts = {TX1: {"transactionHash": TX1, "contractAddress": None}}
    assert parse_external_interactions(block, receipts) == []


def test_receipts_are_only_needed_for_contract_creation() -> None:
    normal_block = BlockData(
        10,
        "0xblock",
        ({"hash": TX1, "from": A, "to": B, "value": "0x0"},),
    )
    creation_block = BlockData(
        10,
        "0xblock",
        ({"hash": TX1, "from": A, "to": None, "value": "0x0"},),
    )

    assert not needs_receipts(normal_block)
    assert needs_receipts(creation_block)


def test_parses_internal_call_and_selfdestruct() -> None:
    traces = [
        {
            "type": "call",
            "transactionHash": TX1,
            "action": {
                "from": A,
                "to": B,
                "value": "0x5",
                "callType": "delegatecall",
            },
        },
        {
            "type": "suicide",
            "transactionHash": TX1,
            "action": {
                "address": B,
                "refundAddress": C,
                "balance": "0x9",
            },
        },
    ]
    edges = parse_parity_traces(traces, 12)
    assert [item.interaction_type for item in edges] == [
        "internal_delegatecall",
        "selfdestruct",
    ]
    assert edges[1].value_wei == "9"


def test_parity_trace_parser_skips_root_call() -> None:
    traces = [
        {
            "type": "call",
            "transactionHash": TX1,
            "traceAddress": [],
            "action": {
                "from": A,
                "to": B,
                "value": "0x5",
                "callType": "call",
            },
        },
        {
            "type": "call",
            "transactionHash": TX1,
            "traceAddress": [0],
            "action": {
                "from": A,
                "to": B,
                "value": "0x6",
                "callType": "call",
            },
        },
    ]
    edges = parse_parity_traces(traces, 12)
    assert len(edges) == 1
    assert edges[0].value_wei == "6"


def test_checkpoint_resume_logic() -> None:
    assert resolve_start_block(100, 120, resume=True) == 121
    assert resolve_start_block(100, 99, resume=True) == 100
    assert resolve_start_block(100, 120, resume=False) == 100
    assert resolve_start_block(100, None, resume=True) == 100


class FakeRpc:
    def call(self, method: str, params=None):
        if method == "eth_blockNumber":
            return "0x5"
        if method == "eth_getBlockByNumber":
            number = int(params[0], 16)
            return {
                "number": hex(number),
                "hash": f"0xblock{number}",
                "transactions": [
                    {
                        "hash": TX1 if number == 4 else TX2,
                        "from": A,
                        "to": B,
                        "value": "0x1",
                    }
                ],
            }
        raise AssertionError(method)


class SlowFakeRpc(FakeRpc):
    def call(self, method: str, params=None):
        if method == "eth_getBlockByNumber":
            number = int(params[0], 16)
            if number == 4:
                time.sleep(0.05)
        return super().call(method, params)


class FakeEndpointRpc(FakeRpc):
    def __init__(self, url: str) -> None:
        self.url = url
        self.block_calls = []

    def call(self, method: str, params=None):
        if method == "eth_getBlockByNumber":
            self.block_calls.append(int(params[0], 16))
        if method == "trace_block":
            return []
        return super().call(method, params)


class FakeMultiRpc:
    def __init__(self, clients) -> None:
        self.clients = tuple(clients)

    def call(self, method: str, params=None):
        if method == "eth_blockNumber":
            return "0x6"
        raise AssertionError(method)


class FakeReceipts:
    def __init__(self):
        self.calls = []

    def get_for_block(self, block_number, transactions):
        self.calls.append(block_number)
        return {
            tx["hash"]: {
                "transactionHash": tx["hash"],
                "contractAddress": None,
            }
            for tx in transactions
        }


class FakeTraces:
    def get_for_block(self, block_number, transactions):
        return []


@dataclass
class FakeCheckpoint:
    last_processed_block: int


class FakeStore:
    def __init__(self):
        self.writes = []
        self.batch_writes = []

    def verify_connectivity(self):
        pass

    def ensure_schema(self):
        pass

    def get_checkpoint(self, checkpoint_id):
        return FakeCheckpoint(3)

    def write_block(self, **kwargs):
        self.writes.append(kwargs)
        return len(kwargs["edges"]) * 2, len(kwargs["edges"])

    def write_blocks(self, blocks, *, checkpoint_id, batch_size):
        self.batch_writes.append([block.block_number for block in blocks])
        edges = [edge for block in blocks for edge in block.edges]
        for block in blocks:
            self.writes.append(
                {
                    "edges": block.edges,
                    "block_number": block.block_number,
                    "block_hash": block.block_hash,
                    "checkpoint_id": checkpoint_id,
                    "batch_size": batch_size,
                }
            )
        return len(edges) * 2, len(edges)


def test_ingestor_resumes_and_processes_blocks_in_order() -> None:
    config = IndexerConfig(
        rpc_url="http://localhost:8545",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="secret",
        start_block=1,
        end_block=5,
        progress_interval=1,
    )
    store = FakeStore()
    stats = Ingestor(
        config,
        FakeRpc(),
        store,
        receipt_loader=FakeReceipts(),
        trace_loader=FakeTraces(),
    ).run()

    assert [write["block_number"] for write in store.writes] == [4, 5]
    assert stats.blocks_processed == 2
    assert stats.transactions_processed == 2
    assert stats.relationships_upserted == 2


def test_ingestor_commits_concurrent_blocks_in_order() -> None:
    config = IndexerConfig(
        rpc_url="http://localhost:8545",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="secret",
        start_block=1,
        end_block=5,
        concurrent_blocks=2,
        progress_interval=1,
    )
    store = FakeStore()
    Ingestor(
        config,
        SlowFakeRpc(),
        store,
        receipt_loader=FakeReceipts(),
        trace_loader=FakeTraces(),
    ).run()

    assert [write["block_number"] for write in store.writes] == [4, 5]


def test_ingestor_honors_per_endpoint_worker_limits() -> None:
    config = IndexerConfig(
        rpc_url="http://a:8545,http://b:8545",
        endpoint_concurrency=(1, 2),
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="secret",
        start_block=1,
        end_block=6,
        concurrent_blocks=3,
        trace_mode="none",
        resume=False,
        progress_interval=1,
    )
    first = FakeEndpointRpc("http://a:8545")
    second = FakeEndpointRpc("http://b:8545")

    Ingestor(
        config,
        FakeMultiRpc([first, second]),
        FakeStore(),
        receipt_loader=FakeReceipts(),
        trace_loader=FakeTraces(),
    ).run()

    assert first.block_calls == [1, 4]
    assert second.block_calls == [2, 3, 5, 6]


def test_ingestor_batches_ordered_commits() -> None:
    config = IndexerConfig(
        rpc_url="http://localhost:8545",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="secret",
        start_block=1,
        end_block=5,
        commit_batch_size=2,
        progress_interval=1,
    )
    store = FakeStore()
    Ingestor(
        config,
        FakeRpc(),
        store,
        receipt_loader=FakeReceipts(),
        trace_loader=FakeTraces(),
    ).run()

    assert store.batch_writes == [[4, 5]]


def test_ingestor_indexes_untracked_addresses() -> None:
    config = IndexerConfig(
        rpc_url="http://localhost:8545",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="secret",
        start_block=4,
        end_block=4,
        resume=False,
        progress_interval=1,
    )
    store = FakeStore()
    Ingestor(
        config,
        FakeRpc(),
        store,
        receipt_loader=FakeReceipts(),
        trace_loader=FakeTraces(),
    ).run()

    assert store.writes[0]["edges"][0].from_address == A
    assert store.writes[0]["edges"][0].to_address == B


def test_ingestor_skips_receipts_when_block_has_no_creation() -> None:
    receipts = FakeReceipts()
    config = IndexerConfig(
        rpc_url="http://localhost:8545",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="secret",
        start_block=4,
        end_block=4,
        resume=False,
        progress_interval=1,
    )

    Ingestor(
        config,
        FakeRpc(),
        FakeStore(),
        receipt_loader=receipts,
        trace_loader=FakeTraces(),
    ).run()

    assert receipts.calls == []
