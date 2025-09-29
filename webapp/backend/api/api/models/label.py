from datetime import datetime
from typing import List

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class Label(SQLModel, table=True):
    address: str = Field(primary_key=True)
    label: str
    date_added: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)


class LabelCreate(SQLModel):
    address: str
    label: str


class LabelUpdate(SQLModel):
    label: str


class AddressList(BaseModel):
    addresses: List[str]
