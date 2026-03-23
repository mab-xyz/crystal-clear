from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class InteractionScanHot(SQLModel, table=True):
    """Tracks hot/slow scan pairs that should be temporarily isolated."""

    __tablename__ = "interaction_scan_hot"
    __table_args__ = (
        UniqueConstraint(
            "from_address",
            "to_address",
            "interaction_type",
            name="uq_interaction_scan_hot_pair_type",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    from_address: str = Field(index=True)
    to_address: str = Field(index=True)
    interaction_type: str = Field(index=True)
    hot_until: datetime = Field(index=True)
    last_reason: str = Field(default="slow")
    last_duration_ms: int = Field(default=0)
    hit_count: int = Field(default=1)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


__all__ = ["InteractionScanHot"]
