import pytest

from eth_graph_indexer.address_filter import normalize_address

A = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def test_normalizes_checksum_insensitively() -> None:
    assert normalize_address("  0xAaAaAaAaAaAaAaAaAaAaAaAaAaAaAaAaAaAaAaAa ") == A


@pytest.mark.parametrize(
    "value",
    ["", "0x1234", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "0x" + "g" * 40],
)
def test_invalid_address_fails_fast(value: str) -> None:
    with pytest.raises(ValueError, match="invalid Ethereum address"):
        normalize_address(value)
