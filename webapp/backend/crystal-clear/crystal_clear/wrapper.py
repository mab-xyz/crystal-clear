from crystal_clear.traces import TraceCollector
from crystal_clear.clients import AlliumClient
from crystal_clear.code_analyzer import Analyzer

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
        self.etherscan_client = etherscan_api_key

    def get_dependencies(self, address: str, from_block: str = None, to_block: str = None, blocks: int = 5) -> dict:
        if not self.trace_collector:
            raise ValueError("TraceCollector is not initialized. Please provide a url.")

        callgraph = self.trace_collector.get_call_graph(address, from_block, to_block, blocks=blocks)

        if self.allium_client:
            addresses = callgraph.nodes
            labels = self.allium_client.get_labels(addresses)
            for addr in addresses:
                if addr not in labels:
                    labels[addr] = addr
            callgraph.nodes = labels
        return callgraph.to_dict()
    
    def get_code_analysis(self, address: str) -> dict:
        if not self.etherscan_client:
            raise ValueError("EtherscanClient is not initialized. Please provide an etherscan_api_key.")

        analyzer = Analyzer(self.etherscan_client, address)
        analysis = analyzer.analyze()
        return analysis
