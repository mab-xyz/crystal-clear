"""Hashes required by the Ledger Web3checks descriptor (TX_HASH, DOMAIN_HASH)."""

from __future__ import annotations

from typing import Any

import base58
import rlp
from eth_account.messages import encode_typed_data
from eth_utils.crypto import keccak

# Number of RLP items in the *unsigned* payload of each typed transaction.
_UNSIGNED_LEN = {1: 8, 2: 9, 3: 11, 4: 10}


class UnsupportedPayload(ValueError):
    """Well-formed input we do not handle (-> HTTP 422 code 2)."""


def _hex_to_bytes(value: str) -> bytes:
    s = value.strip()
    if not s.startswith(("0x", "0X")):
        raise ValueError("hex value must be 0x-prefixed")
    return bytes.fromhex(s[2:])


def evm_address_bytes(address: str) -> bytes:
    b = _hex_to_bytes(address)
    if len(b) != 20:
        raise ValueError("address must be 20 bytes")
    return b


def evm_tx_hash(raw_hex: str) -> bytes:
    """keccak256 of the unsigned transaction.

    Accepts an unsigned or signed RLP; a signature, if present, is stripped
    so the hash is always that of the unsigned form.
    """
    raw = _hex_to_bytes(raw_hex)
    if not raw:
        raise ValueError("empty transaction")
    first = raw[0]
    if first >= 0xC0:  # legacy: bare RLP list
        items = rlp.decode(raw)
        if len(items) == 6:
            return keccak(raw)
        if len(items) != 9:
            raise ValueError("unexpected legacy transaction length")
        if items[7] == b"" and items[8] == b"":  # EIP-155 unsigned
            return keccak(raw)
        v = int.from_bytes(items[6], "big")
        if v in (27, 28):
            return keccak(rlp.encode(items[:6]))
        chain_id = (v - 35) // 2
        return keccak(
            rlp.encode(items[:6] + [chain_id.to_bytes(8, "big").lstrip(b"\0"), b"", b""])
        )
    if first not in _UNSIGNED_LEN:
        raise UnsupportedPayload(f"unsupported transaction type 0x{first:02x}")
    items = rlp.decode(raw[1:])
    n = _UNSIGNED_LEN[first]
    if len(items) == n:
        return keccak(raw)
    if len(items) == n + 3:
        return keccak(bytes([first]) + rlp.encode(items[:n]))
    raise ValueError("unexpected typed transaction length")


def eip712_hashes(data: dict[str, Any]) -> tuple[bytes, bytes]:
    """Return (domain_hash, message_hash) = hashStruct(domain), hashStruct(message)."""
    types = {
        k: v for k, v in data.get("types", {}).items() if k != "EIP712Domain"
    }
    full = dict(data)
    full["types"] = {**types, "EIP712Domain": data["types"]["EIP712Domain"]}
    signable = encode_typed_data(full_message=_coerce_numbers(full))
    return bytes(signable.header), bytes(signable.body)


def _coerce_numbers(full: dict[str, Any]) -> dict[str, Any]:
    """Seaport-style payloads carry uint/int values as decimal strings."""
    types = full["types"]

    def conv(type_name: str, value: Any) -> Any:
        if type_name.endswith("]"):
            inner = type_name[: type_name.rindex("[")]
            return [conv(inner, v) for v in value]
        if type_name in types:
            return {
                f["name"]: conv(f["type"], value[f["name"]])
                for f in types[type_name]
            }
        if type_name.startswith(("uint", "int")) and isinstance(value, str):
            return int(value, 0)
        return value

    out = dict(full)
    out["message"] = conv(full["primaryType"], full["message"])
    out["domain"] = conv("EIP712Domain", full["domain"])
    return out


def solana_decode(value: str, expected_len: int | None = None) -> bytes:
    try:
        b = base58.b58decode(value)
    except ValueError as err:
        raise ValueError("invalid base58") from err
    if expected_len is not None and len(b) != expected_len:
        raise ValueError(f"expected {expected_len} bytes")
    return b


def evm_tx_fields(raw_hex: str) -> dict[str, int]:
    """nonce / gas / value / max fee per gas of an unsigned or signed tx."""
    raw = _hex_to_bytes(raw_hex)
    num = lambda b: int.from_bytes(b, "big")  # noqa: E731
    if raw[0] >= 0xC0:  # legacy
        i = rlp.decode(raw)
        return {"nonce": num(i[0]), "fee": num(i[1]), "gas": num(i[2]), "value": num(i[4])}
    i = rlp.decode(raw[1:])
    if raw[0] == 1:  # [chain, nonce, gasPrice, gas, to, value, ...]
        return {"nonce": num(i[1]), "fee": num(i[2]), "gas": num(i[3]), "value": num(i[5])}
    # types 2/3/4: [chain, nonce, tip, maxFee, gas, to, value, ...]
    return {"nonce": num(i[1]), "fee": num(i[3]), "gas": num(i[4]), "value": num(i[6])}


SIMULATION_GAS = 30_000_000


def with_own_gas(raw_hex: str, gas: int = SIMULATION_GAS) -> str:
    """Unsigned re-encoding of ``raw_hex`` with our own gas parameters.

    The spec asks the partner to use its own gas parameters: gas limit is
    ``gas`` and all fee fields are 0 (no base-fee/balance gating). Only for
    simulation; ``evm_tx_hash`` is always computed on the original payload.
    """
    raw = _hex_to_bytes(raw_hex)
    g = gas.to_bytes((gas.bit_length() + 7) // 8, "big")
    if raw[0] >= 0xC0:  # legacy: [nonce, gasPrice, gas, to, value, data, ...]
        i = rlp.decode(raw)
        out = rlp.encode([i[0], b"", g, i[3], i[4], i[5]])
        return "0x" + out.hex()
    t = raw[0]
    if t not in _UNSIGNED_LEN:
        raise UnsupportedPayload(f"unsupported transaction type 0x{t:02x}")
    i = rlp.decode(raw[1:])[: _UNSIGNED_LEN[t]]
    if t == 1:  # [chain, nonce, gasPrice, gas, ...]
        i[2], i[3] = b"", g
    else:  # [chain, nonce, tip, maxFee, gas, ...]
        i[2], i[3], i[4] = b"", b"", g
    return "0x" + (bytes([t]) + rlp.encode(i)).hex()
