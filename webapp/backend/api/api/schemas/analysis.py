from typing import Any, Dict, List, Optional

from crystal_clear.code_analyzer import RiskFactors
from crystal_clear.traces.models import CallGraph
from pydantic import BaseModel, Field


class AdditionalRiskFactors(RiskFactors):
    repository: bool = Field(None, description="Contract is linked to a repository")
    audits: bool = Field(None, description="Contract has associated audits")
    scorecard: float | None = Field(None, description="Contract has a scorecard")

    def to_dict(self):
        return super().to_dict()

    def __str__(self):
        str_parts = [super().__str__()]
        if not self.repository:
            str_parts.append("Contract is not linked to a repository.")
        if not self.audits:
            str_parts.append("Contract has no associated audits.")
        if self.scorecard is not None and self.scorecard < 5:
            str_parts.append(f"Contract has a low scorecard: {self.scorecard}.")

        return (
            " ".join(str_parts)
            if str_parts
            else "No additional risk factors identified."
        )


class AdditionalRisk(BaseModel):
    verified: bool = Field(..., description="Indicates if the contract is verified")
    risk_factors: AdditionalRiskFactors = Field(
        ..., description="Identified risk factors of the contract"
    )
    details: Dict[str, Any] | None = Field(
        default=None, description="Detailed analysis results"
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class AdditionalDependencyRisk(AdditionalRisk):
    address: str = Field(..., description="Contract address of the dependency")
    dependency_depth: int = Field(..., description="Depth of the dependency chain")


class RiskAnalysisResponse(BaseModel):
    """Response model for contract risk analysis."""

    root_address: str = Field(..., description="Root contract address")
    from_block: int | None = Field(
        default=None, description="Starting block number for the analysis"
    )
    to_block: int | None = Field(
        default=None, description="Ending block number for the analysis"
    )
    dependencies: List[AdditionalDependencyRisk] = Field(
        ..., description="List of analyzed dependencies with risk factors"
    )
    aggregated_risks: AdditionalRisk = Field(
        ..., description="Aggregated risk factors across all dependencies"
    )

    def to_dict(self) -> Dict:
        return {
            "root_address": self.root_address,
            "from_block": self.from_block,
            "to_block": self.to_block,
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "aggregated_risks": self.aggregated_risks.to_dict(),
        }


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
    from_block: Optional[str] = Field(None, description="Start block")
    to_block: Optional[str] = Field(None, description="End block")


class SimulationRequest(BaseModel):
    """Request model for pre-sign transaction simulation."""

    from_addr: str = Field(..., description="EOA sender address")
    to_addr: Optional[str] = Field(None, description="Target contract address")
    data: Optional[str] = Field("0x", description="Calldata hex")
    value: Optional[str] = Field("0x0", description="Wei value (hex)")
    gas: Optional[str] = Field(None, description="Gas limit (hex)")
    maxFeePerGas: Optional[str] = Field(None, description="maxFeePerGas (hex)")
    maxPriorityFeePerGas: Optional[str] = Field(
        None, description="maxPriorityFeePerGas (hex)"
    )
    tx_type: Optional[str] = Field(None, description="Tx type, e.g., 0x2")
    block_tag: Optional[str] = Field("latest", description="Block tag or number")
    allium_query_id: Optional[str] = Field(
        None, description="Allium query ID for first-time interaction"
    )


class SimulationResultItem(BaseModel):
    address: str
    first_time: bool
    verification: dict | None = None


class SimulationResponse(BaseModel):
    results: List[SimulationResultItem]
