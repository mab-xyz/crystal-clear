import logging
from typing import Any, Dict, List, Optional, Tuple


def _node(from_addr: Optional[str], to_addr: Optional[str], typ: str) -> Dict[str, Any]:
    return {
        "from": from_addr or "",
        "to": to_addr or "",
        "type": typ,
        "calls": [],
    }


def from_trace_call(traces: List[Dict[str, Any]], logger: Optional[logging.Logger] = None) -> Dict[str, Any]:
    """
    Normalize Erigon/OpenEthereum trace_call output to a call tree with
    fields: {"from", "to", "type", "calls": [ ... ]}.

    The input is expected to be a list of trace entries, each with keys like:
    - type: e.g., "call", "create", etc.
    - action: { from, to, callType, input, value, ... }
    - result: { address, output, gasUsed, ... } (for create)
    - traceAddress: list[int] representing the call depth path

    Returns a root node. If multiple roots are present, returns a synthetic
    root with those roots as children.
    """
    log = logger or logging.getLogger("TraceNormalizer")

    nodes: Dict[Tuple[int, ...], Dict[str, Any]] = {}
    roots: List[Dict[str, Any]] = []

    for tr in traces or []:
        ttype = str(tr.get("type", "")).upper()
        action = tr.get("action", {}) or {}
        trace_addr: Tuple[int, ...] = tuple(tr.get("traceAddress", []) or [])

        if ttype in {"CALL", "DELEGATECALL", "STATICCALL", "CALLCODE"}:
            src = action.get("from")
            dst = action.get("to")
            node = _node(src, dst, ttype)
        elif ttype in {"CREATE", "CREATE2"}:
            src = action.get("from")
            created = (tr.get("result") or {}).get("address")
            node = _node(src, created, ttype)
        else:
            # Not a call-like frame; skip
            continue

        nodes[trace_addr] = node
        if len(trace_addr) == 0:
            roots.append(node)

    # Link children to parents using traceAddress path prefix
    for path, node in nodes.items():
        if len(path) == 0:
            continue
        parent_path = path[:-1]
        parent = nodes.get(parent_path)
        if parent is not None:
            parent["calls"].append(node)
        else:
            # Orphaned node; attach to synthetic root later
            roots.append(node)

    if len(roots) == 1:
        return roots[0]

    # Synthetic root to host multiple top-level nodes
    synthetic_root = _node("", "", "ROOT")
    synthetic_root["calls"] = roots
    log.debug("Constructed synthetic root for %d roots", len(roots))
    return synthetic_root

