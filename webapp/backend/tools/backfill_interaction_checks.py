from __future__ import annotations

from typing import Callable, Optional

from hexbytes import HexBytes
from web3 import Web3


ALLOWED_TRACE_TYPES = {"call", "delegatecall", "staticcall", "callcode"}
MAX_TRACE_PAGES_PER_CALL = 2_000
TRACE_FILTER_FN: Callable[[Web3, dict, str], list] | None = None


def _normalize_address(address: str | None) -> Optional[str]:
    if not address:
        return None
    addr = address.strip().lower()
    return addr if addr.startswith("0x") else None


def _to_hex_block(value: int) -> str:
    return hex(max(0, int(value)))


def _trace_filter(w3: Web3, params: dict, label: str):
    if TRACE_FILTER_FN is not None:
        return TRACE_FILTER_FN(w3, params, label)
    return w3.tracing.trace_filter(params)


def _normalize_tx_hash(tx_hash: object) -> Optional[str]:
    if isinstance(tx_hash, HexBytes):
        return tx_hash.to_0x_hex()
    if isinstance(tx_hash, str) and tx_hash:
        return tx_hash
    return None


def _page_fingerprint(traces: list[dict]) -> tuple:
    if not traces:
        return (0, None, None, None, None)
    first = traces[0]
    last = traces[-1]
    return (
        len(traces),
        _normalize_tx_hash(first.get("transactionHash")),
        _normalize_tx_hash(last.get("transactionHash")),
        tuple(first.get("traceAddress") or ()),
        tuple(last.get("traceAddress") or ()),
    )


def _is_allowed_trace_type(trace: dict) -> bool:
    return str(trace.get("type", "")).lower() in ALLOWED_TRACE_TYPES


def _is_root_trace(trace: dict) -> bool:
    trace_address = trace.get("traceAddress")
    return trace_address is None or trace_address == []


def _trace_from_to(trace: dict) -> tuple[Optional[str], Optional[str]]:
    from_addr = _normalize_address(trace.get("from"))
    to_addr = _normalize_address(trace.get("to"))
    if from_addr is not None and to_addr is not None:
        return from_addr, to_addr

    action = trace.get("action")
    if isinstance(action, dict):
        return _normalize_address(action.get("from")), _normalize_address(
            action.get("to")
        )
    return from_addr, to_addr


def _is_exact_from_to_trace(
    trace: dict,
    from_address: str,
    to_address: str,
) -> bool:
    trace_from, trace_to = _trace_from_to(trace)
    return trace_from == _normalize_address(from_address) and trace_to == _normalize_address(
        to_address
    )


def _count_direct_interactions(
    w3: Web3,
    from_address: str,
    to_address: str,
    scan_start: int,
    scan_end: int,
    page_size: int,
    *,
    root_only: bool,
    mode_name: str,
) -> tuple[int, bool]:
    try:
        from_checksum = Web3.to_checksum_address(from_address)
        to_checksum = Web3.to_checksum_address(to_address)
    except Exception:
        return 0, False

    tx_hashes: set[str] = set()
    after = 0
    pages = 0
    seen_pages: set[tuple] = set()
    complete = True
    use_intersection = True
    while True:
        if pages >= MAX_TRACE_PAGES_PER_CALL:
            print(
                f"[warn] reached max pages in {mode_name} scan; stopping early "
                f"from={from_address} to={to_address} after={after}"
            )
            complete = False
            break
        pages += 1
        params = {
            "fromBlock": _to_hex_block(scan_start),
            "toBlock": _to_hex_block(scan_end),
            "fromAddress": [from_checksum],
            "count": max(1, int(page_size)),
            "after": after,
        }
        if use_intersection:
            params["toAddress"] = [to_checksum]
            params["mode"] = "intersection"
        try:
            traces = _trace_filter(w3, params, mode_name)
        except Exception:
            # Fallback for providers that do not support intersection mode.
            if use_intersection:
                use_intersection = False
                continue
            complete = False
            break

        if not isinstance(traces, list) or not traces:
            break
        fp = _page_fingerprint(traces)
        if fp in seen_pages:
            print(
                f"[warn] repeated trace_filter page detected in {mode_name}; "
                "stopping early"
            )
            complete = False
            break
        seen_pages.add(fp)

        for trace in traces:
            if not _is_allowed_trace_type(trace):
                continue
            if not _is_exact_from_to_trace(trace, from_address, to_address):
                continue
            if root_only and not _is_root_trace(trace):
                continue
            tx_hash = _normalize_tx_hash(trace.get("transactionHash"))
            if tx_hash:
                tx_hashes.add(tx_hash)

        if len(traces) < int(page_size):
            break
        after += len(traces)

    return len(tx_hashes), complete


