from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class InteractionScanSkippedRange(SQLModel, table=True):
    """Records block ranges that could not be fully scanned and were skipped."""

    __tablename__ = "interaction_scan_skipped_range"

    id: Optional[int] = Field(default=None, primary_key=True)
    from_address: str = Field(index=True)
    to_address: str = Field(index=True)
    interaction_type: str = Field(index=True)
    range_start: int
    range_end: int
    reason: str = Field(default="incomplete")
    created_at: datetime = Field(default_factory=datetime.utcnow)


__all__ = ["InteractionScanSkippedRange"]
