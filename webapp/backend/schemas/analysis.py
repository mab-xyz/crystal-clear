from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ContractDependenciesRequest(BaseModel):
    """Request model for contract dependencies analysis."""

    address: str = Field(..., description="Contract address to analyze")
    from_block: Optional[str] = Field(None, description="Start block")
    to_block: Optional[str] = Field(None, description="End block")


class ContractDependenciesResponse(BaseModel):
    """Response model for contract dependencies analysis."""

    address: str
    from_block: int
    to_block: int
    edges: List[Dict[str, Any]]


class ContractRiskRequest(BaseModel):
    """Request model for contract risk analysis."""

    address: str = Field(..., description="Contract address to analyze")


class ContractRiskResponse(BaseModel):
    """Response model for contract risk analysis."""

    address: str
    risk_score: float = Field(
        ..., ge=0, le=100, description="Risk score from 0 to 100"
    )
    risk_factors: Dict[str, Any] = Field(
        ..., description="Detailed risk factors"
    )
