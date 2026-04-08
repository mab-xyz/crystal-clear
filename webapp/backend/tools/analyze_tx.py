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

TOOLS_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = TOOLS_DIR.parent

for _p in (str(BACKEND_ROOT), str(BACKEND_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Load .env before any module that reads settings.  Import the service module
# directly — it has no heavy dependencies so it works without a full .env.
from src.api.services.tx_risk_assessment import _has_unverified_dangerous  # noqa: E402

_ENV_LOADED = False


def _load_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
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
    _ENV_LOADED = True


_load_env()

# ---------------------------------------------------------------------------
# Keyring helper — CLI-only, not in backend
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
# Analysis + display
# ---------------------------------------------------------------------------

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

    client = CrystalClear(
        url=eth_node_urls.split(",")[0].strip(),
        etherscan_api_key=_get_secret("ETHERSCAN_API_KEY"),
        allium_api_key=_get_secret("ALLIUM_API_KEY"),
        log_level=os.environ.get("LOG_LEVEL", "ERROR"),
    )

    raw = client.simulate_from_tx(tx_hash)

    # Defense-in-depth: the SDK fix excludes EOA roots, but if an unpatched SDK
    # returns one (root, no types, no bytecode), mark verification "n-a" so the
    # backend helper does not flag it as an unverified contract.
    sc = getattr(client, "simulation_collector", None)
    items = []
    for addr, info in raw.items():
        ver_dict = info.get("verification") if isinstance(info.get("verification"), dict) else {}
        if (
            info.get("types") is None
            and ver_dict.get("verification") not in {"verified", "fully-verified"}
            and sc
            and not sc._validate_contract(addr, "latest")
        ):
            info = {**info, "verification": "n-a"}
        items.append({"address": addr, **info})

    contract_items = [it for it in items if it.get("verification") != "n-a"]
    status = (
        "DANGEROUS"
        if any(it.get("first_time") for it in contract_items)
        or _has_unverified_dangerous(contract_items)
        else "OK"
    )

    if as_json:
        print(json.dumps({
            "tx_hash": tx_hash,
            "status": status,
            "contracts": [
                {
                    "address": it["address"],
                    "depth": it.get("depth"),
                    "first_time": it.get("first_time", False),
                    "verification": it.get("verification"),
                    "types": it.get("types"),
                }
                for it in items
            ],
        }, indent=2))
        return

    print(f"Transaction : {tx_hash}")
    print(f"Status      : {status}")
    print()

    if not items:
        print("No contract interactions found (plain ETH transfer to EOA).")
        return

    print(f"{'Address':<44}  {'Depth':>5}  {'First?':>6}  {'Verification':<16}  Types")
    print("-" * 100)
    for it in sorted(items, key=lambda x: (x.get("depth") or 0, x["address"])):
        raw_ver = it.get("verification")
        ver = (
            "n-a" if raw_ver == "n-a"
            else raw_ver.get("verification", "unknown") if isinstance(raw_ver, dict)
            else str(raw_ver) if raw_ver is not None else "unknown"
        )
        types_str = ", ".join(f"{k}×{n}" for k, n in (it.get("types") or {}).items()) or "—"
        print(f"{it['address']:<44}  {it.get('depth', '?'):>5}  "
              f"{'YES' if it.get('first_time') else 'no':>6}  {ver:<16}  {types_str}")


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
    parser.add_argument("--json", dest="as_json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    tx = args.tx_hash.strip().lower()
    if not (tx.startswith("0x") and len(tx) == 66 and all(c in "0123456789abcdef" for c in tx[2:])):
        sys.exit(f"Error: invalid tx hash: {args.tx_hash!r}")

    _run(tx, args.as_json)


if __name__ == "__main__":
    main()