def _count_contract_direct_interactions(
    w3: Web3,
    from_address: str,
    to_address: str,
    scan_start: int,
    scan_end: int,
    page_size: int,
) -> tuple[int, bool]:
    return _count_direct_interactions(
        w3,
        from_address,
        to_address,
        scan_start,
        scan_end,
        page_size,
        root_only=False,
        mode_name="contract_direct",
    )


def _count_sender_direct_interactions(
    w3: Web3,
    sender_address: str,
    to_address: str,
    scan_start: int,
    scan_end: int,
    page_size: int,
) -> tuple[int, bool]:
    return _count_direct_interactions(
        w3,
        sender_address,
        to_address,
        scan_start,
        scan_end,
        page_size,
        root_only=True,
        mode_name="sender_direct",
    )


def _trace_touches_target(call_node: dict, target_norm: str) -> bool:
    to_addr = _normalize_address(call_node.get("to"))
    if to_addr == target_norm:
        return True

    calls = call_node.get("calls")
    if not isinstance(calls, list):
        return False
    for child in calls:
        if isinstance(child, dict) and _trace_touches_target(child, target_norm):
            return True
    return False


def _count_transitive_interactions(
    w3: Web3,
    from_address: str,
    to_address: str,
    scan_start: int,
    scan_end: int,
    page_size: int,
) -> int:
    try:
        from_checksum = Web3.to_checksum_address(from_address)
    except Exception:
        return 0
    target_norm = _normalize_address(to_address)
    if not target_norm:
        return 0

    tx_hashes: list[str] = []
    seen: set[str] = set()
    after = 0
    pages = 0
    seen_pages: set[tuple] = set()
    while True:
        if pages >= MAX_TRACE_PAGES_PER_CALL:
            print(
                "[warn] reached max pages in transitive scan; stopping early "
                f"from={from_address} to={to_address} after={after}"
            )
            break
        pages += 1
        params = {
            "fromBlock": _to_hex_block(scan_start),
            "toBlock": _to_hex_block(scan_end),
            "fromAddress": [from_checksum],
            "count": max(1, int(page_size)),
            "after": after,
        }
        try:
            traces = _trace_filter(w3, params, "transitive")
        except Exception:
            break

        if not isinstance(traces, list) or not traces:
            break
        fp = _page_fingerprint(traces)
        if fp in seen_pages:
            print(
                "[warn] repeated trace_filter page detected in transitive; "
                "stopping early"
            )
            break
        seen_pages.add(fp)

        for trace in traces:
            if not _is_allowed_trace_type(trace):
                continue
            tx_hash = _normalize_tx_hash(trace.get("transactionHash"))
            if not tx_hash or tx_hash in seen:
                continue
            seen.add(tx_hash)
            tx_hashes.append(tx_hash)

        if len(traces) < int(page_size):
            break
        after += len(traces)

    total = 0
    for tx_hash in tx_hashes:
        try:
            tree = w3.geth.debug.trace_transaction(
                tx_hash,
                {"tracer": "callTracer"},
            )
        except Exception:
            continue
        if isinstance(tree, dict) and _trace_touches_target(tree, target_norm):
            total += 1
    return total
