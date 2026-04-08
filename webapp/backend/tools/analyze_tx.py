#!/usr/bin/env python3
"""Analyze a single on-chain transaction by hash.

Usage:
    python tools/analyze_tx.py <tx_hash>
    python tools/analyze_tx.py --json <tx_hash>

Credentials are resolved in this order (first non-empty value wins):
    1. Environment variable
    2. Backend .env file
    3. System keyring  (service name: "crystal-clear", key: variable name)

To store credentials in the keyring:
    python -c "import keyring; keyring.set_password('crystal-clear', 'ETH_NODE_URLS', 'http://...')"
    python -c "import keyring; keyring.set_password('crystal-clear', 'ETHERSCAN_API_KEY', 'yourkey')"

Example (env vars):
    ETH_NODE_URLS=http://localhost:8545 ETHERSCAN_API_KEY=... \\
        python tools/analyze_tx.py 0xabc...
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Path / env setup (mirrors the pattern used by other tools in this directory)
# ---------------------------------------------------------------------------

TOOLS_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = TOOLS_DIR.parent

for _p in (str(BACKEND_ROOT), str(BACKEND_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _load_env() -> None:
    """Populate os.environ from backend .env file (if present)."""
    for candidate in (BACKEND_ROOT / ".env", BACKEND_ROOT / "api" / ".env"):
        if not candidate.exists():
            continue
        for line in candidate.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
        break


_load_env()


# ---------------------------------------------------------------------------
# Keyring helper
# ---------------------------------------------------------------------------

_KEYRING_SERVICE = "crystal-clear"


def _get_secret(name: str) -> str:
    """Return the value for *name*, checking env then system keyring."""
    value = os.environ.get(name, "")
    if value:
        return value
    try:
        import keyring  # optional dependency
        stored = keyring.get_password(_KEYRING_SERVICE, name)
        if stored:
            return stored
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# Core analysis helpers
# ---------------------------------------------------------------------------

SAFE_VERIFICATIONS = {"verified", "fully-verified"}


def _assess_status(results: dict) -> str:
    """Apply the same risk logic as the /tx-risk/{tx_hash} endpoint."""
    for info in results.values():
        if info.get("first_time", False):
            return "DANGEROUS"
        v = info.get("verification") or {}
        ver = str(v.get("verification", "")).lower() if isinstance(v, dict) else ""
        if ver not in SAFE_VERIFICATIONS:
            return "DANGEROUS"
    return "OK"


def _run(tx_hash: str, as_json: bool) -> None:
    from crystal_clear import CrystalClear

    eth_node_urls = _get_secret("ETH_NODE_URLS") or _get_secret("ETH_NODE_URL")
    if not eth_node_urls:
        sys.exit(
            "Error: ETH_NODE_URLS not found.\n"
            "Set it via environment variable, backend .env file, or keyring:\n"
            "  python -c \"import keyring; keyring.set_password"
            "('crystal-clear', 'ETH_NODE_URLS', 'http://...')\""
        )

    etherscan_key = _get_secret("ETHERSCAN_API_KEY")
    allium_key = _get_secret("ALLIUM_API_KEY")

    client = CrystalClear(
        url=eth_node_urls.split(",")[0].strip(),
        etherscan_api_key=etherscan_key,
        allium_api_key=allium_key,
        log_level=os.environ.get("LOG_LEVEL", "ERROR"),
    )

    results = client.simulate_from_tx(tx_hash)
    status = _assess_status(results)

    if as_json:
        output = {
            "tx_hash": tx_hash,
            "status": status,
            "contracts": [
                {
                    "address": addr,
                    "depth": info.get("depth"),
                    "first_time": info.get("first_time", False),
                    "verification": info.get("verification"),
                    "types": info.get("types"),
                }
                for addr, info in results.items()
            ],
        }
        print(json.dumps(output, indent=2))
        return

    # Human-readable output
    print(f"Transaction : {tx_hash}")
    print(f"Status      : {status}")
    print()

    if not results:
        print("No contract interactions found (plain ETH transfer to EOA).")
        return

    print(f"{'Address':<44}  {'Depth':>5}  {'First?':>6}  {'Verification':<16}  Types")
    print("-" * 100)
    for addr, info in sorted(results.items(), key=lambda kv: (kv[1].get("depth") or 0, kv[0])):
        v = info.get("verification") or {}
        ver = v.get("verification", "unknown") if isinstance(v, dict) else str(v)
        types_str = ", ".join(
            f"{k}×{n}" for k, n in (info.get("types") or {}).items()
        ) or "—"
        first = "YES" if info.get("first_time", False) else "no"
        depth = info.get("depth", "?")
        print(f"{addr:<44}  {depth:>5}  {first:>6}  {ver:<16}  {types_str}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze an on-chain Ethereum transaction for contract risk.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("tx_hash", help="Transaction hash (0x-prefixed, 66 chars)")
    parser.add_argument(
        "--json", dest="as_json", action="store_true", help="Output raw JSON"
    )
    args = parser.parse_args()

    tx = args.tx_hash.strip().lower()
    if not (tx.startswith("0x") and len(tx) == 66 and all(c in "0123456789abcdef" for c in tx[2:])):
        sys.exit(f"Error: invalid tx hash: {args.tx_hash!r}")

    _run(tx, args.as_json)


if __name__ == "__main__":
    main()
