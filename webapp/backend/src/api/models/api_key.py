from datetime import datetime
from typing import Optional

from sqlmodel import Field, Index, SQLModel


class ApiKey(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    prefix: str = Field(index=True, description="First characters to identify key")
    key_hash: str = Field(index=True, description="sha256 of the full key")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    revoked_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    __table_args__ = (
        Index("ux_apikey_prefix", "prefix", unique=True),
        Index("ux_apikey_key_hash", "key_hash", unique=True),
    )


class ApiKeyCreate(SQLModel):
    name: str


class ApiKeyResponse(SQLModel):
    id: int
    name: str
    prefix: str
    created_at: datetime
    revoked_at: Optional[datetime]
    last_used_at: Optional[datetime]


class ApiKeyCreatedResponse(ApiKeyResponse):
    key: str


class ApiKeyListResponse(SQLModel):
    total: int
    items: list[ApiKeyResponse]

