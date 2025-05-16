import logging

from scsc.graph import CallGraph
from scsc.traces import TraceCollector
from scsc.utils import validate_and_convert_address, validate_and_convert_block


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
        contract_address = validate_and_convert_address(contract_address)
        self.cg = CallGraph(contract_address)
        self.logger.info(
            f"Initialized SupplyChain for contract {contract_address}."
        )

    def get_network(
        self,
        from_block: str | int | None,
        to_block: str | int | None,
        blocks: int = 10,
    ) -> dict:
        """
        Collects calls from the last 10 blocks and returns the call graph in JSON format.
        """
        if from_block is None and to_block is None:
            self.logger.info("Collecting calls from the last n blocks.")
            latest_block = self.tc.w3.eth.block_number
            from_block = latest_block - blocks
            to_block = latest_block

        self.collect_calls(from_block, to_block)
        edges = self.cg.to_json()["edges"]
        return {
            "contract_address": self.cg.contract_address,
            "from_block": from_block,
            "to_block": to_block,
            "n_nodes": len(self.cg.get_all_contracts()),
            "nodes": self.cg.get_all_contracts(),
            "edges": edges,
        }

    def collect_calls(
        self, from_block: str | int, to_block: str | int
    ) -> None:
        """
        Collects calls from the blockchain and adds them to the call graph.
        Args:
            from_block: Block number in decimal or hex format
            to_block: Block number in decimal or hex format
        Raises:
            ValueError: If from_block is greater than to_block
        """
        self.logger.info(
            f"Collecting calls from block {from_block} to {to_block}."
        )
        from_block_hex = validate_and_convert_block(from_block)
        to_block_hex = validate_and_convert_block(to_block)

        if int(from_block_hex, 16) > int(to_block_hex, 16):
            raise ValueError(
                f"from_block ({from_block}) must be less than or equal to to_block ({to_block})"
            )

        calls = self.tc.get_calls_from(
            from_block_hex, to_block_hex, self.cg.contract_address
        )
        for c in calls:
            self.cg.add_call(c["from"], c["to"], c["type"])
        self.logger.info(f"Collected {len(calls)} calls.")

    def get_all_dependencies(self) -> list:
        """
        Collects all contracts in the call graph excluding the main contract address.
        """
        all_contracts = self.cg.get_all_contracts()
        return [
            contract
            for contract in all_contracts
            if contract != self.cg.contract_address
        ]

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
