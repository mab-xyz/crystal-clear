import logging
from typing import Any, Dict, Iterable, List, Optional, Protocol, Set

from web3 import Web3

from pydantic import BaseModel, Field

from crystal_clear.clients import AlliumClient, EtherscanClient, SourcifyClient
from crystal_clear.code_analyzer import (
    Analyzer,
    PermissionsInfo,
    ProxyInfo,
    Risk,
    RiskFactors,
)
from crystal_clear.traces import CallGraph, TraceCollector, SimulationCollector


class DependencyRisk(Risk):
    address: str = Field(..., description="Contract address of the dependency")
    dependency_depth: int = Field(
        ..., description="Depth of the dependency chain"
    )


class RiskAnalysis(BaseModel):
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

    def to_dict(self) -> Dict:
        return {
            "root_address": self.root_address,
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "aggregated_risks": self.aggregated_risks.to_dict(),
        }


class VerificationCache(Protocol):
    """Minimal protocol for pluggable verification caches."""

    def get(self, address: str) -> Optional[dict]: ...


class FirstTimeCache(Protocol):
    """Protocol describing first-time interaction caches."""

    def get(
        self,
        from_address: str,
        to_address: str,
        from_block: int,
        to_block: int,
        latest_offset: Optional[int],
    ) -> Optional[bool]: ...

    def set(
        self,
        from_address: str,
        to_address: str,
        from_block: int,
        to_block: int,
        latest_offset: Optional[int],
        is_first_time: bool,
        ttl_seconds: Optional[int] = None,
    ) -> None: ...

    def set(
        self, address: str, payload: dict, ttl_seconds: Optional[int] = None
    ) -> None: ...


