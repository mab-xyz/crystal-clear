from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from web3 import Web3


class RiskFactors(BaseModel):
    """Risk markers mirrored from the Crystal Clear models."""

    upgradeability: bool | None = Field(
        None, description="Contract is upgradeable"
    )
    permissioned: bool | None = Field(
        None, description="Contract has permissioned functions"
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def __str__(self) -> str:
        str_parts: List[str] = []
        if self.upgradeability:
            str_parts.append("Contract is upgradeable.")
        if self.permissioned:
            str_parts.append("Contract has permissioned functions.")

        return (
            " ".join(str_parts) if str_parts else "No risk factors identified."
        )


class CallEdge(BaseModel):
    """Call edge between contracts."""

    source: str = Field(..., description="Caller contract address")
    target: str = Field(..., description="Target contract address")
    types: Dict[str, int] = Field(
        default_factory=dict, description="Call type frequencies"
    )

    @field_validator("source", "target", mode="before")
    @classmethod
    def validate_and_normalize_address(cls, v: str) -> str:
        if not v:
            raise ValueError("Address cannot be empty")

        try:
            return Web3.to_checksum_address(v)
        except ValueError as e:
            raise ValueError(f"Invalid Ethereum address: {v} - {e}") from e

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class CallGraph(BaseModel):
    """Result of dependency network analysis."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    address: str = Field(..., description="Target contract address")
    from_block: int = Field(..., description="Starting block number")
    to_block: int = Field(..., description="Ending block number")
    n_nodes: int = Field(..., description="Number of unique nodes")
    nodes: Dict[str, str] = Field(
        ..., description="Node metadata mapped by address"
    )
    edges: List[CallEdge] = Field(..., description="Call edges between nodes")
    dependency_depths: Dict[str, int] = Field(
        ..., description="Depth of each dependency from the root contract"
    )
    n_matching_transactions: int = Field(
        ..., description="Number of matching transactions"
    )

    @field_validator("address", mode="before")
    @classmethod
    def validate_and_normalize_address(cls, v: str) -> str:
        if not v:
            raise ValueError("Address cannot be empty")

        try:
            return Web3.to_checksum_address(v)
        except ValueError as e:
            raise ValueError(f"Invalid Ethereum address: {v} - {e}") from e

    def to_dict(self) -> Dict[str, Any]:
        data = self.model_dump()
        data["edges"] = [edge.to_dict() for edge in self.edges]
        return data


class Risk(BaseModel):
    """Baseline risk information for a contract."""

    verified: bool = Field(
        ..., description="Indicates if the contract is verified"
    )
    risk_factors: RiskFactors = Field(
        ..., description="Identified risk factors of the contract"
    )
    details: Dict[str, Any] | None = Field(
        default=None, description="Detailed analysis results"
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class DependencyRisk(Risk):
    address: str = Field(..., description="Contract address of the dependency")
    dependency_depth: int = Field(
        ..., description="Depth of the dependency chain"
    )


class RiskAnalysis(BaseModel):
    """Risk information returned by the dependency analyzer."""

    root_address: str = Field(..., description="Root contract address")
    from_block: int | None = Field(
        default=None, description="Starting block number for the analysis"
    )
    to_block: int | None = Field(
        default=None, description="Ending block number for the analysis"
    )
    dependencies: List[DependencyRisk] = Field(
        ..., description="List of analyzed dependencies with risk factors"
    )
    aggregated_risks: Risk = Field(
        ..., description="Aggregated risk factors across all dependencies"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_address": self.root_address,
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "aggregated_risks": self.aggregated_risks.to_dict(),
        }


class AdditionalRiskFactors(RiskFactors):
    repository: bool = Field(
        None, description="Contract is linked to a repository"
    )
    audits: bool = Field(None, description="Contract has associated audits")
    scorecard: float | None = Field(
        None, description="Contract has a scorecard"
    )

    def to_dict(self):
        return super().to_dict()

    def __str__(self):
        str_parts = [super().__str__()]
        if not self.repository:
            str_parts.append("Contract is not linked to a repository.")
        if not self.audits:
            str_parts.append("Contract has no associated audits.")
        if self.scorecard is not None and self.scorecard < 5:
            str_parts.append(
                f"Contract has a low scorecard: {self.scorecard}."
            )

        return (
            " ".join(str_parts)
            if str_parts
            else "No additional risk factors identified."
        )


class AdditionalRisk(BaseModel):
    verified: bool = Field(
        ..., description="Indicates if the contract is verified"
    )
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
    dependency_depth: int = Field(
        ..., description="Depth of the dependency chain"
    )


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
    to_addr: str = Field(..., description="Target contract address")
    data: str = Field("0x", description="Calldata hex")
    value: Optional[str] = Field("0x0", description="Wei value (hex)")
    gas: Optional[str] = Field(None, description="Gas limit (hex)")
    gasPrice: Optional[str] = Field(None, description="Gas price (hex)")
    maxFeePerGas: Optional[str] = Field(None, description="maxFeePerGas (hex)")
    maxPriorityFeePerGas: Optional[str] = Field(
        None, description="maxPriorityFeePerGas (hex)"
    )
    tx_type: Optional[str] = Field(None, description="Tx type, e.g., 0x2")
    block_tag: Optional[str] = Field(
        "latest", description="Block tag or number"
    )
    # allium_query_id: Optional[str] = Field(
    #     None, description="Allium query ID for first-time interaction"
    # )
    latest_offset: Optional[int] = Field(
        100,
        description="Limit first-time checks to N latest blocks (performance control)",
    )
    from_block: Optional[str] = Field(
        None, description="Lower bound block for first-time checks"
    )
    to_block: Optional[str] = Field(
        None, description="Upper bound block for first-time checks"
    )
    interaction_types: Optional[
        List[
            Literal[
                "sender_direct",
                "sender_transitive",
                "contract_direct",
                "contract_transitive",
            ]
        ]
    ] = Field(
        None,
        description=(
            "Interaction types to evaluate. If omitted, all applicable types are used."
        ),
    )


class SimulationResultItem(BaseModel):
    """Risk analysis result for a single contract touched during the transaction."""

    address: str = Field(
        ..., description="Checksummed Ethereum address of the touched contract"
    )
    first_time: bool = Field(
        ...,
        description=(
            "True if the sender has never interacted with this contract "
            "across any of the checked interaction types"
        ),
    )
    verification: dict | None = Field(
        None,
        description=(
            "Source-code verification status from Etherscan/Sourcify "
            '(e.g. {"verification": "verified", "compiler": "solc", ...}). '
            "Null when verification data is unavailable."
        ),
    )
    depth: int | None = Field(
        None,
        description=(
            "Call depth at which this contract was reached during trace simulation "
            "(0 = direct target, 1+ = internal/delegate call)"
        ),
    )
    types: Dict[str, int] | None = Field(
        None,
        description=(
            "Map of EVM call types to their frequency for this address "
            '(e.g. {"CALL": 2, "DELEGATECALL": 1})'
        ),
    )
    interaction_first_time: Dict[str, bool] | None = Field(
        None,
        description=(
            "Per-interaction-type first-time flag. Keys are interaction types "
            "(sender_direct, sender_transitive, contract_direct, contract_transitive); "
            "values are true if this is the first recorded interaction of that type."
        ),
    )
    interaction_state: Dict[str, Literal["FOUND", "MISSING"]] | None = Field(
        None,
        description=(
            "Per-interaction-type data availability. FOUND means historical scan data "
            "exists; MISSING means no scan data is available and the result is "
            "best-effort."
        ),
    )
    is_eip7702: bool = Field(
        False,
        description="Whether this address is an EIP-7702 delegated EOA",
    )
    delegate_address: Optional[str] = Field(
        None,
        description=(
            "Delegate contract address for EIP-7702 delegated EOAs. "
            "Verification data refers to this delegate contract."
        ),
    )


class SimulationResponse(BaseModel):
    """Aggregated risk verdict for a simulated or decoded transaction."""

    status: Literal["OK", "DANGEROUS", "POTENTIAL_DANGEROUS"] = Field(
        ...,
        description=(
            "Overall risk verdict. OK = no issues found; "
            "DANGEROUS = at least one first-time or unverified contract interaction; "
            "POTENTIAL_DANGEROUS = scan data is incomplete so risk cannot be ruled out."
        ),
    )
    interaction_status: (
        Dict[
            Literal[
                "sender_direct",
                "sender_transitive",
                "contract_direct",
                "contract_transitive",
            ],
            Literal["dangerous", "ok", "not_checked", "potential_dangerous"],
        ]
        | None
    ) = Field(
        None,
        description=(
            "Per-interaction-type risk status. Each key is an interaction type and "
            "its value is one of: ok, dangerous, potential_dangerous, or not_checked."
        ),
    )
    details: List[SimulationResultItem] = Field(
        ...,
        description="Per-contract breakdown of risk signals for every address touched by the transaction",
    )
    dangerous_interaction_types: List[str] | None = Field(
        None,
        description=(
            "Interaction types that triggered the DANGEROUS verdict "
            '(e.g. ["contract_direct"]). Null when status is OK.'
        ),
    )
    danger_reason: Optional[
        Literal[
            "FIRST_TIME_INTERACTION",
            "MISSING_HISTORY",
            "UNVERIFIED",
            "EIP_7702_UNVERIFIED_DELEGATE",
        ]
    ] = Field(
        None,
        description=(
            "Root cause of a non-OK verdict. FIRST_TIME_INTERACTION = sender/contract "
            "has never called this address; MISSING_HISTORY = no historical scan data "
            "available; UNVERIFIED = contract source code is not verified on-chain; "
            "EIP_7702_UNVERIFIED_DELEGATE = the destination is an EIP-7702 delegated "
            "EOA whose delegate contract is not verified."
        ),
    )
    ok_reason: Optional[
        Literal["to EOA", "EIP-7702 delegated EOA (verified delegate)"]
    ] = Field(
        None,
        description=(
            "Reason the verdict is OK when the transaction touches no contracts. "
            "to EOA = the destination address has no bytecode (plain ETH transfer). "
            "EIP-7702 delegated EOA (verified delegate) = destination is an EIP-7702 "
            "delegated EOA whose delegate contract is verified."
        ),
    )
    ok_reason: Optional[Literal["to EOA"]] = Field(
        None,
        description=(
            "Reason the verdict is OK when the transaction touches no contracts. "
            "to EOA = the destination address has no bytecode (plain ETH transfer)."
        ),
    )


class RawTxRiskRequest(BaseModel):
    """Request model for raw signed transaction risk check."""

    raw_tx: str = Field(..., description="0x-hex of the signed transaction")
    sender_address: Optional[str] = Field(
        None,
        description=(
            "The 0x-hex address of the sender. "
            "Required if 'raw_tx' is an unsigned transaction. "
            "Ignored if 'raw_tx' is a signed transaction."
        ),
    )
    block_tag: Optional[str] = Field(
        "latest", description="Block tag or number"
    )
    latest_offset: Optional[int] = Field(
        100,
        description="Limit first-time checks to N latest blocks (performance control)",
    )
    from_block: Optional[str] = Field(
        None, description="Lower bound block for first-time checks"
    )
    to_block: Optional[str] = Field(
        None, description="Upper bound block for first-time checks"
    )
    interaction_type: Optional[
        Literal[
            "sender_direct",
            "sender_transitive",
            "contract_direct",
            "contract_transitive",
        ]
    ] = Field(
        None,
        description=(
            "Specific interaction type to evaluate. If omitted, all applicable types are used."
        ),
    )
