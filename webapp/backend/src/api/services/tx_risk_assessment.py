"""Lightweight risk-assessment helpers shared by the router and CLI tools.

This module has no heavy dependencies so it can be imported without a full
backend settings environment.
"""

from __future__ import annotations


def _has_unverified_dangerous(items: list[dict]) -> bool:
    """Return True if any item in the call chain has unverified contract code.

    An unverified contract is dangerous regardless of whether it is a
    first-time interaction: interacting with unverified code is always risky.
    Verified contracts that are first-time interactions are handled separately
    via contract_dangerous_types / FIRST_TIME_INTERACTION.
    """
    for item in items:
        v = item.get("verification") or {}
        ver = str(v.get("verification", "")).lower() if isinstance(v, dict) else ""
        if ver not in {"verified", "fully-verified"}:
            return True
    return False
