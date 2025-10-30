import logging
from typing import Any, Dict, List

from web3 import Web3

from .models import CallEdge
from .trace_collector import TraceCollector
from .adapters import from_trace_call


class SimulationCollector(TraceCollector):
    def __init__(self, url: str, log_level: str = "INFO"):
        super().__init__(url=url, log_level=log_level)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _trace_call(
        self, call_object: Dict[str, Any], block_tag: str | int = "latest"
    ) -> Dict[str, Any] | None:
        try:
            tag: str
            if isinstance(block_tag, int):
                tag = self.validate_and_convert_block(block_tag)
            elif isinstance(block_tag, str) and block_tag.startswith("0x"):
                tag = self.validate_and_convert_block(block_tag)
            else:
                tag = block_tag  # allow tags like "latest", "pending"

            traces = self.w3.tracing.trace_call(call_object, ["trace"], tag)
            root = from_trace_call(traces, logger=self.logger)
            return root
        except Exception as e:
            self.logger.error(f"Error during trace_call: {e}")
            return None

    def get_edges_from_simulation(
        self, call_object: Dict[str, Any], block_tag: str | int = "latest"
    ) -> List[CallEdge]:
        self.logger.info("Running simulation via trace_call.")

        root = self._trace_call(call_object, block_tag)
        if not root:
            return []

        contract_address = call_object.get("to") or root.get("to") or ""
        if not contract_address:
            return []

        calls: Dict[tuple[str, str], CallEdge] = {}
        try:
            self._extract_calls(
                root, Web3.to_checksum_address(contract_address), calls
            )
        except Exception as e:
            self.logger.error(f"Error extracting calls from simulation: {e}")
            return []

        # Determine block identifier for contract code checks
        block_identifier: Any
        if isinstance(block_tag, int) or (
            isinstance(block_tag, str) and block_tag.startswith("0x")
        ):
            block_identifier = self.validate_and_convert_block(block_tag)
        else:
            block_identifier = block_tag

        filtered = self._filter_contract_calls(
            list(calls.values()), block_identifier
        )
        self.logger.info(f"Extracted {len(filtered)} edges from simulation.")
        return filtered

    def get_edges_from_tx(self, tx_hash: str, root_contract: str | None = None) -> List[CallEdge]:
        """
        Extract call edges from an on-chain transaction using debug_traceTransaction.

        If root_contract is not provided, the top-level trace 'to' will be used
        as the root and all of its subcalls will be extracted.
        """
        self.logger.info(f"Tracing on-chain transaction {tx_hash}.")
        trace = self._get_calls_from_tx(tx_hash)
        if not trace:
            return []

        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            block_number = receipt.blockNumber
            block_identifier = self.validate_and_convert_block(block_number)
        except Exception:
            block_identifier = "latest"

        if not root_contract:
            root_contract = trace.get("to") or ""
        if not root_contract:
            return []

        calls: Dict[tuple[str, str], CallEdge] = {}
        try:
            self._extract_calls(trace, Web3.to_checksum_address(root_contract), calls)
        except Exception as e:
            self.logger.error(f"Error extracting calls from tx: {e}")
            return []

        filtered = self._filter_contract_calls(list(calls.values()), block_identifier)
        self.logger.info(f"Extracted {len(filtered)} edges from tx.")
        return filtered
