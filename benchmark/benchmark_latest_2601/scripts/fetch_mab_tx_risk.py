#!/usr/bin/env python3
"""Fetch tx-risk assessments for benchmark incidents via the MAB API."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests


TX_RE = re.compile(r"0x[0-9a-fA-F]{64}")


def extract_tx_hash(raw: Optional[str]) -> Optional[str]:
    """Return the tx hash from a raw hash or etherscan-style URL."""

    if not raw:
        return None
    raw = raw.strip()
    if TX_RE.fullmatch(raw):
        return raw.lower()
    if "/tx/" in raw:
        part = raw.split("/tx/", 1)[1]
        part = part.split("/", 1)[0]
        part = part.split("?", 1)[0]
        part = part.strip()
        if TX_RE.fullmatch(part):
            return part.lower()
    return None


def classify_response(payload: Dict[str, Any]) -> Tuple[str, str]:
    """Return (label, status) where label is danger/ok derived from API payload."""

    status = str(payload.get("status", "")).upper() or "UNKNOWN"
    if status in {"DANGEROUS", "WARNING", "ALERT"}:
        return "dangerous", status
    if status in {"OK", "SAFE", "CLEAN"}:
        return "ok", status

    details = payload.get("details") or []
    if isinstance(details, list):
        for item in details:
            if not isinstance(item, dict):
                continue
            if item.get("first_time"):
                return "dangerous", status
            verification = item.get("verification") or {}
            if isinstance(verification, dict):
                verdict = str(verification.get("verification", "")).lower()
                if verdict and verdict not in {"verified", "fully-verified"}:
                    return "dangerous", status
    return "ok", status


def iter_incident_txs(incident: Dict[str, Any]) -> Iterable[Tuple[str, str]]:
    """Yield (tx_type, raw_entry) for attack and normal txs in the incident."""

    attack = incident.get("attack_tx")
    if attack:
        yield "attack", attack
    for idx, normal in enumerate(incident.get("normal_txs") or []):
        yield f"normal[{idx}]", normal


def build_tx_risk_url(base: str, tx_hash: str) -> str:
    base = base.rstrip("/")
    if base.endswith("/tx-risk"):
        return f"{base}/{tx_hash}"
    if base.endswith("/tx-risk/"):
        return f"{base}{tx_hash}"
    return f"{base}/tx-risk/{tx_hash}"


def call_tx_risk_api(
    session: requests.Session,
    tx_hash: str,
    base_url: str,
    api_key: Optional[str],
    timeout: float,
    latest_offset: Optional[int],
) -> Dict[str, Any]:
    url = build_tx_risk_url(base_url, tx_hash)
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    params = None
    if latest_offset is not None:
        params = {"latest_offset": int(latest_offset)}
    resp = session.get(
        url,
        headers=headers,
        params=params,
        timeout=max(timeout, 0.1),
    )
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(
            f"HTTP {resp.status_code} calling {url}: {resp.text}"
        ) from exc
    return resp.json()


def process_incidents(
    incidents: List[Dict[str, Any]],
    base_url: str,
    api_key: Optional[str],
    timeout: float,
    sleep_s: float,
    dry_run: bool,
    latest_offset: Optional[int] = None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    session = requests.Session()
    try:
        for inc_idx, incident in enumerate(incidents, start=1):
            print(f"[info] Processing incident {inc_idx}/{len(incidents)}")
            name = incident.get("name") or "unknown"
            inc_id = (
                incident.get("id") or incident.get("incident_id") or f"idx-{inc_idx}"
            )
            for tx_type, raw_tx in iter_incident_txs(incident):
                tx_hash = extract_tx_hash(raw_tx)
                if not tx_hash:
                    results.append(
                        {
                            "incident_id": inc_id,
                            "incident_name": name,
                            "tx_type": tx_type,
                            "raw": raw_tx,
                            "classification": "skipped",
                            "status": "INVALID_TX",
                            "error": "Could not parse tx hash",
                        }
                    )
                    print(
                        f"[warn] {inc_id} {name} {tx_type}: invalid tx entry; skipping",
                        file=sys.stderr,
                    )
                    continue

                entry: Dict[str, Any] = {
                    "incident_id": inc_id,
                    "incident_name": name,
                    "tx_type": tx_type,
                    "tx_hash": tx_hash,
                    "raw": raw_tx,
                }

                if dry_run:
                    entry.update(
                        {
                            "classification": "dry-run",
                            "status": "DRY_RUN",
                        }
                    )
                    results.append(entry)
                    continue

                start_ts = time.perf_counter()
                try:
                    payload = call_tx_risk_api(
                        session,
                        tx_hash,
                        base_url,
                        api_key,
                        timeout,
                        latest_offset,
                    )
                except Exception as exc:  # noqa: BLE001 - want to surface all failures
                    duration = time.perf_counter() - start_ts
                    entry.update(
                        {
                            "classification": "skipped",
                            "status": "ERROR",
                            "error": str(exc),
                            "duration_s": duration,
                        }
                    )
                    results.append(entry)
                    print(
                        f"[warn] {inc_id} {name} {tx_type} {tx_hash}: {exc}; skipping after {duration:.3f}s",
                        file=sys.stderr,
                    )
                    continue

                label, status = classify_response(payload)
                duration = time.perf_counter() - start_ts
                entry.update(
                    {
                        "classification": label,
                        "status": status,
                        "analysis": payload,
                        "duration_s": duration,
                    }
                )
                results.append(entry)
                print(
                    f"[info] {inc_id} {name} {tx_type} {tx_hash}: completed in {duration:.3f}s status={status}",
                    file=sys.stderr,
                )
                if sleep_s > 0:
                    time.sleep(sleep_s)
    finally:
        session.close()
    return results


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Call https://api.mab.xyz/v1/analysis/tx-risk for benchmark txs",
    )
    parser.add_argument(
        "--input",
        default="4_ethereum_incidents_with_attack_and_normal_txs.json",
        help="Path to incidents JSON file",
    )
    parser.add_argument(
        "--output",
        default="results/mab_tx_risk_results.json",
        help="Path to store the collected results",
    )
    parser.add_argument(
        "--api-url",
        default="https://api.mab.xyz/v1/analysis/tx-risk",
        help="Base API URL (will have /{tx_hash} appended as needed)",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("MAB_API_KEY"),
        help="API key to send as X-API-Key",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=600.0,
        help="HTTP request timeout in seconds",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Optional delay in seconds between API calls",
    )
    parser.add_argument(
        "--latest-offset",
        type=int,
        default=500,
        help="Limit first-time checks to N latest blocks",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse incidents but skip API calls",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2

    with input_path.open("r") as src:
        incidents = json.load(src)
        if not isinstance(incidents, list):
            raise SystemExit("Input JSON must be a list of incidents")

    print(
        f"Loaded {len(incidents)} incidents from {input_path}; dry_run={args.dry_run}"
    )

    collected = process_incidents(
        incidents=incidents,
        base_url=args.api_url,
        api_key=args.api_key,
        timeout=args.timeout,
        sleep_s=args.sleep,
        dry_run=args.dry_run,
        latest_offset=args.latest_offset,
    )

    out_path = Path(args.output)
    if out_path.parent and not out_path.parent.exists():
        out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "api_url": args.api_url,
        "input": str(input_path),
        "count": len(collected),
        "results": collected,
    }
    with out_path.open("w") as dest:
        json.dump(payload, dest, indent=2)
    print(f"Wrote {len(collected)} entries to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
