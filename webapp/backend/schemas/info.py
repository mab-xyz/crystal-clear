from typing import Literal

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


class VerificationInfoResponse(BaseModel):
    """Response model for contract verification information."""
    address: str = Field(..., description="Contract address")
    verfication: Literal["verified", "fully-verified"] = Field(
        ..., description="Verification status"
    )
    verifiedAt: str = Field(None, description="Verification date")