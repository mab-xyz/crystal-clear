from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


class LedgerReport(SQLModel, table=True):
    """Report behind a Ledger descriptor's tiny URL (rolling retention)."""

    __tablename__ = "ledger_report"

    id: str = Field(primary_key=True, max_length=16)
    family: str
    kind: str = Field(description="tx | eip-712")
    block: Optional[int] = None
    request_json: dict = Field(sa_column=Column(JSON, nullable=False))
    simulation_json: dict = Field(sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("ix_ledger_report_last_accessed_at", "last_accessed_at"),
    )
