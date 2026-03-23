#!/usr/bin/env python3
"""Compatibility wrapper for backfill_first_time_interactions core module."""

from __future__ import annotations

import sys
from pathlib import Path
import backfill_first_time_interactions_core as _core


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


# Keep monkeypatch compatibility for tests that mutate this module constant.
MAX_TRACE_PAGES_PER_CALL = _core.MAX_TRACE_PAGES_PER_CALL

# Re-export all core symbols, including underscore-prefixed helpers.
for _name in dir(_core):
    if _name.startswith("__"):
        continue
    globals().setdefault(_name, getattr(_core, _name))


def _count_contract_direct_interactions(
    w3,
    from_address: str,
    to_address: str,
    scan_start: int,
    scan_end: int,
    page_size: int,
):
    _core.MAX_TRACE_PAGES_PER_CALL = MAX_TRACE_PAGES_PER_CALL
    return _core._count_contract_direct_interactions(
        w3,
        from_address,
        to_address,
        scan_start,
        scan_end,
        page_size,
    )


def _count_sender_direct_interactions(
    w3,
    sender_address: str,
    to_address: str,
    scan_start: int,
    scan_end: int,
    page_size: int,
):
    _core.MAX_TRACE_PAGES_PER_CALL = MAX_TRACE_PAGES_PER_CALL
    return _core._count_sender_direct_interactions(
        w3,
        sender_address,
        to_address,
        scan_start,
        scan_end,
        page_size,
    )


if __name__ == "__main__":
    _core.main()
