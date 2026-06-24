from functools import lru_cache
from typing import Any, Mapping

from crystal_clear import CrystalClear

from src.api.core.config import get_eth_node_url, settings
from src.api.integrations.risk_engine import RiskEngine
from src.api.schemas.analysis import RiskAnalysis
from src.api.services.first_time_cache import FirstInteractionCache
from src.api.services.verification_cache import (
    AllowlistedContractVerificationCache,
    ContractVerificationCache,
)


class CrystalClearRiskEngine(RiskEngine):
    """Concrete adapter that delegates to the Crystal Clear SDK."""

    def __init__(self) -> None:
        self._verification_cache = AllowlistedContractVerificationCache(
            ContractVerificationCache()
        )
        self._first_time_cache = FirstInteractionCache()
        self._client = CrystalClear(
            url=get_eth_node_url(),
            allium_api_key=settings.allium_api_key,
            etherscan_api_key=settings.etherscan_api_key,
            log_level=settings.log_level,
            verification_cache=self._verification_cache,
            first_time_cache=self._first_time_cache,
        )

    def get_risk_factors(
        self,
        address: str,
        scope: str,
        from_block: str | None = None,
        to_block: str | None = None,
        blocks: int = 5,
    ) -> RiskAnalysis:
        raw = self._client.get_risk_factors(
            address,
            scope=scope,
            from_block=from_block,
            to_block=to_block,
            blocks=blocks,
        )
        return RiskAnalysis.model_validate(raw.model_dump())

    def simulate_and_check(
        self,
        call_object: Mapping[str, Any],
        block_tag: str | int = "latest",
        from_block: str | int | None = None,
        to_block: str | int | None = None,
        latest_offset: int | None = None,
    ) -> dict[str, Any]:
        return self._client.simulate_and_check(
            dict(call_object),
            block_tag=block_tag,
            from_block=from_block,
            to_block=to_block,
            latest_offset=latest_offset,
        )

    def simulate_from_tx(
        self,
        tx_hash: str,
        root_contract: str | None = None,
        from_block: str | int | None = None,
        to_block: str | int | None = None,
        latest_offset: int | None = None,
    ) -> dict[str, Any]:
        return self._client.simulate_from_tx(
            tx_hash,
            root_contract=root_contract,
            from_block=from_block,
            to_block=to_block,
            latest_offset=latest_offset,
        )

    def get_transaction(self, tx_hash: str) -> dict[str, Any]:
        sc = self._client.simulation_collector
        if sc is None:
            raise ValueError("SimulationCollector is not initialized.")
        from hexbytes import HexBytes

        tx = sc.w3.eth.get_transaction(HexBytes(tx_hash))
        return dict(tx)


@lru_cache(maxsize=1)
def get_risk_engine() -> RiskEngine:
    """Lazy singleton used by FastAPI dependency injection."""
    return CrystalClearRiskEngine()
