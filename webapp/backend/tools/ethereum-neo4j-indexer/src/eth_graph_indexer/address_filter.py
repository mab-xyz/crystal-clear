"""Ethereum address normalization."""

from __future__ import annotations

import re

ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def normalize_address(value: str | None) -> str | None:
    if value is None:
        return None
    address = value.strip()
    if not ADDRESS_RE.fullmatch(address):
        raise ValueError(
            f"invalid Ethereum address {value!r}; expected 0x plus 40 hex characters"
        )
    return address.lower()
