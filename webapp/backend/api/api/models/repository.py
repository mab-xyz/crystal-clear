from sqlmodel import SQLModel, Field, Index
from sqlalchemy import text
from datetime import datetime
from typing import Optional, List

class RepositoryBase(SQLModel):
    """Base model with common fields"""
    protocol: str = Field(index=True)
    version: Optional[str] = Field(default=None, index=True)
    url: str

class Repository(RepositoryBase, table=True):
    """Database model for source repositories"""
    id: Optional[int] = Field(default=None, primary_key=True)
    date_added: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)

    __table_args__ = (
        # Unique index when version IS NULL
        Index(
            "unique_protocol_when_version_null",
            "protocol",
            unique=True,
            postgresql_where=text("version IS NULL")
        ),
        # Unique index for protocol + version when version IS NOT NULL
        Index(
            "unique_protocol_version_when_version_not_null",
            "protocol", "version",
            unique=True,
            postgresql_where=text("version IS NOT NULL")
        ),
    )

class RepositoryCreate(RepositoryBase):
    """Request model for creating source repository entries"""
    pass

class RepositoryUpdate(SQLModel):
    """Request model for updating source repository entries"""
    url: str

class RepositoryResponse(RepositoryBase):
    """Response model for source repository operations"""
    date_added: datetime
    last_updated: datetime

class RepositoryListResponse(SQLModel):
    """Response model for list of source repository entries"""
    total: int
    items: List[RepositoryResponse]