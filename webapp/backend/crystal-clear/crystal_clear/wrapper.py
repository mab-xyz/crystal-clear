import logging
from typing import Dict, List

from pydantic import BaseModel, Field

from crystal_clear.clients import AlliumClient, EtherscanClient, SourcifyClient
from crystal_clear.code_analyzer import (
    Analyzer,
    PermissionsInfo,
    ProxyInfo,
    Risk,
    RiskFactors,
)
from crystal_clear.traces import CallGraph, TraceCollector


class DependencyRisk(Risk):
    address: str = Field(..., description="Contract address of the dependency")
    dependency_depth: int = Field(..., description="Depth of the dependency chain")


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


class CrystalClear:
    def __init__(
        self,
        url: str,
        allium_api_key: str = None,
        etherscan_api_key: str = None,
        log_level: str = "INFO",
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

    def get_dependencies(
        self,
        address: str,
        from_block: str = None,
        to_block: str = None,
        blocks: int = 5,
    ) -> CallGraph:
        if not self.trace_collector:
            raise ValueError("TraceCollector is not initialized. Please provide a url.")

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
            raise ValueError("TraceCollector is not initialized. Please provide a url.")

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

    def get_risk_factors(
        self,
        address: str,
        scope: str,
        from_block: str = None,
        to_block: str = None,
        blocks: int = 5,
    ) -> RiskAnalysis:
        if scope not in ["single", "supply-chain"]:
            raise ValueError("Scope must be either 'single' or 'supply-chain'.")
        if not self.etherscan_key:
            raise ValueError(
                "EtherscanClient is not initialized. Please provide an etherscan_api_key."
            )
        if scope == "single":
            analyzer = Analyzer(self.etherscan_key, address, log_level=self.log_level)
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
                risk_factors=RiskFactors(upgradeability=False, permissioned=False),
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
                        analysis.aggregated_risks.risk_factors.permissioned = True
                except Exception as e:
                    print(f"Error analyzing {addr}: {e}")
            return analysis