class CrystalClear:
    def __init__(
        self,
        url: str,
        allium_api_key: str = None,
        etherscan_api_key: str = None,
        log_level: str = "INFO",
        verification_cache: Optional[VerificationCache] = None,
        first_time_cache: Optional[FirstTimeCache] = None,
    ):
        """
        Wrapper class for CrystalClear library.

        Parameters:
        -----------
        url : str
            URL of the Ethereum node for TraceCollector.
        allium_api_key : str, optional
            API key for AlliumClient.
        etherscan_api_key : str, optional
            API key for EtherscanClient.

        Raises:
        -------
        ValueError:
            If url is not provided.
        """
        self.log_level = log_level.upper()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(getattr(logging, self.log_level))
        self.trace_collector = (
            TraceCollector(url, log_level=self.log_level) if url else None
        )
        self.simulation_collector = (
            SimulationCollector(url, log_level=self.log_level) if url else None
        )
        self.allium_client = (
            AlliumClient(allium_api_key, log_level=self.log_level)
            if allium_api_key
            else None
        )
        self.etherscan_key = etherscan_api_key
        self.sourcify_client = SourcifyClient(log_level=self.log_level)
        self.etherscan_client = (
            EtherscanClient(etherscan_api_key, log_level=self.log_level)
            if etherscan_api_key
            else None
        )
        self.verification_cache = verification_cache
        self.first_time_cache = first_time_cache
        # First-time checks rely on on-chain history via trace_filter

    @staticmethod
    def _normalize_address(address: str | None) -> Optional[str]:
        if not address:
            return None
        addr = address.strip()
        if not addr:
            return None
        lower = addr.lower()
        if not lower.startswith("0x"):
            return None
        return lower

    def get_dependencies(
        self,
        address: str,
        from_block: str = None,
        to_block: str = None,
        blocks: int = 5,
    ) -> CallGraph:
        if not self.trace_collector:
            raise ValueError(
                "TraceCollector is not initialized. Please provide a url."
            )

        callgraph = self.trace_collector.get_call_graph(
            address, from_block, to_block, blocks=blocks
        )

        return callgraph

    def get_dependencies_full(
        self,
        address: str,
        from_block: str = None,
        to_block: str = None,
        blocks: int = 5,
    ) -> CallGraph:
        if not self.trace_collector:
            raise ValueError(
                "TraceCollector is not initialized. Please provide a url."
            )

        callgraph = self.trace_collector.get_call_graph(
            address, from_block, to_block, blocks=blocks
        )

        if self.allium_client:
            addresses = callgraph.nodes.keys()
            labels = self.allium_client.get_labels(addresses)
            if labels:
                for addr in addresses:
                    if addr.lower() not in labels:
                        labels[addr] = addr
                callgraph.nodes = labels
        return callgraph

    def get_proxy_info(self, address: str) -> ProxyInfo:
        if not self.etherscan_key:
            raise ValueError(
                "EtherscanClient is not initialized. Please provide an etherscan_api_key."
            )

        analyzer = Analyzer(self.etherscan_key, address)
        analysis = analyzer.get_proxy_info()
        return analysis

    def get_permissions_info(self, address: str) -> PermissionsInfo:
        if not self.etherscan_key:
            raise ValueError(
                "EtherscanClient is not initialized. Please provide an etherscan_api_key."
            )

        analyzer = Analyzer(self.etherscan_key, address)
        permissions = analyzer.get_permissions_info()
        return permissions

    def _get_cached_verification(
        self, address: str, normalized: Optional[str] = None
    ) -> Optional[dict]:
        if not self.verification_cache:
            return None
        key = normalized or self._normalize_address(address)
        if not key:
            return None
        try:
            return self.verification_cache.get(key)
        except Exception as exc:  # cache failures should not break flow
            self.logger.debug(
                "Verification cache lookup failed for %s: %s", address, exc
            )
            return None

    def _store_cached_verification(
        self,
        address: str,
        payload: dict,
        normalized: Optional[str] = None,
    ) -> None:
        if not self.verification_cache:
            return
        key = normalized or self._normalize_address(address)
        if not key:
            return
        try:
            self.verification_cache.set(key, payload)
        except Exception as exc:
            self.logger.debug(
                "Verification cache store failed for %s: %s", address, exc
            )

    def _verification_details(self, address: str) -> dict:
        normalized = self._normalize_address(address)
        cached = self._get_cached_verification(address, normalized=normalized)
        if cached:
            return cached

        return self._refresh_verification_details(address, normalized)

    def _refresh_verification_details(
        self, address: str, normalized: Optional[str] = None
    ) -> dict:
        target = (
            normalized or self._normalize_address(address) or address.lower()
        )
        response = self.sourcify_client.check_contract_verified(target)
        if (
            hasattr(response, "verification")
            and getattr(response, "verification") == "not-verified"
            and self.etherscan_client is not None
        ):
            response = self.etherscan_client.check_contract_verified(target)

        payload: Dict[str, Any] = (
            response.model_dump()
            if hasattr(response, "model_dump")
            else dict(response)
        )
        self._store_cached_verification(
            address, payload, normalized=normalized
        )
        return payload

    def _batch_verification_details(
        self, addresses: Set[str]
    ) -> dict[str, dict]:
        if not addresses:
            return {}
        normalized_map: dict[str, str] = {}
        for addr in addresses:
            norm = self._normalize_address(addr)
            if norm:
                normalized_map[norm] = addr

        if not normalized_map:
            return {}

        cached: dict[str, dict] = {}
        if self.verification_cache:
            try:
                cached = self.verification_cache.get_many(
                    normalized_map.keys()
                )
            except Exception as exc:
                self.logger.debug(
                    "Verification cache batch fetch failed: %s", exc
                )
                cached = {}

        results: dict[str, dict] = dict(cached)
        missing = [norm for norm in normalized_map if norm not in results]
        for norm in missing:
            addr = normalized_map[norm]
            payload = self._refresh_verification_details(addr, normalized=norm)
            results[norm] = payload
        return results

    def _get_cached_first_time(
        self,
        from_addr: str,
        target: str,
        from_block: int,
        to_block: int,
        latest_offset: Optional[int],
    ) -> Optional[bool]:
        if not self.first_time_cache:
            return None
        try:
            return self.first_time_cache.get(
                from_addr, target, from_block, to_block, latest_offset
            )
        except Exception as exc:
            self.logger.debug(
                "First-time cache lookup failed for %s -> %s: %s",
                from_addr,
                target,
                exc,
            )
            return None

    def _store_cached_first_time(
        self,
        from_addr: str,
        target: str,
        from_block: int,
        to_block: int,
        latest_offset: Optional[int],
        is_first_time: bool,
    ) -> None:
        if not self.first_time_cache:
            return
        try:
            self.first_time_cache.set(
                from_addr,
                target,
                from_block,
                to_block,
                latest_offset,
                is_first_time,
            )
        except Exception as exc:
            self.logger.debug(
                "First-time cache store failed for %s -> %s: %s",
                from_addr,
                target,
                exc,
            )

    def _resolve_block_bounds(
        self,
        from_block: str | int | None,
        to_block: str | int | None,
        latest_offset: int | None,
    ) -> tuple[int, int, str, str]:
        w3 = self.trace_collector.w3
        try:
            latest_num = int(w3.eth.block_number)
        except Exception:
            latest_num = 0

        if to_block is None or (
            isinstance(to_block, str) and to_block == "latest"
        ):
            to_num = latest_num
        else:
            if isinstance(to_block, int):
                to_num = to_block
            elif isinstance(to_block, str) and to_block.startswith("0x"):
                to_num = int(to_block, 16)
            elif isinstance(to_block, str) and to_block.isdigit():
                to_num = int(to_block)
            else:
                raise ValueError(f"Invalid to_block: {to_block}")

        if from_block is None:
            if latest_offset is None or int(latest_offset) <= 0:
                from_num = 0
            else:
                to_num_safe = max(0, to_num)
                from_num = max(0, to_num_safe - int(latest_offset))
        else:
            if isinstance(from_block, int):
                from_num = from_block
            elif isinstance(from_block, str) and from_block.startswith("0x"):
                from_num = int(from_block, 16)
            elif isinstance(from_block, str) and from_block.isdigit():
                from_num = int(from_block)
            else:
                raise ValueError(f"Invalid from_block: {from_block}")

        from_num = max(0, from_num)
        to_num = max(0, to_num)
        return from_num, to_num, hex(from_num), hex(to_num)

    def _trace_first_time(
        self,
        from_addr: str,
        target: str,
        from_block_hex: str,
        to_block_hex: str,
    ) -> bool:
        w3 = self.trace_collector.w3
        try:
            sender = w3.to_checksum_address(from_addr)
            dst = w3.to_checksum_address(target)
        except Exception:
            return True

        exists = self.trace_collector.has_from_to_interaction(
            from_block_hex, to_block_hex, sender, dst
        )
        return not exists

    def _batch_first_time(
        self,
        from_addr: str,
        targets: Set[str],
        from_block: str | int | None,
        to_block: str | int | None,
        latest_offset: int | None,
    ) -> dict[str, bool]:
        if not targets:
            return {}

        if not self.trace_collector:
            return {}

        normalized_from = self._normalize_address(from_addr)
        target_map: dict[str, str] = {}
        for addr in targets:
            norm = self._normalize_address(addr)
            if norm:
                target_map[norm] = addr

        if not target_map or not normalized_from:
            return {norm: True for norm in target_map}

        from_num, to_num, from_block_hex, to_block_hex = (
            self._resolve_block_bounds(from_block, to_block, latest_offset)
        )
        offset_val = int(latest_offset) if latest_offset is not None else None

        cached: dict[tuple, bool] = {}
        if self.first_time_cache:
            entries = [
                (normalized_from, norm, from_num, to_num, offset_val)
                for norm in target_map
            ]
            try:
                cached = self.first_time_cache.get_many(entries)
            except Exception as exc:
                self.logger.debug(
                    "First-time cache batch fetch failed: %s", exc
                )
                cached = {}

        results: dict[str, bool] = {}
        for key, value in cached.items():
            _, target_norm, *_ = key
            results[target_norm] = value

        missing = [norm for norm in target_map if norm not in results]
        for norm in missing:
            addr = target_map[norm]
            result = self._trace_first_time(
                normalized_from, addr, from_block_hex, to_block_hex
            )
            results[norm] = result
            self._store_cached_first_time(
                normalized_from,
                norm,
                from_num,
                to_num,
                offset_val,
                result,
            )

        return results

    def _is_first_time_onchain(
        self,
        from_addr: str,
        target: str,
        from_block: str | int | None = None,
        to_block: str | int | None = None,
        latest_offset: int | None = None,
    ) -> bool:
        """
        Check if there has been any on-chain interaction from from_addr to target
        within the provided block range. Defaults to full history if bounds omitted.
        Returns True if no prior interaction is found.
        """
        if not self.trace_collector:
            raise ValueError(
                "TraceCollector is not initialized. Please provide a node url."
            )

        from_num, to_num, from_block_hex, to_block_hex = (
            self._resolve_block_bounds(from_block, to_block, latest_offset)
        )
        cached = self._get_cached_first_time(
            from_addr, target, from_num, to_num, latest_offset
        )
        if cached is not None:
            return cached

        result = self._trace_first_time(
            from_addr, target, from_block_hex, to_block_hex
        )
        self._store_cached_first_time(
            from_addr, target, from_num, to_num, latest_offset, result
        )
        return result

    def first_time(
        self,
        from_addr: str,
        target: str,
        from_block: str | int | None = None,
        to_block: str | int | None = None,
        latest_offset: int | None = None,
    ) -> bool:
        """
        Check if it's the first time on-chain interaction between from_addr -> target.
        Scans chain history using trace_filter within the provided block range.
        """
        return self._is_first_time_onchain(
            from_addr,
            target,
            from_block,
            to_block,
            latest_offset=latest_offset,
        )

    def simulate_and_check(
        self,
        call_object: dict,
        block_tag: str | int = "latest",
        from_block: str | int | None = None,
        to_block: str | int | None = None,
        latest_offset: int | None = None,
        # allium_query_id: str | None = None,  # reserved for future use
        full_tree: bool = True,
        include_root: bool = True,
    ) -> dict:
        if not self.simulation_collector:
            raise ValueError(
                "SimulationCollector is not initialized. Please provide a url."
            )
        edges = self.simulation_collector.get_edges_from_simulation(
            call_object, block_tag=block_tag
        )
        from_addr = call_object.get("from", "")
        results: dict[str, dict] = {}
        # Always include the root callee (depth=0) if present
        root_addr = call_object.get("to", "") or ""
        # Normalize root to checksum if possible
        try:
            if root_addr:
                root_addr = Web3.to_checksum_address(root_addr)
        except Exception:
            pass
        # Skip root address if it has no bytecode (EOA — not a smart contract).
        # A plain ETH transfer to an EOA must not appear in risk results as an
        # "unverified" entity: there is no contract code to check.
        if root_addr and not self.simulation_collector._validate_contract(
            root_addr, "latest"
        ):
            root_addr = ""
        # Compute depths for all nodes using existing helper
        try:
            nodes = set()
            if root_addr:
                nodes.add(root_addr)
            for e in edges:
                nodes.add(e.source)
                nodes.add(e.target)
            depths = self.simulation_collector.get_depths(
                nodes, edges, root_addr.lower() if root_addr else ""
            )
        except Exception:
            depths = {}
        target_addresses: Set[str] = set()
        if root_addr:
            target_addresses.add(root_addr)
        for e in edges:
            target_addresses.add(e.target)

        verification_map = self._batch_verification_details(target_addresses)

        first_time_map = self._batch_first_time(
            from_addr,
            target_addresses,
            from_block=from_block,
            to_block=to_block,
            latest_offset=latest_offset,
        )

        if root_addr:
            root_norm = root_addr.lower()
            first_time_val = first_time_map.get(root_norm)
            if first_time_val is None:
                first_time_val = self.first_time(
                    from_addr,
                    root_addr,
                    from_block=from_block,
                    to_block=to_block,
                    latest_offset=latest_offset,
                )
            verification = verification_map.get(root_norm)
            if verification is None:
                verification = self._verification_details(root_addr)
            info = {
                "first_time": first_time_val,
                "verification": verification,
                "depth": 0,
            }
            results[root_addr] = info
        for edge in edges:
            # Edge targets are checksum-normalized by model validators
            addr = edge.target
            # Skip duplicate entry if edge target is the root (case-insensitive)
            try:
                if root_addr and addr.lower() == root_addr.lower():
                    continue
            except Exception:
                pass
            norm = addr.lower()
            first_time_val = first_time_map.get(norm)
            if first_time_val is None:
                first_time_val = self.first_time(
                    from_addr,
                    addr,
                    from_block=from_block,
                    to_block=to_block,
                    latest_offset=latest_offset,
                )
            verification = verification_map.get(norm)
            if verification is None:
                verification = self._verification_details(addr)
            info = {
                "first_time": first_time_val,
                "verification": verification,
            }
            # Populate depth from computed depths map; fallback to None
            try:
                info["depth"] = depths.get(addr.lower(), -1)
            except Exception:
                info["depth"] = None
            if hasattr(edge, "types") and isinstance(edge.types, dict):
                info["types"] = edge.types
            results[addr] = info
        return results

    def simulate_from_tx(
        self,
        tx_hash: str,
        root_contract: str | None = None,
        from_block: str | int | None = None,
        to_block: str | int | None = None,
        latest_offset: int | None = None,
        full_tree: bool = True,
        include_root: bool = True,
    ) -> dict:
        if not self.simulation_collector:
            raise ValueError(
                "SimulationCollector is not initialized. Please provide a url."
            )

        edges = self.simulation_collector.get_edges_from_tx(
            tx_hash, root_contract=root_contract
        )

        # Determine sender (from EOA) for first-time checks
        from_addr = ""
        try:
            # Prefer transaction object for reliability
            tx = self.simulation_collector.w3.eth.get_transaction(tx_hash)
            from_addr = (
                tx.get("from", "")
                if isinstance(tx, dict)
                else getattr(tx, "from", "")
            )
        except Exception:
            try:
                trace = self.simulation_collector._get_calls_from_tx(tx_hash)
                from_addr = trace.get("from", "") if trace else ""
            except Exception:
                from_addr = ""

        # For on-chain mode without explicit to_block, cap range to before this tx's block
        if to_block is None:
            try:
                receipt = (
                    self.simulation_collector.w3.eth.get_transaction_receipt(
                        tx_hash
                    )
                )
                blk = getattr(receipt, "blockNumber", None) or receipt.get(
                    "blockNumber"
                )
                if isinstance(blk, int) and blk > 0:
                    to_block = blk - 1
            except Exception:
                pass

        results: dict[str, dict] = {}
        # Always include the root callee (tx.to or provided root_contract)
        root_addr = root_contract
        if not root_addr:
            try:
                # fall back to tx.to
                tx = self.simulation_collector.w3.eth.get_transaction(tx_hash)
                root_addr = (
                    tx.get("to", "")
                    if isinstance(tx, dict)
                    else getattr(tx, "to", "")
                )
            except Exception:
                root_addr = ""
        # Normalize root to checksum if possible
        try:
            if root_addr:
                root_addr = Web3.to_checksum_address(root_addr)
        except Exception:
            pass
        # Skip root address if it has no bytecode (EOA — not a smart contract).
        if root_addr and not self.simulation_collector._validate_contract(
            root_addr, "latest"
        ):
            root_addr = ""
        # Compute depths for all nodes
        try:
            nodes = set()
            if root_addr:
                nodes.add(root_addr)
            for e in edges:
                nodes.add(e.source)
                nodes.add(e.target)
            depths = self.simulation_collector.get_depths(
                nodes, edges, root_addr.lower() if root_addr else ""
            )
        except Exception:
            depths = {}
        target_addresses: Set[str] = set()
        if root_addr:
            target_addresses.add(root_addr)
        for e in edges:
            target_addresses.add(e.target)

        verification_map = self._batch_verification_details(target_addresses)
        first_time_map = self._batch_first_time(
            from_addr,
            target_addresses,
            from_block=from_block,
            to_block=to_block,
            latest_offset=latest_offset,
        )

        if root_addr:
            root_norm = root_addr.lower()
            first_time_val = first_time_map.get(root_norm)
            if first_time_val is None:
                first_time_val = self.first_time(
                    from_addr,
                    root_addr,
                    from_block=from_block,
                    to_block=to_block,
                    latest_offset=latest_offset,
                )
            verification = verification_map.get(root_norm)
            if verification is None:
                verification = self._verification_details(root_addr)
            info = {
                "first_time": first_time_val,
                "verification": verification,
                "depth": 0,
            }
            results[root_addr] = info
        for edge in edges:
            addr = edge.target
            # Skip duplicate entry if edge target is the root (case-insensitive)
            try:
                if root_addr and addr.lower() == root_addr.lower():
                    continue
            except Exception:
                pass
            norm = addr.lower()
            first_time_val = first_time_map.get(norm)
            if first_time_val is None:
                first_time_val = self.first_time(
                    from_addr,
                    addr,
                    from_block=from_block,
                    to_block=to_block,
                    latest_offset=latest_offset,
                )
            verification = verification_map.get(norm)
            if verification is None:
                verification = self._verification_details(addr)
            info = {
                "first_time": first_time_val,
                "verification": verification,
            }
            try:
                info["depth"] = depths.get(addr.lower(), -1)
            except Exception:
                info["depth"] = None
            if hasattr(edge, "types") and isinstance(edge.types, dict):
                info["types"] = edge.types
            results[addr] = info
        return results

    def get_risk_factors(
        self,
        address: str,
        scope: str,
        from_block: str = None,
        to_block: str = None,
        blocks: int = 5,
    ) -> RiskAnalysis:
        if scope not in ["single", "supply-chain"]:
            raise ValueError(
                "Scope must be either 'single' or 'supply-chain'."
            )
        if not self.etherscan_key:
            raise ValueError(
                "EtherscanClient is not initialized. Please provide an etherscan_api_key."
            )
        if scope == "single":
            analyzer = Analyzer(
                self.etherscan_key, address, log_level=self.log_level
            )
            risk = analyzer.risk()
            dependency_risk = DependencyRisk(
                address=address, dependency_depth=0, **risk.model_dump()
            )
            aggregated_risk = Risk(
                verified=risk.verified, risk_factors=risk.risk_factors
            )
            analysis = RiskAnalysis(
                root_address=address,
                dependencies=[dependency_risk],
                aggregated_risks=aggregated_risk,
            )
            return analysis

        else:
            if not self.trace_collector:
                raise ValueError(
                    "TraceCollector is not initialized. Please provide a node url."
                )
            callgraph: CallGraph = self.get_dependencies(
                address, from_block, to_block, blocks=blocks
            )
            aggregated = Risk(
                verified=True,
                risk_factors=RiskFactors(
                    upgradeability=False, permissioned=False
                ),
            )
            analysis = RiskAnalysis(
                root_address=address,
                from_block=callgraph.from_block,
                to_block=callgraph.to_block,
                dependencies=[],
                aggregated_risks=aggregated,
            )
            for addr in callgraph.nodes.keys():
                try:
                    analyzer = Analyzer(
                        self.etherscan_key, addr, log_level=self.log_level
                    )
                    risk: Risk = analyzer.risk()
                    dependency_risk = DependencyRisk(
                        address=addr,
                        dependency_depth=callgraph.dependency_depths.get(
                            addr.lower(), 0
                        ),
                        **risk.model_dump(),
                    )
                    analysis.dependencies.append(dependency_risk)
                    if risk.verified == "not-verified":
                        analysis.aggregated_risks.verified = False
                    if risk.risk_factors.upgradeability:
                        analysis.aggregated_risks.risk_factors.upgradeability = True
                    if risk.risk_factors.permissioned:
                        analysis.aggregated_risks.risk_factors.permissioned = (
                            True
                        )
                except Exception as e:
                    print(f"Error analyzing {addr}: {e}")
            return analysis
