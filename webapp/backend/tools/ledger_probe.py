#!/usr/bin/env python3
"""Black-box probe of the Ledger Web3checks endpoint (crystal-clear on pellow).

Calls the public HTTPS URL with a known mainnet transaction and checks the
whole chain: 200, descriptor structure, ECDSA signature against the public
key registered with Ledger, tiny URL resolves, and an unsupported chain
answers 422 code 2. Silent on success. Notifies once when it starts failing
and once when it recovers (state file), never on every run.

cron: */10 * * * * flock -n ~/.cache/ledger-probe.lock ~/bin/ledger-probe.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

BASE = os.environ.get("LEDGER_PROBE_BASE", "https://api2.mab.xyz")
CONF = Path(os.environ.get("LEDGER_PROBE_DIR", Path.home() / ".config/crystal-clear"))
STATE = Path.home() / ".local/state/ledger-probe.failing"
NOTIFY = os.environ.get("LEDGER_PROBE_NOTIFY", str(Path.home() / "bin/mevgo-tg-notify.sh"))
# Burn address: funded, nonce 0 forever (nobody holds its key), so the
# probe never goes stale. Plain 0-value transfer, EIP-1559, chain 1.
FROM = "0x000000000000000000000000000000000000dEaD"
RAW = (
    "0x02e8018084773594008504a817c8008252089412345678901234567890123456789012345678908080c0"
    ""
)


def call(method: str, url: str, key: str | None = None, body: dict | None = None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Accept", "application/json")
    if key:
        req.add_header("X-API-Key", key)
    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(req, data=data, timeout=60) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except ValueError:
            return e.code, None


def read_der(buf: bytes, i: int):
    first = buf[i]
    if first < 0x80:
        return first, i + 1
    n = first & 0x7F
    return int.from_bytes(buf[i + 1 : i + 1 + n], "big"), i + 1 + n


def check() -> None:
    key = (CONF / "ledger-probe.key").read_text().strip()
    pub = (CONF / "ledger-public-key.hex").read_text().strip()
    status, js = call("POST", f"{BASE}/ethereum/scan/tx", key,
                      {"tx": {"from": FROM, "raw": RAW}, "chain": 1})
    assert status == 200, f"scan/tx -> HTTP {status} {js}"
    desc = bytes.fromhex(js["descriptor"][2:])
    assert js["public_key_id"] == "crystal_clear", "public_key_id"
    fields, i, signed = {}, 0, None
    while i < len(desc):
        start = i
        tag, i = read_der(desc, i)
        ln, i = read_der(desc, i)
        if tag == 0x15:
            sig, signed = desc[i : i + ln], desc[:start]
        fields[tag] = desc[i : i + ln]
        i += ln
    assert signed is not None, "no signature"
    ec.EllipticCurvePublicKey.from_encoded_point(
        ec.SECP256K1(), bytes.fromhex(pub)
    ).verify(sig, signed, ec.ECDSA(hashes.SHA256()))  # raises on mismatch
    assert fields[0x01] == b"\x09" and fields[0x02] == b"\x01", "structure/version"
    assert fields[0x23] == (1).to_bytes(8, "big"), "chain id"
    assert fields[0x22] == bytes.fromhex(FROM[2:]), "address"
    assert fields[0x84] == b"\x00", "simulation type"
    url = fields[0x83].decode()
    assert len(url) <= 30 and url.startswith(f"{BASE}/r/"), f"tiny url {url}"
    st, rep = call("GET", url)
    assert st == 200 and rep and "simulation" in rep, f"report {url} -> {st}"
    st, err = call("POST", f"{BASE}/ethereum/scan/tx", key,
                   {"tx": {"from": FROM, "raw": RAW}, "chain": 137})
    assert st == 422 and err and err.get("code") == 2, f"unsupported chain -> {st} {err}"


def notify(msg: str) -> None:
    try:
        subprocess.run([NOTIFY], input=msg.encode(), timeout=30, check=False)
    except Exception as exc:  # noqa: BLE001
        print(f"ledger-probe: notify failed: {exc}", file=sys.stderr)


def main() -> int:
    try:
        check()
    except Exception as exc:  # noqa: BLE001 - any failure is a probe failure
        reason = f"{type(exc).__name__}: {exc}"[:400]
        if not STATE.exists():
            STATE.parent.mkdir(parents=True, exist_ok=True)
            STATE.write_text(reason)
            notify(f"crystal-clear Ledger probe FAILING ({BASE}): {reason}")
        print(f"ledger-probe: FAIL {reason}", file=sys.stderr)
        return 1
    if STATE.exists():
        STATE.unlink()
        notify(f"crystal-clear Ledger probe recovered ({BASE})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
