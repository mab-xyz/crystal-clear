from crystal_clear.traces import TraceCollector
from crystal_clear.clients import AlliumClient

class CrystalClear:
    def __init__(self, url: str, api_key: str = None):
        """
        Wrapper class for CrystalClear library.

        Parameters:
        -----------
        url : str
            URL of the Ethereum node for TraceCollector.
        api_key : str, optional
            API key for AlliumClient.

        Raises:
        -------
        ValueError:
            If url is not provided.
        """
        if not url:
            raise ValueError("You must provide at least a node url.")

        self.trace_collector = TraceCollector(url)
        self.allium_client = AlliumClient(api_key) if api_key else None

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
        return callgraph
