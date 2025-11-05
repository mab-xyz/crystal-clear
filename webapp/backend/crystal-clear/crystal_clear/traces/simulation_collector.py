import logging
from typing import Any, Dict, List
from collections.abc import Mapping

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
            elif isinstance(block_tag, str):
                if block_tag.startswith("0x") or block_tag.isdigit():
                    tag = self.validate_and_convert_block(block_tag)
                else:
                    tag = block_tag  # allow tags like "latest", "pending"
            else:
                tag = block_tag

            # Normalize call object to satisfy RPC expectations
            co = dict(call_object)
            try:
                if "from" in co and co["from"]:
                    co["from"] = Web3.to_checksum_address(co["from"])
                if "to" in co and co["to"]:
                    co["to"] = Web3.to_checksum_address(co["to"])
            except Exception as e:
                self.logger.error(f"Invalid address in call object: {e}")
                return None

            def to_hex_qty(v):
                if v is None:
                    return None
                if isinstance(v, int):
                    return hex(v)
                if isinstance(v, str):
                    s = v.strip()
                    if s.lower().startswith("0x"):
                        return s
                    if s.isdigit():
                        return hex(int(s))
                return v

            for k in ("value", "gas", "gasPrice"):
                if k in co:
                    co[k] = to_hex_qty(co[k])

            if (
                "data" in co
                and isinstance(co["data"], str)
                and not co["data"].lower().startswith("0x")
            ):
                co["data"] = "0x" + co["data"]

            resp = self.w3.tracing.trace_call(co, ["trace"], tag)
            # Accept both Erigon-style mapping with 'trace' and raw list
            if isinstance(resp, Mapping) or hasattr(resp, "get"):
                try:
                    traces = resp.get("trace") or resp.get("traces") or []
                except Exception:
                    # Fallback: try to coerce to dict then access
                    try:
                        traces = (
                            dict(resp).get("trace")
                            or dict(resp).get("traces")
                            or []
                        )
                    except Exception:
                        traces = []
            elif isinstance(resp, list):
                traces = resp
            else:
                self.logger.error(
                    f"Unsupported trace_call response type: {type(resp)}"
                )
                return None

            # Log a concise summary of trace_call results to aid debugging
            try:
                n = len(traces) if isinstance(traces, list) else 0
                self.logger.info(
                    f"trace_call returned {n} trace entrie(s); resp_type={type(resp)}"
                )
                # Log all trace entries (may be verbose)
                for i, tr in enumerate(traces):
                    try:
                        ttype = str(tr.get("type", "")).upper()
                        action = tr.get("action", {}) or {}
                        src = action.get("from")
                        dst = action.get("to")
                        ctype = str(action.get("callType", "")).upper() or "-"
                        path = tr.get("traceAddress", []) or []
                        self.logger.info(
                            f"trace[{i}]: type={ttype} callType={ctype} from={src} to={dst} path={path}"
                        )
                    except Exception as ie:
                        self.logger.debug(f"trace[{i}] summary error: {ie}")
            except Exception as le:
                self.logger.debug(f"trace_call logging error: {le}")

            if not isinstance(traces, list):
                self.logger.error(
                    f"Unexpected 'trace' payload type: {type(traces)}"
                )
                return None

            root = from_trace_call(traces, logger=self.logger)
            return root
        except Exception as e:
            self.logger.error(f"Error during trace_call: {e}")
            return None

    def get_edges_from_simulation(
        self,
        call_object: Dict[str, Any],
        block_tag: str | int = "latest",
    ) -> List[CallEdge]:
        self.logger.info("Running simulation via trace_call.")

        root = self._trace_call(call_object, block_tag)
        if not root:
            return []

        calls: Dict[tuple[str, str], CallEdge] = {}
        try:
            # Determine which top-level node(s) to extract from.
            # trace_call may return multiple top-level entries; our normalizer
            # wraps them under a synthetic ROOT node (type == "ROOT"). In that case,
            # we should locate the branch matching the intended callee (call_object["to"]).
            target_callee = (
                call_object.get("to") or root.get("to") or ""
            ).strip()

            # Helper to checksum safely
            def _checksum(addr: str) -> str:
                try:
                    return Web3.to_checksum_address(addr)
                except Exception:
                    return addr

            # Build list of entry nodes to traverse
            entry_nodes: List[Dict[str, Any]]
            if str(root.get("type", "")).upper() == "ROOT":
                candidates = list(root.get("calls", []) or [])
                if target_callee:
                    want = target_callee.lower()
                    selected = [
                        c
                        for c in candidates
                        if (c.get("to") or "").lower() == want
                    ]
                    entry_nodes = selected or candidates
                    if not selected:
                        self.logger.warning(
                            "Root callee %s not found among top-level traces; extracting all branches.",
                            target_callee,
                        )
                else:
                    entry_nodes = candidates
            else:
                entry_nodes = [root]

            # Traverse each selected entry node, seeding caller as its own 'to'
            for node in entry_nodes:
                to_addr = (node.get("to") or "").strip()
                if not to_addr:
                    # Skip malformed nodes without a target
                    continue
                seed = _checksum(target_callee or to_addr)
                self._extract_all_subcalls(node, calls, seed)
        except Exception as e:
            self.logger.error(f"Error extracting calls from simulation: {e}")
            return []

        # Determine block identifier for contract code checks
        block_identifier: Any
        if isinstance(block_tag, int):
            block_identifier = self.validate_and_convert_block(block_tag)
        elif isinstance(block_tag, str):
            # Convert numeric strings (decimal or 0x-hex) to hex; keep tags like "latest"
            if block_tag.startswith("0x") or block_tag.isdigit():
                block_identifier = self.validate_and_convert_block(block_tag)
            else:
                block_identifier = block_tag
        else:
            block_identifier = block_tag

        filtered = self._filter_contract_calls(
            list(calls.values()), block_identifier
        )
        self.logger.info(
            f"Extracted {len(filtered)} edges from simulation, the block is {block_identifier}."
        )
        return filtered

    def get_edges_from_tx(
        self,
        tx_hash: str,
        root_contract: str | None = None,
    ) -> List[CallEdge]:
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
            # Always collect the full subcall tree beneath the root contract
            self._extract_all_subcalls(
                trace, calls, Web3.to_checksum_address(root_contract)
            )
        except Exception as e:
            self.logger.error(f"Error extracting calls from tx: {e}")
            return []

        filtered = self._filter_contract_calls(
            list(calls.values()), block_identifier
        )
        self.logger.info(f"Extracted {len(filtered)} edges from tx.")
        return filtered
