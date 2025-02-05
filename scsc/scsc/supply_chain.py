import logging

from scsc.graph import CallGraph
from scsc.traces import TraceCollector


class SupplyChain:
    """
    Represents a supply chain that collects
    and processes call data from a blockchain.
    """

    def __init__(self, url: str, contract_address: str):
        """
        Initializes the SupplyChain with a URL and contract address.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tc = TraceCollector(url)
        self.cg = CallGraph(contract_address)
        self.logger.info(
            f"Initialized SupplyChain for contract {contract_address}."
        )

    def collect_calls(self, from_block: str, to_block: str) -> None:
        """
        Collects calls from the blockchain and adds them to the call graph.
        """
        self.logger.info(
            f"Collecting calls from block {from_block} to {to_block}."
        )
        try:
            from_block_hex = (
                hex(int(from_block)) if from_block.isdigit() else from_block
            )
            to_block_hex = (
                hex(int(to_block)) if to_block.isdigit() else to_block
            )
            calls = self.tc.get_calls_from(
                from_block_hex, to_block_hex, self.cg.contract_address
            )
            for c in calls:
                self.cg.add_call(c["from"], c["to"], data=c["type"])
            self.logger.info(f"Collected {len(calls)} calls.")
        except Exception as e:
            self.logger.error(f"Error collecting calls: {e}")

    def get_all_dependencies(self) -> None:
        """
        Collects all dependencies of the contract.
        """
        return self.cg.get_callee_contracts(self.cg.contract_address)

    def export_dot(self, filename: str) -> None:
        """
        Exports the call graph to a DOT file.
        """
        self.logger.info(f"Exporting call graph to DOT file: {filename}.")
        self.cg.export_dot(filename)

    def export_json(self, filename: str) -> None:
        """
        Exports the call graph to a JSON file.
        """
        self.logger.info(f"Exporting call graph to JSON file: {filename}.")
        self.cg.export_json(filename)
