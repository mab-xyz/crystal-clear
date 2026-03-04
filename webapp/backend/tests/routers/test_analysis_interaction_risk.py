import pytest
from fastapi import HTTPException

from src.api.routers.analysis import _validate_tx_hash


# Accepts a canonical lowercase tx hash and returns it unchanged.
def test_validate_tx_hash_accepts_valid_lowercase_hash():
    value = _validate_tx_hash(
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    assert value == "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


# Normalizes uppercase hex characters to lowercase.
def test_validate_tx_hash_normalizes_uppercase_hash():
    value = _validate_tx_hash(
        "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    )
    assert value == "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


@pytest.mark.parametrize(
    "bad_hash",
    [
        "",
        "0x",
        "0x1234",
        "not-a-hash",
        "0xgggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg",
    ],
)
# Rejects malformed tx hashes and returns a consistent 422 error payload.
def test_validate_tx_hash_rejects_invalid_values(bad_hash):
    with pytest.raises(HTTPException) as exc:
        _validate_tx_hash(bad_hash)

    assert exc.value.status_code == 422
    assert exc.value.detail == "Invalid tx_hash format"
