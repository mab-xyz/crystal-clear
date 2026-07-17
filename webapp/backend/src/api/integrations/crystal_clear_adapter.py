from functools import lru_cache
from threading import RLock
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


class _NoFirstTimeCache:
    def get_many(self, entries):
        return {entry: False for entry in entries}

    def get(self, *_args, **_kwargs):
        return False

    def set(self, *_args, **_kwargs):
        return None


class CrystalClearRiskEngine(RiskEngine):
    """Concrete adapter that delegates to the Crystal Clear SDK."""

    def __init__(self) -> None:
        self._verification_cache = AllowlistedContractVerificationCache(
            ContractVerificationCache()
        )
        self._first_time_cache = FirstInteractionCache()
        self._simulate_lock = RLock()
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
        check_first_time: bool = True,
    ) -> dict[str, Any]:
        if check_first_time:
            return self._client.simulate_and_check(
                dict(call_object),
                block_tag=block_tag,
                from_block=from_block,
                to_block=to_block,
                latest_offset=latest_offset,
            )

        with self._simulate_lock:
            original_cache = getattr(self._client, "first_time_cache", None)
            self._client.first_time_cache = _NoFirstTimeCache()
            try:
                return self._client.simulate_and_check(
                    dict(call_object),
                    block_tag=block_tag,
                    from_block=from_block,
                    to_block=to_block,
                    latest_offset=latest_offset,
                )
            finally:
                self._client.first_time_cache = original_cache

    def simulate_and_check_with_edges(
        self,
        call_object: Mapping[str, Any],
        block_tag: str | int = "latest",
        from_block: str | int | None = None,
        to_block: str | int | None = None,
        latest_offset: int | None = None,
        check_first_time: bool = True,
    ) -> tuple[dict[str, Any], list[tuple[str, str]]]:
        collector = self._client.simulation_collector
        if collector is None:
            raise ValueError("SimulationCollector is not initialized.")

        captured_edges: list[tuple[str, str]] = []
        original_get_edges = collector.get_edges_from_simulation

        def capture_edges(*args, **kwargs):
            edges = original_get_edges(*args, **kwargs)
            captured_edges.extend((edge.source, edge.target) for edge in edges)
            return edges

        with self._simulate_lock:
            original_cache = getattr(self._client, "first_time_cache", None)
            collector.get_edges_from_simulation = capture_edges
            if not check_first_time:
                self._client.first_time_cache = _NoFirstTimeCache()
            try:
                results = self._client.simulate_and_check(
                    dict(call_object),
                    block_tag=block_tag,
                    from_block=from_block,
                    to_block=to_block,
                    latest_offset=latest_offset,
                )
            finally:
                collector.get_edges_from_simulation = original_get_edges
                self._client.first_time_cache = original_cache
        return results, captured_edges

    def get_latest_block_number(self) -> int:
        collector = self._client.simulation_collector
        if collector is None:
            raise ValueError("SimulationCollector is not initialized.")
        return int(collector.w3.eth.block_number)

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
