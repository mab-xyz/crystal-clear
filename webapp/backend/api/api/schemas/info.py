from typing import List

from crystal_clear.clients.models import VerificationDetails
from crystal_clear.code_analyzer import PermissionsInfo, ProxyInfo
from pydantic import BaseModel, Field


class LatestBlockResponse(BaseModel):
    """Request model for contract dependencies analysis."""

    block_number: int = Field(
        ..., description="Latest block number from the Ethereum network"
    )


class DeploymentInfoRequest(BaseModel):
    """Request model for deployment information."""

    address: str = Field(..., description="Contract address for deployment info")


class DeploymentInfoResponse(BaseModel):
    """Response model for deployment information."""

    address: str = Field(..., description="Contract address")
    deployer: str = Field(..., description="Deployer address")
    deployer_eoa: str = Field(..., description="Deployer EOA address")
    tx_hash: str = Field(..., description="Transaction hash")
    block_number: int = Field(..., description="Block number of deployment")


class VerificationInfoResponse(VerificationDetails):
    """Response model for contract verification information."""


class ScorecardResponse(BaseModel):
    repo_info: str
    source: str
    score: float
    date: str
    checks: List[dict]


class ProxyInfoResponse(ProxyInfo):
    """Response model for proxy information."""

    address: str = Field(..., description="Contract address")


class PermissionsInfoResponse(PermissionsInfo):
    """Response model for permissioned functions of a contract."""

    address: str = Field(..., description="Contract address")
