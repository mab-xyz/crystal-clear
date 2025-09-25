from sqlmodel import SQLModel, Field
from datetime import datetime
from pydantic import BaseModel
from typing import List

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