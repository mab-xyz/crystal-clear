from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AddressMetadata(SQLModel, table=True):
    """Address-level metadata used for scan pruning and retries."""

    __tablename__ = "address_metadata"

    address: str = Field(primary_key=True)
    address_type: str = Field(
        default="unknown",
        description="eoa, eoa_delegated, contract, or unknown",
    )
    delegate_address: Optional[str] = Field(
        default=None,
        description="Delegate contract address for EIP-7702 delegated EOAs",
    )
    creation_block: Optional[int] = Field(
        default=None,
        description="Contract creation block when address_type=contract",
    )
    first_tx_block: Optional[int] = Field(
        default=None,
        description="First observed outbound tx block for EOAs",
    )
    source: Optional[str] = Field(
        default=None,
        description="Source used to populate metadata",
    )
    needs_retry: bool = Field(
        default=False,
        description="True when metadata lookup failed and should be retried",
    )
    checked_at: datetime = Field(default_factory=datetime.utcnow)


__all__ = ["AddressMetadata"]
