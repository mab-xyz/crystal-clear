#!/usr/bin/env python3
"""Tiny helper to test the tx-risk endpoint manually."""

from __future__ import annotations

import argparse
import json
import sys
from urllib import error, parse, request
from datetime import datetime
from typing import Optional


from fetch_mab_tx_risk import build_tx_risk_url, extract_tx_hash


def call_endpoint(
    base_url: str, tx_hash: str, api_key: str, latest_offset: Optional[int] | None
) -> dict:
    url = build_tx_risk_url(base_url, tx_hash)
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    params = None
    if latest_offset is not None:
        params = {"latest_offset": int(latest_offset)}
    if params:
        query = parse.urlencode(params)
        url = f"{url}?{query}"
    req = request.Request(url, headers=headers, method="GET")
    with request.urlopen(req, timeout=600.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Interactive tx-risk tester (enter tx hash/URL per line)",
    )
    parser.add_argument(
        "--api-url",
        default="https://api.mab.xyz/v1/analysis/tx-risk",
        help="Base endpoint to call",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional API key to send as X-API-Key",
    )
    # add latest-offset arg for compatibility
    parser.add_argument(
        "--latest-offset",
        type=int,
        default=100,
        help="Limit first-time checks to N latest blocks",
    )
    args = parser.parse_args()

    print("Enter tx hash or etherscan URL (blank line to exit):")
    while True:
        raw = input("> ").strip()
        if not raw:
            break
        tx_hash = extract_tx_hash(raw)
        if not tx_hash:
            print("Could not parse tx hash, try again", file=sys.stderr)
            continue

        try:
            start_time = datetime.now()
            resp = call_endpoint(
                args.api_url, tx_hash, args.api_key, args.latest_offset
            )
            endtime = datetime.now()
            duration = (endtime - start_time).total_seconds()
            print(f"[info] Call completed in {duration:.3f}s", file=sys.stderr)
        except error.HTTPError as exc:
            print(
                f"HTTP {exc.code}: {exc.read().decode('utf-8', 'ignore')}",
                file=sys.stderr,
            )
            continue
        except error.URLError as exc:
            print(f"Network error: {exc}", file=sys.stderr)
            continue
        status = resp.get("status", "?")
        summary = resp.get("summary") or resp.get("message") or "(no summary)"
        print(f"[{status}] {tx_hash}: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
