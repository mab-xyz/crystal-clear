from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class FirstInteraction(SQLModel, table=True):
    """Persistent record for first-time interaction checks."""

    __tablename__ = "first_time_interactions"
    __table_args__ = (
        UniqueConstraint(
            "from_address",
            "to_address",
            "from_block",
            "to_block",
            "latest_offset",
            name="uq_first_time_window",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    from_address: str = Field(index=True, description="Normalized sender address")
    to_address: str = Field(index=True, description="Normalized target address")
    from_block: int = Field(description="Lower bound block (inclusive)")
    to_block: int = Field(description="Upper bound block (inclusive)")
    latest_offset: Optional[int] = Field(
        default=None, description="Original latest_offset parameter"
    )
    is_first_time: bool = Field(description="True if no interaction was found")
    result_block_number: Optional[int] = Field(
        default=None,
        description="Block number where an interaction was observed (if any)",
    )
    checked_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the check was run"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        index=True,
        description="Optional expiry for this cache entry",
    )


__all__ = ["FirstInteraction"]
