import logging
import random
import time
from collections import deque
from typing import Dict, List, Set

from hexbytes import HexBytes
from web3 import Web3
from web3.middleware import Web3Middleware
from web3.types import CallTrace, RPCResponse

from .models import CallEdge, CallGraph


class RateLimitRetryMiddleware(Web3Middleware):
    def __init__(self, w3: Web3, max_retries: int = 5):
        super().__init__(w3)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.max_retries = max_retries

    def wrap_make_request(self, make_request):
        def middleware(method, params):
            for attempt in range(self.max_retries):
                try:
                    response: RPCResponse = make_request(method, params)
                    return response  # success or non-429 error
                except Exception as e:
                    self.logger.warning(
                        f"Request failed attempt {attempt + 1}: {e}. Retrying in {2 ** attempt} seconds..."
                    )
                    wait_time = (2**attempt) + random.random()
                    time.sleep(wait_time)
                    continue
            self.logger.warning("Max retries(5) reached. Giving up.")
            return response  # give up after max_retries

        return middleware


class TraceCollector:
    def __init__(self, url: str, log_level: str = "INFO"):
        """
        Initializes the TraceCollector with a URL and log level.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.w3 = Web3(Web3.HTTPProvider(url))
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to the Ethereum node.")
        self.w3.middleware_onion.add(RateLimitRetryMiddleware)
        self.logger.info("Connected to the Ethereum node.")

    def _validate_contract(self, address: str, block: str) -> bool:
        """
        Validates contract address, checks if it's different from x0 and not a precompile address.
        """
        try:
            if address.startswith("0x000000000000000000000000000000000000000"):
                self.logger.info(f"Address is a precompile address: {address}")
                return False
            address = Web3.to_checksum_address(address)
            if not Web3.is_address(address):
                self.logger.info(f"Invalid contract address format: {address}")
                return False
            code = self.w3.eth.get_code(address, block_identifier=block)
            if len(code) == 0:
                self.logger.info(f"No code at address: {address}")
                return False

            if code.hex() == "x0":
                self.logger.info(f"Contract at {address} matches x0 contract")
                return False

            return True
        except Exception as e:
            self.logger.error(f"Error validating contract: {e}")
            return False

    def _filter_txs_from(
        self, from_block: str, to_block: str, contract_address: str
    ) -> Set[str]:
        """
        Filters transactions from a given block range and contract address.
        """
        self.logger.info(
            f"Filtering transactions from block {from_block} \
              to {to_block} for contract {contract_address}."
        )
        filter_params = {
            "fromBlock": from_block,
            "toBlock": to_block,
            "fromAddress": [contract_address],
        }
        try:
            res = self.w3.tracing.trace_filter(filter_params)
        except Exception as e:
            self.logger.error(f"Error filtering transactions: {e}")
            return set()

        if res is None:
            return set()
        tx_hashes = {
            (
                r["transactionHash"].to_0x_hex()
                if type(r["transactionHash"]) is HexBytes
                else r["transactionHash"]
            )
            for r in res
            if r["type"] == "call"
        }
        self.logger.info(f"Found {len(tx_hashes)} transactions.")
        return tx_hashes

    def _get_calls_from_tx(self, tx_hash: str) -> CallTrace:
        """
        Gets calls from a transaction hash.
        """
        self.logger.info(f"Tracing transaction {tx_hash}.")
        try:
            res = self.w3.geth.debug.trace_transaction(
                tx_hash, {"tracer": "callTracer"}
            )
        except Exception as e:
            self.logger.error(f"Error tracing transaction {tx_hash}: {e}")
            return None
        return res

    def _extract_all_subcalls(
        self, call: CallTrace, calls: Dict[tuple[str, str], CallEdge], caller: str
    ) -> None:
        """
        Recursively extracts all subcalls from a call.
        """
        key: tuple[str, str] = (caller, call["to"])
        if key not in calls:
            calls[key] = CallEdge(source=caller, target=call["to"], types={})
        if call["type"] not in calls[key].types:
            calls[key].types[call["type"]] = 0
        calls[key].types[call["type"]] += 1
        for subcall in call.get("calls", []):
            self._extract_all_subcalls(subcall, calls, call["to"])

    def _extract_calls(
        self,
        call: CallTrace,
        contract_address: str,
        calls: Dict[tuple[str, str], CallEdge],
    ) -> None:
        """
        Extracts calls from a call and its subcalls.
        """
        if call["to"].lower() == contract_address.lower():
            for subcall in call.get("calls", []):
                self._extract_all_subcalls(subcall, calls, call["to"])
        else:
            for subcall in call.get("calls", []):
                self._extract_calls(subcall, contract_address, calls)

    def get_calls(self, tx_hashes: Set[str], contract_address: str) -> List[CallEdge]:
        """
        Gets calls for a given set of transaction hashes and contract address.
        """
        self.logger.info(f"Getting calls for contract {contract_address}.")
        calls = {}
        for h in tx_hashes:
            res = self._get_calls_from_tx(h)
            if res:
                self._extract_calls(res, contract_address, calls)
        self.logger.info(f"Extracted {len(calls)} calls.")
        return list(calls.values())

    def _filter_contract_calls(self, calls: List[CallEdge], to_block) -> List[CallEdge]:
        """
        Filters calls to contract addresses.
        """
        return [c for c in calls if self._validate_contract(c.target, to_block)]

    def get_calls_from(
        self, from_block: str | int, to_block: str | int, contract_address: str
    ) -> CallGraph:
        """
        Gets calls from a given block range and contract address.
        """
        self.logger.info(
            f"Getting calls from block {from_block} \
            to {to_block} for contract {contract_address}."
        )
        from_block_hex: str = self.validate_and_convert_block(from_block)
        to_block_hex: str = self.validate_and_convert_block(to_block)

        if not self._validate_contract(contract_address, to_block_hex):
            raise ValueError("Invalid contract address or bytecode.")

        contract_address: str = Web3.to_checksum_address(contract_address)
        tx_hashes: Set[str] = self._filter_txs_from(
            from_block_hex, to_block_hex, contract_address
        )
        calls: List[CallEdge] = self.get_calls(tx_hashes, contract_address)
        filtered_calls: List[CallEdge] = self._filter_contract_calls(
            calls, to_block_hex
        )

        edges: List[CallEdge] = filtered_calls
        nodes: Set[str] = set()
        for edge in edges:
            nodes.add(edge.source)
            nodes.add(edge.target)

        nodes_dict = {node: "" for node in nodes}

        depths: Dict[str, int] = self.get_depths(nodes, edges, contract_address.lower())
        graph = CallGraph(
            address=contract_address,
            from_block=int(from_block_hex, 16),
            to_block=int(to_block_hex, 16),
            n_nodes=len(nodes),
            nodes=nodes_dict,
            edges=edges,
            dependency_depths=depths,
            n_matching_transactions=len(tx_hashes),
        )
        self.logger.info(
            f"Constructed call graph with {len(nodes)} nodes and {len(edges)} edges."
        )
        return graph

    def get_call_graph(
        self,
        contract_address: str,
        from_block: str | int | None,
        to_block: str | int | None,
        blocks: int = 5,
    ) -> CallGraph:
        """
        Collects calls from the last 5 blocks and returns the call graph in JSON format.
        """
        if from_block is None and to_block is None:
            self.logger.info("Collecting calls from the last n blocks.")
            latest_block = self.w3.eth.block_number
            from_block = latest_block - blocks
            to_block = latest_block

        res = self.get_calls_from(from_block, to_block, contract_address)
        return res

    def validate_and_convert_block(self, block: str) -> str:
        """
        Validates if block number is decimal or hex and returns hex format.
        """
        if isinstance(block, int):
            return hex(block)

        if isinstance(block, str):
            if block.startswith("0x"):
                try:
                    int(block, 16)
                    return block
                except ValueError as e:
                    raise ValueError(f"Invalid hex block number: {block}") from e

            if block.isdigit():
                return hex(int(block))

        raise ValueError(
            f"Block number must be decimal or hexadecimal: {block}"
        ) from None

    def get_depths(
        self, nodes: Set[str], edges: List[CallEdge], root_address: str
    ) -> Dict[str, int]:
        """
        Add depth information to edges based on distance from the root address.

        Args:
            data: The data structure containing address, nodes, and edges

        Returns:
            The modified data structure with depth added to each edge
        """

        # Create adjacency list for graph traversal
        graph = {}
        for edge in edges:
            source = edge.source.lower()
            target = edge.target.lower()

            if source not in graph:
                graph[source] = []
            graph[source].append(target)

        # BFS to calculate depths from root address
        depths = {}
        visited = set()
        queue = deque()

        # Start with root address at depth 0
        queue.append((root_address, 0))
        visited.add(root_address)
        depths[root_address] = 0

        while queue:
            current_node, current_depth = queue.popleft()

            if current_node in graph:
                for neighbor in graph[current_node]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        depths[neighbor] = current_depth + 1
                        queue.append((neighbor, current_depth + 1))

        dependency_depths = {}
        for node in nodes:
            if node.lower() != root_address.lower():
                depth = depths.get(
                    node.lower(), -1
                )  # -1 if target not reachable from root
                dependency_depths[node.lower()] = depth
        return dependency_depths
