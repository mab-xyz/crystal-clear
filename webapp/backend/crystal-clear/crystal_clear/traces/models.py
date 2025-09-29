from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator
from web3 import Web3


class CallEdge(BaseModel):
    """Model representing a call edge between contracts."""

    source: str = Field(..., description="Caller contract address")
    target: str = Field(..., description="Target contract address")
    types: Dict[str, int] = Field(
        default_factory=dict, description="Call type frequencies"
    )

    @field_validator("source", "target", mode="before")
    @classmethod
    def validate_and_normalize_address(cls, v: str) -> str:
        """Validate and normalize Ethereum addresses."""
        if not v:
            raise ValueError("Address cannot be empty")

        try:
            return Web3.to_checksum_address(v)
        except ValueError as e:
            raise ValueError(f"Invalid Ethereum address: {v} - {e}") from e

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.model_dump()


class CallGraph(BaseModel):
    """Model representing the call graph analysis result."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    address: str = Field(..., description="Target contract address")
    from_block: int = Field(..., description="Starting block number")
    to_block: int = Field(..., description="Ending block number")
    n_nodes: int = Field(..., description="Number of unique nodes")
    nodes: Dict[str, str] = Field(..., description="Node addresses with metadata")
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
        """Validate and normalize the target address."""
        if not v:
            raise ValueError("Address cannot be empty")

        try:
            return Web3.to_checksum_address(v)
        except ValueError as e:
            raise ValueError(f"Invalid Ethereum address: {v} - {e}") from e

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = self.model_dump()
        data["edges"] = [edge.to_dict() for edge in self.edges]
        return data
