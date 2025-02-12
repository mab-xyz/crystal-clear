import logging

from web3 import Web3

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
        contract_address = self._validate_and_convert_address(contract_address)
        self.cg = CallGraph(contract_address)
        self.logger.info(
            f"Initialized SupplyChain for contract {contract_address}."
        )

    def _validate_and_convert_block(self, block: str) -> str:
        """
        Validates if block number is decimal or hex and returns hex format.
        """
        if isinstance(block, int):
            return hex(block)

        if isinstance(block, str):
            # Check if it's already hex
            if block.startswith("0x"):
                try:
                    int(block, 16)
                    return block
                except ValueError as e:
                    raise ValueError(
                        f"Invalid hex block number: {block}"
                    ) from e

            # Check if it's decimal
            if block.isdigit():
                return hex(int(block))

        raise ValueError(
            f"Block number must be decimal or hexadecimal: {block}"
        ) from None

    def _validate_and_convert_address(self, address: str) -> str:
        """
        Validates if the address is a valid Ethereum address and converts to checksum.

        Args:
            address: Ethereum address
        Returns:
            Checksum address
        Raises:
            ValueError: If address is invalid
        """
        if not Web3.is_address(address):
            raise ValueError(f"Invalid Ethereum address: {address}")
        return Web3.to_checksum_address(address)

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
        try:
            from_block_hex = self._validate_and_convert_block(from_block)
            to_block_hex = self._validate_and_convert_block(to_block)

            if int(from_block_hex, 16) > int(to_block_hex, 16):
                raise ValueError(
                    f"from_block ({from_block}) must be less than or equal to to_block ({to_block})"
                )

            calls = self.tc.get_calls_from(
                from_block_hex, to_block_hex, self.cg.contract_address
            )
            for c in calls:
                self.cg.add_call(c["from"], c["to"], data=c["type"])
            self.logger.info(f"Collected {len(calls)} calls.")
        except Exception as e:
            self.logger.error(f"collect_calls: {e}")

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
