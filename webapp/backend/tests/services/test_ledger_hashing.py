import json
from pathlib import Path

import pytest
import rlp
from eth_utils.crypto import keccak

from src.api.services import ledger_hashing as lh

FIX = Path(__file__).parent.parent / "fixtures"


def _ref_encode_type(name, types):
    deps = {name}
    stack = [name]
    while stack:
        t = stack.pop()
        for f in types[t]:
            base = f["type"].split("[")[0]
            if base in types and base not in deps:
                deps.add(base)
                stack.append(base)
    order = [name] + sorted(deps - {name})
    return "".join(
        f"{t}({','.join(f['type'] + ' ' + f['name'] for f in types[t])})"
        for t in order
    )


def _ref_value(t, v, types):
    if t.endswith("]"):
        inner = t[: t.rindex("[")]
        return keccak(b"".join(_ref_value(inner, x, types) for x in v))
    if t in types:
        return _ref_struct(t, v, types)
    if t == "string":
        return keccak(v.encode())
    if t == "bytes":
        return keccak(bytes.fromhex(v[2:]))
    if t == "address":
        return bytes(12) + bytes.fromhex(v[2:])
    if t.startswith("bytes"):
        return bytes.fromhex(v[2:]).ljust(32, b"\0")
    return int(v).to_bytes(32, "big")


def _ref_struct(name, value, types):
    enc = keccak(_ref_encode_type(name, types).encode())
    for f in types[name]:
        enc += _ref_value(f["type"], value[f["name"]], types)
    return keccak(enc)


def test_eip712_seaport_matches_independent_reference():
    data = json.loads((FIX / "ledger_eip712_seaport.json").read_text())["msg"]["data"]
    dom, msg = lh.eip712_hashes(data)
    assert dom == _ref_struct("EIP712Domain", data["domain"], data["types"])
    assert msg == _ref_struct(data["primaryType"], data["message"], data["types"])


def test_eip712_tamper_changes_message_hash_not_domain():
    data = json.loads((FIX / "ledger_eip712_seaport.json").read_text())["msg"]["data"]
    dom, msg = lh.eip712_hashes(data)
    data["message"]["salt"] = "1"
    dom2, msg2 = lh.eip712_hashes(data)
    assert dom == dom2 and msg != msg2


def test_evm_unsigned_type2_hash_is_keccak_of_raw():
    raw = json.loads((FIX / "ledger_eth_tx.json").read_text())["tx"]["raw"]
    assert lh.evm_tx_hash(raw) == keccak(bytes.fromhex(raw[2:]))


def test_evm_signed_type2_strips_signature():
    raw = json.loads((FIX / "ledger_eth_tx.json").read_text())["tx"]["raw"]
    items = rlp.decode(bytes.fromhex(raw[4:]))
    signed = b"\x02" + rlp.encode(items + [b"\x01", b"\x02" * 32, b"\x03" * 32])
    assert lh.evm_tx_hash("0x" + signed.hex()) == lh.evm_tx_hash(raw)


def test_evm_legacy_signed_matches_unsigned_eip155():
    base = [b"\x01", b"\x01", b"\x52\x08", b"\x11" * 20, b"\x05", b""]
    unsigned = rlp.encode(base + [b"\x01", b"", b""])
    signed = rlp.encode(base + [b"\x25", b"\x02" * 32, b"\x03" * 32])  # v=37
    assert lh.evm_tx_hash("0x" + signed.hex()) == keccak(unsigned)
    assert lh.evm_tx_hash("0x" + unsigned.hex()) == keccak(unsigned)


def test_evm_rejects_bad_input():
    with pytest.raises(ValueError):
        lh.evm_tx_hash("02ab")
    with pytest.raises(lh.UnsupportedPayload):
        lh.evm_tx_hash("0x09c0")


def test_solana_decode():
    assert lh.solana_decode("11111111111111111111111111111111", 32) == bytes(32)
    with pytest.raises(ValueError):
        lh.solana_decode("0OIl")
    with pytest.raises(ValueError):
        lh.solana_decode("1111", 32)


def test_evm_tx_fields_typed_and_legacy():
    raw = json.loads((FIX / "ledger_eth_tx.json").read_text())["tx"]["raw"]
    f = lh.evm_tx_fields(raw)
    assert f == {"nonce": 0x28, "fee": 0x12C44E32BA, "gas": 0x9FE8, "value": 0}
    legacy = rlp.encode([b"\x07", b"\x05", b"\x52\x08", b"\x11" * 20, b"\x09", b""])
    assert lh.evm_tx_fields("0x" + legacy.hex()) == {
        "nonce": 7, "fee": 5, "gas": 0x5208, "value": 9,
    }
