from sqlmodel import SQLModel, Field
from datetime import datetime

class Deployment(SQLModel, table=True):
    address: str = Field(primary_key=True)
    deployer: str
    deployer_eoa: str
    tx_hash: str
    block_number: int
    date_added: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)


class DeploymentCreate(SQLModel):
    address: str
    deployer: str
    deployer_eoa: str
    tx_hash: str
    block_number: int
