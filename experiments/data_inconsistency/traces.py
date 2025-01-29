from typing import Dict, Any
import requests

class Traces:
    def __init__(self, url: str, id: str):
        """
        Initialize the Traces class with the given RPC URL.

        :param url: The base URL for the JSON-RPC endpoint.
        """
        self.url = url
        self.id = id
        self.no = 1

    def post_request(self, method: str, params: Any) -> Any:
        """
        Send a POST request to the JSON-RPC endpoint.

        :param method: The JSON-RPC method name.
        :param params: The parameters for the method.
        :return: The result from the JSON-RPC response.
        """
        response = requests.post(
            self.url,
            json={
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": self.id + str(self.no),
            }
        )
        self.no += 1
        response.raise_for_status()  # Raise an error for HTTP errors
        return response.json().get("result")

    def get_block(self, block_number: int, precompiles: bool = True) -> Dict[str, Any]:
        """
        Get traces for a specific block.

        :param block_number: The block number to get traces for.
        :param precompiles: Whether to include precompiles in the traces.
        :return: A dictionary with block traces.
        """
        return self.post_request(
            "trace_block",
            [block_number, None, {"tracerConfig": {"includePrecompiles": precompiles}}]
        )

    def get_transaction(self, tx_hash: str, precompiles: bool = True) -> Dict[str, Any]:
        """
        Get traces for a specific transaction.

        :param tx_hash: The transaction hash to get traces for.
        :param precompiles: Whether to include precompiles in the traces.
        :return: A dictionary with transaction traces.
        """
        return self.post_request(
            "trace_transaction",
            [tx_hash, None, {"tracerConfig": {"includePrecompiles": precompiles}}]
        )