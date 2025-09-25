from sqlmodel import SQLModel, Field, Index
from sqlalchemy import text
from datetime import datetime
from typing import Optional, List

class AuditBase(SQLModel):
    """Base model with common fields"""
    protocol: str = Field(index=True)
    version: Optional[str] = Field(default=None, index=True)
    company: str = Field(index=True)
    url: str

class Audit(AuditBase, table=True):
    """Database model for audit entries"""
    id: Optional[int] = Field(default=None, primary_key=True)
    date_added: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)

    __table_args__ = (
        # Unique index when version IS NULL
        Index(
            "unique_protocol_company_when_version_null",
            "protocol", "company",
            unique=True,
            postgresql_where=text("version IS NULL")
        ),
        # Unique index for protocol + version + company when version IS NOT NULL
        Index(
            "unique_protocol_version_company_when_version_not_null",
            "protocol", "version", "company",
            unique=True,
            postgresql_where=text("version IS NOT NULL")
        ),
    )

class AuditCreate(AuditBase):
    """Request model for creating audit entries"""
    pass

class AuditUpdate(SQLModel):
    """Schema for updating audit entries"""
    url: str

class AuditResponse(AuditBase):
    """Response schema for audit entries"""
    date_added: datetime
    last_updated: datetime

class AuditListResponse(SQLModel):
    """Response schema for list of audits"""
    total: int
    items: list[AuditResponse]
