from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel


class ContractVerification(SQLModel, table=True):
    """Persistent verification record per contract/source pair."""

    __tablename__ = "contract_verifications"
    __table_args__ = (
        UniqueConstraint(
            "contract_address", "source", name="uq_contract_verifications"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    contract_address: str = Field(
        index=True, description="Normalized contract address"
    )
    source: str = Field(
        default="unknown",
        index=True,
        description="Source of the verification info (sourcify/etherscan)",
    )
    verification_status: str = Field(
        default="not-verified",
        index=True,
        description="Verification status returned by the upstream service",
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="Raw payload returned by the verification service",
    )
    checked_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this record was last refreshed",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        index=True,
        description="Optional expiry for the cached record",
    )


__all__ = ["ContractVerification"]
