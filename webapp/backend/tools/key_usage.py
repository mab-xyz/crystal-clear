#!/usr/bin/env python3
"""Request counts per API key file, using each key's own /keys/usage/me.

One line per key file in ~/.config/crystal-clear/keys/*.json (no admin key
needed). Silent when there are no key files.

usage: key_usage.py [--days N] [--base URL] [--json]
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--base", default="https://api2.mab.xyz")
    ap.add_argument("--dir", default=str(Path.home() / ".config/crystal-clear/keys"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rows = []
    for f in sorted(Path(a.dir).glob("*.json")):
        meta = json.loads(f.read_text())
        req = urllib.request.Request(
            f"{a.base}/keys/usage/me?days={a.days}", headers={"X-API-Key": meta["key"]}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            u = json.load(r)
        rows.append({
            "name": meta["name"], "environment": meta.get("environment"),
            "created_at": meta.get("created_at"), "days": a.days,
            "total": u["total"], "scan": u["scan"], "2xx": u["ok_2xx"],
            "4xx": u["client_error_4xx"], "5xx": u["server_error_5xx"],
            "by_day": u["by_day"],
        })
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    for r in rows:
        print(f"{r['name']} last{a.days}d total={r['total']} scan={r['scan']} "
              f"2xx={r['2xx']} 4xx={r['4xx']} 5xx={r['5xx']} created={r['created_at']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
