from typing import Literal, List, Optional

from pydantic import BaseModel, Field


class LatestBlockResponse(BaseModel):
    """Request model for contract dependencies analysis."""

    block_number: int = Field(
        ..., description="Latest block number from the Ethereum network"
    )


class DeploymentInfoRequest(BaseModel):
    """Request model for deployment information."""

    address: str = Field(
        ..., description="Contract address for deployment info"
    )


class DeploymentInfoResponse(BaseModel):
    """Response model for deployment information."""

    address: str = Field(..., description="Contract address")
    deployer: str = Field(..., description="Deployer address")
    deployer_eoa: str = Field(..., description="Deployer EOA address")
    tx_hash: str = Field(..., description="Transaction hash")
    block_number: int = Field(..., description="Block number of deployment")


class VerificationInfoResponse(BaseModel):
    """Response model for contract verification information."""

    address: str = Field(..., description="Contract address")
    verification: Literal["verified", "fully-verified", "not-verified"] = (
        Field(..., description="Verification status")
    )
    verifiedAt: str = Field(None, description="Verification date")
    is_eip7702: bool = Field(
        False,
        description="Whether address is an EIP-7702 delegated EOA",
    )
    delegate_address: Optional[str] = Field(
        None,
        description="Delegate contract address for EIP-7702 delegated EOAs",
    )


class ScorecardResponse(BaseModel):
    repo_info: str
    source: str
    score: float
    date: str
    checks: List[dict]


class ProxyInfoResponse(BaseModel):
    """Response model for proxy information."""

    address: str = Field(..., description="Proxy contract address")
    type: str = Field(..., description="Type of proxy (e.g., 'upgradable')")
    message: str = Field(
        ..., description="Additional information about the proxy"
    )


class PermissionsInfoResponse(BaseModel):
    """Response model for permissioned functions of a contract."""

    address: str = Field(..., description="Contract address")
    functions: List[str] = Field(
        ..., description="List of functions that require specific permissions"
    )
