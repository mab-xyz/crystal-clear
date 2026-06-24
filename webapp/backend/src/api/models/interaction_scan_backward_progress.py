from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class InteractionScanBackwardProgress(SQLModel, table=True):
    """Tracks backward-scan progress for a (from, to, interaction_type) pair."""

    __tablename__ = "interaction_scan_backward_progress"
    __table_args__ = (
        UniqueConstraint(
            "from_address",
            "to_address",
            "interaction_type",
            name="uq_interaction_scan_backward_progress_pair_type",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    from_address: str = Field(index=True)
    to_address: str = Field(index=True)
    interaction_type: str
    last_backward_block: Optional[int] = Field(
        default=None,
        description="Lowest block reached so far; None = scan not yet started",
    )
    updated_at: datetime = Field(default_factory=datetime.utcnow)


__all__ = ["InteractionScanBackwardProgress"]
