from typing import Protocol, Any, Mapping

from src.api.schemas.analysis import RiskAnalysis


class RiskEngine(Protocol):
    """Abstraction for any risk-analysis backend."""

    def get_risk_factors(
        self,
        address: str,
        scope: str,
        from_block: str | None = None,
        to_block: str | None = None,
        blocks: int = 5,
    ) -> RiskAnalysis:
        """Return supply-chain or single-contract risk data."""

    def simulate_and_check(
        self,
        call_object: Mapping[str, Any],
        block_tag: str | int = "latest",
        from_block: str | int | None = None,
        to_block: str | int | None = None,
        latest_offset: int | None = None,
        check_first_time: bool = True,
    ) -> dict[str, Any]:
        """Simulate calldata and return touched-contract results."""

    def simulate_from_tx(
        self,
        tx_hash: str,
        root_contract: str | None = None,
        from_block: str | int | None = None,
        to_block: str | int | None = None,
        latest_offset: int | None = None,
    ) -> dict[str, Any]:
        """Simulate an on-chain transaction by hash."""

    def get_transaction(self, tx_hash: str) -> dict[str, Any]:
        """Fetch a transaction from the chain by hash and return its fields."""
