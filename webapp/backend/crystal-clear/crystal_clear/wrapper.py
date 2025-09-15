from crystal_clear.traces import TraceCollector
from crystal_clear.clients import AlliumClient

class CrystalClear:
    def __init__(self, url: str = None, api_key: str = None):
        """
        Wrapper class for CrystalClear library.

        Parameters:
        -----------
        url : str, optional
            URL of the Ethereum node for TraceCollector.
        api_key : str, optional
            API key for AlliumClient.

        Raises:
        -------
        ValueError:
            If neither url nor api_key is provided.
        """
        if not url and not api_key:
            raise ValueError("You must provide at least a url or an api_key.")

        self.trace_collector = TraceCollector(url) if url else None
        self.allium_client = AlliumClient(api_key) if api_key else None
    
    def _init_trace_collector(self, url: str):
        if self.trace_collector is None:
            self.trace_collector = TraceCollector(url)
    
    def _init_allium_client(self, api_key: str):
        if self.allium_client is None:
            self.allium_client = AlliumClient(api_key)

    def get_dependencies_allium(self, address: str, from_block: str = None, to_block: str = None, blocks: int = 5) -> dict:
        if not self.allium_client:
            raise ValueError("AlliumClient is not initialized. Please provide an api_key.")
        
        if from_block is None and to_block is None:
            network = self.allium_client.get_contract_dependencies_latest(
                address=address,
                blocks=blocks
            )
        else:
            network = self.allium_client.get_contract_dependencies(
                address=address,
                from_block=from_block,
                to_block=to_block
            )
        if not network:
            raise Exception(f"Error fetching dependencies for address {address}. ")

        addresses = network["nodes"]
        labels = self.allium_client.get_labels(addresses)
        for addr in addresses:
            if addr not in labels:
                labels[addr] = addr
        network["nodes"] = labels
        return network

    def get_dependencies_node(self, address: str, from_block: str = None, to_block: str = None, blocks: int = 5) -> dict:
        if not self.trace_collector:
            raise ValueError("TraceCollector is not initialized. Please provide a url.")
        
        return self.trace_collector.get_network(address, from_block, to_block, blocks=blocks)

