"""Ledger "Web3checks on device" descriptor: DER-TLV encoding and signing.

Pure functions, no I/O. Spec: OpenAPI Web3checks on device v0.0.11.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)

_SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

STRUCTURE_TYPE = 0x01
VERSION = 0x02
CHAIN_ID = 0x23
ADDRESS = 0x22
TX_HASH = 0x27
DOMAIN_HASH = 0x28
W3C_NORMALIZED_RISK = 0x80
W3C_NORMALIZED_CATEGORY = 0x81
W3C_PROVIDER_MESSAGE = 0x82
W3C_TINY_URL = 0x83
W3C_SIMULATION_TYPE = 0x84
DER_SIGNATURE = 0x15

STRUCTURE_TYPE_VALUE = 0x09
VERSION_VALUE = 0x01

RISK_BENIGN = 0x00
RISK_RISK = 0x01
RISK_THREAT = 0x02

CATEGORY_NA = 0x00
CATEGORY_OTHERS = 0x01
CATEGORY_ADDRESS = 0x02
CATEGORY_CONTRACT = 0x03
CATEGORY_LOSING = 0x04

SIMULATION_TX = 0x00
SIMULATION_EIP712 = 0x01

MAX_PROVIDER_MESSAGE = 25
MAX_TINY_URL = 30


def der_length(n: int) -> bytes:
    """DER length (also used for tags): short form < 128, else long form."""
    if n < 0:
        raise ValueError("negative length")
    if n < 0x80:
        return bytes([n])
    body = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(body)]) + body


def tlv(tag: int, value: bytes) -> bytes:
    return der_length(tag) + der_length(len(value)) + value


@dataclass(frozen=True)
class DescriptorFields:
    address: bytes
    tx_hash: bytes
    risk: int
    category: int
    tiny_url: str
    simulation_type: int
    chain_id: Optional[int] = None
    domain_hash: Optional[bytes] = None
    provider_message: Optional[str] = None


def _ascii(value: str, max_len: int, name: str) -> bytes:
    raw = value.encode("ascii")
    if len(raw) > max_len:
        raise ValueError(f"{name} longer than {max_len} bytes")
    return raw


def encode_fields(f: DescriptorFields) -> bytes:
    """TLV bytes from STRUCTURE_TYPE to W3C_SIMULATION_TYPE (signed part)."""
    if f.risk not in (RISK_BENIGN, RISK_RISK, RISK_THREAT):
        raise ValueError("invalid risk")
    if len(f.tx_hash) != 32:
        raise ValueError("tx_hash must be 32 bytes")
    if f.domain_hash is not None and len(f.domain_hash) != 32:
        raise ValueError("domain_hash must be 32 bytes")
    out = tlv(STRUCTURE_TYPE, bytes([STRUCTURE_TYPE_VALUE]))
    out += tlv(VERSION, bytes([VERSION_VALUE]))
    if f.chain_id is not None:
        out += tlv(CHAIN_ID, f.chain_id.to_bytes(8, "big"))
    out += tlv(ADDRESS, f.address)
    out += tlv(TX_HASH, f.tx_hash)
    if f.domain_hash is not None:
        out += tlv(DOMAIN_HASH, f.domain_hash)
    out += tlv(W3C_NORMALIZED_RISK, bytes([f.risk]))
    out += tlv(W3C_NORMALIZED_CATEGORY, bytes([f.category]))
    if f.provider_message:
        out += tlv(
            W3C_PROVIDER_MESSAGE,
            _ascii(f.provider_message, MAX_PROVIDER_MESSAGE, "message"),
        )
    out += tlv(W3C_TINY_URL, _ascii(f.tiny_url, MAX_TINY_URL, "tiny_url"))
    out += tlv(W3C_SIMULATION_TYPE, bytes([f.simulation_type]))
    return out


def load_private_key(hex_key: str) -> ec.EllipticCurvePrivateKey:
    return ec.derive_private_key(int(hex_key, 16), ec.SECP256K1())


def public_key_compressed_hex(key: ec.EllipticCurvePrivateKey) -> str:
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        PublicFormat,
    )

    return (
        key.public_key()
        .public_bytes(Encoding.X962, PublicFormat.CompressedPoint)
        .hex()
    )


def sign_descriptor(
    f: DescriptorFields, key: ec.EllipticCurvePrivateKey
) -> bytes:
    """Full descriptor: signed TLV fields followed by DER_SIGNATURE."""
    body = encode_fields(f)
    r, s = decode_dss_signature(key.sign(body, ec.ECDSA(hashes.SHA256())))
    if s > _SECP256K1_N // 2:  # canonical low-S
        s = _SECP256K1_N - s
    sig = encode_dss_signature(r, s)
    return body + tlv(DER_SIGNATURE, sig)


def _read_der(buf: bytes, i: int) -> tuple[int, int]:
    first = buf[i]
    if first < 0x80:
        return first, i + 1
    n = first & 0x7F
    return int.from_bytes(buf[i + 1 : i + 1 + n], "big"), i + 1 + n


def parse_descriptor(desc: bytes) -> dict[int, bytes]:
    """Parse TLVs into {tag: value} (test/verification helper)."""
    out: dict[int, bytes] = {}
    i = 0
    while i < len(desc):
        tag, i = _read_der(desc, i)
        length, i = _read_der(desc, i)
        out[tag] = desc[i : i + length]
        i += length
    return out


def verify_descriptor(desc: bytes, public_key_hex: str) -> bool:
    """Independent check: signature covers everything before DER_SIGNATURE."""
    from cryptography.exceptions import InvalidSignature

    i = 0
    while i < len(desc):
        start = i
        tag, i = _read_der(desc, i)
        length, i = _read_der(desc, i)
        if tag == DER_SIGNATURE:
            pub = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256K1(), bytes.fromhex(public_key_hex)
            )
            try:
                pub.verify(
                    desc[i : i + length],
                    desc[:start],
                    ec.ECDSA(hashes.SHA256()),
                )
            except InvalidSignature:
                return False
            return True
        i += length
    return False


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()
