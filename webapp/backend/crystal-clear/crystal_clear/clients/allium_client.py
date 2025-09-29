import logging
from typing import Any, Dict, List, Optional

from .base_client import BaseClient


class AlliumClient(BaseClient):
    def __init__(self, api_key: str, log_level: str = "INFO"):
        super().__init__(
            base_url="https://api.allium.so/api/v1/explorer/queries", api_key=api_key
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))

    def get_labels(self, addresses: List[str]) -> Optional[Dict[str, str]]:
        """
        Get labels for multiple Ethereum addresses.

        Args:
            addresses: List of Ethereum addresses to lookup

        Returns:
            dict: Dictionary mapping addresses to their labels
        """
        if not addresses:
            self.logger.warning("No addresses provided for label lookup.")
            return None

        params = {
            "param_477": ",".join(f"'{address.lower()}'" for address in addresses)
        }
        response = self.post("g23nJaD4vABOS6utYocZ/run", params)

        if response and "data" in response:
            return {item["address"]: item["name"] for item in response["data"]}
        self.logger.warning("No data received for label lookup.")
        return None

    def get_deployment(self, address: str) -> Optional[Dict[str, str]]:
        """
        Get deployment information for a given Ethereum address.

        Args:
            address: Ethereum address to lookup

        Returns:
            dict: Dictionary containing deployment information
        """
        if not address:
            self.logger.warning("No address provided for deployment lookup.")
            return None

        params = {"param_191": address.lower()}
        response = self.post("zz57rFHkFDf69LFLWsX4/run", params)

        if response and "data" in response:
            return response["data"][0] if response["data"] else None
        self.logger.warning("No data received for deployment lookup.")
        return None

    def get_contract_dependencies(
        self, address: str, from_block: str, to_block: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get contract dependencies for analysis.

        Args:
            address: Contract address to analyze
            from_block: Starting block number
            to_block: Ending block number

        Returns:
            dict: Network data with nodes and edges
        """
        if not all([address, from_block, to_block]):
            self.logger.warning("Missing parameters for contract dependency lookup.")
            return None

        from_block = self.validate_convert_block(from_block)
        to_block = self.validate_convert_block(to_block)

        params = {
            "param_87": from_block,
            "param_43": to_block,
            "param_97": address.lower(),
        }
        response = self.post("Iovn51yTlL1FamnKu2BH/run", params)
        if response and "data" in response:
            nodes = {address.lower()}
            edges = {}
            n_matching_transactions = 0

            for row in response["data"]:
                n_matching_transactions += row.get("n_matching_transactions", 0)
                nodes.update(
                    [
                        row.get("from_address", "").lower(),
                        row.get("to_address", "").lower(),
                    ]
                )
                edge_key = (row.get("from_address"), row.get("to_address"))
                edges.setdefault(edge_key, {}).update(
                    {row.get("call_type", "").upper(): row.get("call_count", 0)}
                )

            data = {
                "address": address.lower(),
                "from_block": int(from_block),
                "to_block": int(to_block),
                "n_nodes": len(nodes),
                "n_matching_transactions": n_matching_transactions,
                "nodes": list(nodes),
                "edges": [
                    {"source": k[0], "target": k[1], "types": v}
                    for k, v in edges.items()
                ],
            }

            return data
        self.logger.warning("No data received for contract dependency lookup.")
        return None

    def get_contract_dependencies_latest(
        self, address: str, blocks: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Get contract dependencies for analysis using the latest blocks.

        Args:
            address: Contract address to analyze
            block_range: Number of blocks to analyze prior to the latest block

        Returns:
            dict: Network data with nodes and edges
        """
        params = {"param_69": str(blocks), "param_97": address.lower()}

        response = self.post("N8wWhdIF1OWEALVQVQlA/run", params)
        if response and "data" in response:
            nodes = {address.lower()}
            edges = {}
            n_matching_transactions = 0
            from_block = 0
            to_block = 0

            for row in response["data"]:
                from_block = row.get("from_block", 0)
                to_block = row.get("to_block", 0)
                n_matching_transactions += row.get("n_matching_transactions", 0)
                nodes.update(
                    [
                        row.get("from_address", "").lower(),
                        row.get("to_address", "").lower(),
                    ]
                )
                edge_key = (row.get("from_address"), row.get("to_address"))
                edges.setdefault(edge_key, {}).update(
                    {row.get("call_type", "").upper(): row.get("call_count", 0)}
                )

            data = {
                "address": address.lower(),
                "from_block": int(from_block),
                "to_block": int(to_block),
                "n_nodes": len(nodes),
                "n_matching_transactions": n_matching_transactions,
                "nodes": list(nodes),
                "edges": [
                    {"source": k[0], "target": k[1], "types": v}
                    for k, v in edges.items()
                ],
            }
            return data
        self.logger.warning("No data received for contract dependency lookup.")
        return None

    def validate_convert_block(self, block: str) -> str:
        if isinstance(block, str):
            if block.startswith("0x"):
                return str(int(block, 16))
            if int(block) >= 0:
                return block
        elif isinstance(block, int):
            return str(block)
        else:
            raise ValueError(
                "Block must be an integer or a hex string starting with '0x'"
            )
