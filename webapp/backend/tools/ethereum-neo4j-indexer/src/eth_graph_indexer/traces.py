"""Trace retrieval and internal interaction parsing."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .address_filter import normalize_address
from .models import InteractionEdge, hex_to_int
from .rpc import RpcClient


def _safe_address(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return normalize_address(value)
    except ValueError:
        return None


def parse_parity_traces(
    traces: Iterable[dict], block_number: int
) -> list[InteractionEdge]:
    edges: list[InteractionEdge] = []
    for trace in traces:
        if not isinstance(trace, Mapping):
            continue
        trace_type = str(trace.get("type", "")).lower()
        action = trace.get("action")
        if not isinstance(action, Mapping):
            continue
        if trace.get("traceAddress") == []:
            continue
        tx_hash = trace.get("transactionHash")
        if not isinstance(tx_hash, str):
            continue

        if trace_type == "call":
            from_address = _safe_address(action.get("from"))
            to_address = _safe_address(action.get("to"))
            call_type = str(action.get("callType") or "call").lower()
            value = hex_to_int(action.get("value"))
            interaction_type = f"internal_{call_type}"
        elif trace_type in {"suicide", "selfdestruct"}:
            from_address = _safe_address(
                action.get("address") or action.get("from")
            )
            to_address = _safe_address(
                action.get("refundAddress")
                or action.get("beneficiary")
                or action.get("to")
            )
            value = hex_to_int(
                action.get("balance")
                if action.get("balance") is not None
                else action.get("value")
            )
            interaction_type = "selfdestruct"
        elif trace_type == "create":
            from_address = _safe_address(action.get("from"))
            result = trace.get("result")
            to_address = (
                _safe_address(result.get("address"))
                if isinstance(result, Mapping)
                else None
            )
            value = hex_to_int(action.get("value"))
            interaction_type = "internal_contract_creation"
        else:
            continue

        if from_address and to_address:
            edges.append(
                InteractionEdge(
                    tx_hash=tx_hash.lower(),
                    block_number=block_number,
                    from_address=from_address,
                    to_address=to_address,
                    interaction_type=interaction_type,
                    value_wei=str(value),
                )
            )
    return edges


def _walk_call_frame(
    frame: Mapping[str, Any],
    *,
    tx_hash: str,
    block_number: int,
    root: bool,
) -> list[InteractionEdge]:
    edges: list[InteractionEdge] = []
    frame_type = str(frame.get("type") or "CALL").upper()
    from_address = _safe_address(frame.get("from"))
    to_address = _safe_address(frame.get("to"))

    if not root and from_address and to_address:
        if frame_type in {"SELFDESTRUCT", "SUICIDE"}:
            interaction_type = "selfdestruct"
        elif frame_type in {"CREATE", "CREATE2"}:
            interaction_type = "internal_contract_creation"
        else:
            interaction_type = f"internal_{frame_type.lower()}"
        edges.append(
            InteractionEdge(
                tx_hash=tx_hash.lower(),
                block_number=block_number,
                from_address=from_address,
                to_address=to_address,
                interaction_type=interaction_type,
                value_wei=str(hex_to_int(frame.get("value"))),
            )
        )

    calls = frame.get("calls") or []
    if isinstance(calls, list):
        for child in calls:
            if isinstance(child, Mapping):
                edges.extend(
                    _walk_call_frame(
                        child,
                        tx_hash=tx_hash,
                        block_number=block_number,
                        root=False,
                    )
                )
    return edges


def parse_debug_traces(
    payload: list,
    transactions: tuple[dict, ...],
    block_number: int,
) -> list[InteractionEdge]:
    edges: list[InteractionEdge] = []
    for index, item in enumerate(payload):
        if index >= len(transactions):
            break
        tx_hash = transactions[index].get("hash")
        if not isinstance(tx_hash, str) or not isinstance(item, Mapping):
            continue
        frame = item.get("result", item)
        if isinstance(frame, Mapping):
            edges.extend(
                _walk_call_frame(
                    frame,
                    tx_hash=tx_hash,
                    block_number=block_number,
                    root=True,
                )
            )
    return edges


class TraceLoader:
    def __init__(self, rpc: RpcClient, mode: str) -> None:
        self.rpc = rpc
        self.mode = mode

    def get_for_block(
        self, block_number: int, transactions: tuple[dict, ...]
    ) -> list[InteractionEdge]:
        if self.mode == "none":
            return []
        if self.mode == "trace_block":
            payload = self.rpc.call("trace_block", [hex(block_number)])
            if not isinstance(payload, list):
                raise ValueError("trace_block did not return a list")
            return parse_parity_traces(payload, block_number)
        payload = self.rpc.call(
            "debug_traceBlockByNumber",
            [
                hex(block_number),
                {"tracer": "callTracer", "timeout": "120s"},
            ],
        )
        if not isinstance(payload, list):
            raise ValueError("debug_traceBlockByNumber did not return a list")
        return parse_debug_traces(payload, transactions, block_number)
