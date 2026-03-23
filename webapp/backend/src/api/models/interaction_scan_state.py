from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class InteractionScanState(SQLModel, table=True):
    """Incremental scan state for a (from, to, interaction_type) pair."""

    __tablename__ = "interaction_scan_state"
    __table_args__ = (
        UniqueConstraint(
            "from_address",
            "to_address",
            "interaction_type",
            name="uq_interaction_scan_state_pair_type",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    from_address: str = Field(index=True)
    to_address: str = Field(index=True)
    interaction_type: str = Field(
        default="direct",
        description="direct or transitive",
    )
    from_block: int = Field(default=0, description="Creation-based lower bound")
    last_analyzed_block: Optional[int] = Field(
        default=None,
        description="Last fully scanned block",
    )
    how_many_times: int = Field(default=0, description="Accumulated interactions")
    first_time_interact: bool = Field(
        default=True,
        description="True when how_many_times == 0 (no interactions found yet)",
    )
    needs_creation_retry: bool = Field(
        default=False,
        description="True when creation block fallback failed",
    )
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    last_requested_at: Optional[datetime] = Field(
        default=None,
        description="Last time this pair was seen in a tx-risk endpoint request",
    )


__all__ = ["InteractionScanState"]
