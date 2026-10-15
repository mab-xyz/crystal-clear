"""Request/response models for the Ledger Web3checks on-device API (v0.0.11)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class TxInput(BaseModel):
    from_: str = Field(..., alias="from", description="Signer address")
    raw: str = Field(..., description="Unsigned tx: RLP hex (EVM) / base58 message (Solana)")


class TxScanInput(BaseModel):
    tx: TxInput
    chain: Optional[int] = Field(None, description="EVM chain id (required for ethereum); Solana 900/901/902")
    domain: Optional[str] = None
    block: Optional[int] = Field(None, description="Block (EVM) / slot (Solana); tests only")


class Eip712Input(BaseModel):
    from_: str = Field(..., alias="from")
    data: dict[str, Any]


class Eip712ScanInput(BaseModel):
    msg: Eip712Input
    domain: Optional[str] = None
    block: Optional[int] = None


class ScanResponse(BaseModel):
    public_key_id: str
    descriptor: str
    block: int
    simulation: dict[str, Any] = {}


class ProviderError(BaseModel):
    code: int
    message: str
