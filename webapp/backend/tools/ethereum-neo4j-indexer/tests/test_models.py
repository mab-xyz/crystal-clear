import pytest

from eth_graph_indexer.models import (
    BlockData,
    InteractionEdge,
    address_to_bytes,
    hex_to_int,
)


def test_hex_to_int_accepts_hex_and_integer() -> None:
    assert hex_to_int("0x10") == 16
    assert hex_to_int(16) == 16
    assert hex_to_int(None) == 0


def test_block_data_parses_rpc_payload() -> None:
    block = BlockData.from_rpc(
        {"number": "0x2a", "hash": "0xABC", "transactions": [{"hash": "0x1"}]}
    )
    assert block.number == 42
    assert block.block_hash == "0xabc"
    assert len(block.transactions) == 1


def test_block_data_rejects_missing_hash() -> None:
    with pytest.raises(ValueError, match="has no hash"):
        BlockData.from_rpc({"number": "0x1", "transactions": []})


def test_address_to_bytes_converts_normalized_address() -> None:
    assert address_to_bytes("0x" + "0a" * 20) == bytes([10]) * 20


def test_interaction_record_uses_binary_addresses_and_block_number() -> None:
    edge = InteractionEdge(
        tx_hash="0x01",
        block_number=1,
        from_address="0x" + "a" * 40,
        to_address="0x" + "b" * 40,
        interaction_type=None,
        value_wei="0",
    )
    record = edge.to_record()
    assert record == {
        "blockNumber": 1,
        "from": bytes.fromhex("a" * 40),
        "to": bytes.fromhex("b" * 40),
    }
