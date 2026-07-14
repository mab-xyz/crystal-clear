"""Typed domain models."""

from __future__ import annotations

from dataclasses import dataclass


def hex_to_int(value: str | int | None, *, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    return int(value, 16)


def address_to_bytes(address: str) -> bytes:
    return bytes.fromhex(address.removeprefix("0x"))


@dataclass(frozen=True, slots=True)
class BlockData:
    number: int
    block_hash: str
    transactions: tuple[dict, ...]

    @classmethod
    def from_rpc(cls, payload: dict) -> BlockData:
        if not isinstance(payload, dict):
            raise ValueError("block response must be an object")
        number = hex_to_int(payload.get("number"))
        block_hash = payload.get("hash")
        transactions = payload.get("transactions")
        if not isinstance(block_hash, str) or not block_hash:
            raise ValueError(f"block {number} has no hash")
        if not isinstance(transactions, list):
            raise ValueError(f"block {number} transactions must be a list")
        return cls(number, block_hash.lower(), tuple(transactions))


@dataclass(frozen=True, slots=True)
class InteractionEdge:
    tx_hash: str
    block_number: int
    from_address: str
    to_address: str
    interaction_type: str | None
    value_wei: str

    @property
    def identity(self) -> tuple[str, str, str]:
        return self.tx_hash, self.from_address, self.to_address

    def to_record(self) -> dict:
        edge_id = f"{self.from_address}:{self.to_address}:{self.block_number}"
        return {
            "id": edge_id,
            "blockNumber": self.block_number,
            "from": address_to_bytes(self.from_address),
            "to": address_to_bytes(self.to_address),
        }


@dataclass(frozen=True, slots=True)
class BlockWrite:
    edges: list[InteractionEdge]
    block_number: int
    block_hash: str
