from crystal_clear.traces import TraceCollector, CallGraph
from crystal_clear.clients import AlliumClient, EtherscanClient, SourcifyClient
from crystal_clear.code_analyzer import Analyzer, ProxyInfo, PermissionsInfo

class CrystalClear:
    def __init__(self, url: str, allium_api_key: str = None, etherscan_api_key: str = None):
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
        self.trace_collector = TraceCollector(url) if url else None
        self.allium_client = AlliumClient(allium_api_key) if allium_api_key else None
        self.etherscan_key = etherscan_api_key
        self.sourcify_client = SourcifyClient()
        self.etherscan_client = EtherscanClient(etherscan_api_key) if etherscan_api_key else None

    def get_dependencies(self, address: str, from_block: str = None, to_block: str = None, blocks: int = 5) -> CallGraph:
        if not self.trace_collector:
            raise ValueError("TraceCollector is not initialized. Please provide a url.")

        callgraph = self.trace_collector.get_call_graph(address, from_block, to_block, blocks=blocks)

        return callgraph

    def get_dependencies_full(self, address: str, from_block: str = None, to_block: str = None, blocks: int = 5) -> CallGraph:
        if not self.trace_collector:
            raise ValueError("TraceCollector is not initialized. Please provide a url.")

        callgraph = self.trace_collector.get_call_graph(address, from_block, to_block, blocks=blocks)

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
            raise ValueError("EtherscanClient is not initialized. Please provide an etherscan_api_key.")

        analyzer = Analyzer(self.etherscan_key, address)
        analysis = analyzer.get_proxy_info()
        return analysis

    def get_permissions_info(self, address: str) -> PermissionsInfo:
        if not self.etherscan_key:
            raise ValueError("EtherscanClient is not initialized. Please provide an etherscan_api_key.")

        analyzer = Analyzer(self.etherscan_key, address)
        permissions = analyzer.get_permissions_info()
        return permissions
