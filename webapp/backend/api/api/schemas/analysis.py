from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from crystal_clear.traces.models import CallGraph

class ContractDependenciesRequest(BaseModel):
    """Request model for contract dependencies analysis."""

    address: str = Field(..., description="Contract address to analyze")
    from_block: Optional[str] = Field(None, description="Start block")
    to_block: Optional[str] = Field(None, description="End block")


class ContractDependenciesResponse(CallGraph):
    """Response model for contract dependencies analysis."""


class ContractRiskRequest(BaseModel):
    """Request model for contract risk analysis."""

    address: str = Field(..., description="Contract address to analyze")


class ContractRiskResponse(BaseModel):
    """Response model for contract risk analysis."""

    address: str
    risk_factors: Dict[str, Any] = Field(
        ..., description="Detailed risk factors"
    )

