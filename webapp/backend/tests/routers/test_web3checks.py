import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src.api.core.config import settings
from src.api.core.database import get_session
from src.api.integrations.crystal_clear_adapter import get_risk_engine
from src.api.models.ledger_report import LedgerReport
from src.api.routers import analysis, web3checks
from src.api.services import ledger_descriptor as ld
from src.api.services import ledger_hashing as lh
from src.api.services import ledger_reports

FIX = Path(__file__).parent.parent / "fixtures"
KEY_HEX = "22" * 32
CONTRACT = "0x282a7d13152b3f51a3e31d46a2ca563f8554d85d"


class Engine:
    def __init__(self, verification="verified", fail=False):
        self.verification = verification
        self.fail = fail
        self.calls = []

    def get_latest_block_number(self):
        return 21680884

    def simulate_and_check_with_edges(self, call_object, **kw):
        self.calls.append((call_object, kw))
        if self.fail:
            raise RuntimeError("node down")
        return (
            {
                CONTRACT: {
                    "verification": {"verification": self.verification},
                    "depth": 1,
                    "types": {"CALL": 1},
                }
            },
            [],
        )


@pytest.fixture
def ctx(monkeypatch):
    db = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(db)
    monkeypatch.setattr(settings, "ledger_signer_private_key_hex", KEY_HEX)
    monkeypatch.setattr(settings, "ledger_report_base_url", "https://api2.mab.xyz/r")
    state = {"contract_dangerous": []}
    monkeypatch.setattr(
        analysis,
        "_evaluate_interaction_scan_risk",
        lambda **_k: ({}, {}, state["contract_dangerous"], [], [], []),
    )
    engine = Engine()
    app = FastAPI()
    app.include_router(web3checks.router)
    app.include_router(web3checks.public_router)

    def _session():
        with Session(db) as s:
            yield s

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_risk_engine] = lambda: engine
    return TestClient(app), engine, state, db


PUB = ld.public_key_compressed_hex(ld.load_private_key(KEY_HEX))


def _tx():
    return json.loads((FIX / "ledger_eth_tx.json").read_text())


def _parsed(resp):
    desc = bytes.fromhex(resp.json()["descriptor"][2:])
    assert ld.verify_descriptor(desc, PUB)
    return ld.parse_descriptor(desc)


def test_eth_tx_benign(ctx):
    client, engine, _, _ = ctx
    body = _tx()
    r = client.post("/ethereum/scan/tx", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["block"] == body["block"]
    assert r.json()["public_key_id"] == settings.ledger_public_key_id
    p = _parsed(r)
    assert p[ld.TX_HASH] == lh.evm_tx_hash(body["tx"]["raw"])
    assert p[ld.CHAIN_ID] == (1).to_bytes(8, "big")
    assert p[ld.ADDRESS] == lh.evm_address_bytes(body["tx"]["from"])
    assert p[ld.W3C_NORMALIZED_RISK] == b"\x00"
    assert p[ld.W3C_NORMALIZED_CATEGORY] == b"\x00"
    assert p[ld.W3C_SIMULATION_TYPE] == b"\x00"
    assert len(p[ld.W3C_TINY_URL]) <= 30
    assert engine.calls[0][1]["block_tag"] == hex(body["block"])


def test_eth_tx_latest_block_resolved(ctx):
    client, *_ = ctx
    body = _tx()
    del body["block"]
    r = client.post("/ethereum/scan/tx", json=body)
    assert r.status_code == 200 and r.json()["block"] == 21680884


def test_eth_tx_first_time_contract_is_risk(ctx):
    client, _, state, _ = ctx
    state["contract_dangerous"] = ["contract_direct"]
    p = _parsed(client.post("/ethereum/scan/tx", json=_tx()))
    assert p[ld.W3C_NORMALIZED_RISK] == b"\x01"
    assert p[ld.W3C_NORMALIZED_CATEGORY] == b"\x03"


def test_eth_tx_unverified_is_threat(ctx):
    client, engine, _, _ = ctx
    engine.verification = "not-verified"
    p = _parsed(client.post("/ethereum/scan/tx", json=_tx()))
    assert p[ld.W3C_NORMALIZED_RISK] == b"\x02"
    assert p[ld.W3C_NORMALIZED_CATEGORY] == b"\x03"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda b: b.pop("chain"),
        lambda b: b.pop("tx"),
        lambda b: b["tx"].update(raw="0xzz"),
        lambda b: b["tx"].update({"from": "0x1234"}),
    ],
)
def test_bad_requests_are_400(ctx, mutate):
    client, *_ = ctx
    body = _tx()
    mutate(body)
    r = client.post("/ethereum/scan/tx", json=body)
    assert r.status_code == 400, r.text
    assert "message" in r.json()


def test_unsupported_chain_is_422_code_2(ctx):
    client, *_ = ctx
    body = _tx()
    body["chain"] = 137
    r = client.post("/ethereum/scan/tx", json=body)
    assert r.status_code == 422 and r.json()["code"] == 2


def test_unknown_family_is_422_code_2(ctx):
    client, *_ = ctx
    r = client.post("/bitcoin/scan/tx", json=_tx())
    assert r.status_code == 422 and r.json()["code"] == 2


def test_solana_is_422_code_2_but_bad_input_is_400(ctx):
    client, *_ = ctx
    good = {
        "tx": {"from": "11111111111111111111111111111111", "raw": "3Bxs4h"},
        "chain": 900,
    }
    r = client.post("/solana/scan/tx", json=good)
    assert r.status_code == 422 and r.json()["code"] == 2
    bad = {"tx": {"from": "0OIl", "raw": "3Bxs4h"}, "chain": 900}
    assert client.post("/solana/scan/tx", json=bad).status_code == 400


def test_signer_missing_and_engine_failure_are_500_code_100(ctx, monkeypatch):
    client, engine, _, _ = ctx
    engine.fail = True
    r = client.post("/ethereum/scan/tx", json=_tx())
    assert r.status_code == 500 and r.json()["code"] == 100
    monkeypatch.setattr(settings, "ledger_signer_private_key_hex", None)
    r = client.post("/ethereum/scan/tx", json=_tx())
    assert r.status_code == 500 and r.json()["code"] == 100


def test_eip712_seaport(ctx):
    client, engine, _, _ = ctx
    body = json.loads((FIX / "ledger_eip712_seaport.json").read_text())
    r = client.post("/ethereum/scan/eip-712", json=body)
    assert r.status_code == 200, r.text
    p = _parsed(r)
    dom, msg = lh.eip712_hashes(body["msg"]["data"])
    assert p[ld.DOMAIN_HASH] == dom and p[ld.TX_HASH] == msg
    assert ld.CHAIN_ID not in p
    assert p[ld.W3C_SIMULATION_TYPE] == b"\x01"
    assert engine.calls[0][0]["to"].lower() == (
        body["msg"]["data"]["domain"]["verifyingContract"]
    )


def test_eip712_other_chain_and_bad_input(ctx):
    client, *_ = ctx
    body = json.loads((FIX / "ledger_eip712_seaport.json").read_text())
    body["msg"]["data"]["domain"]["chainId"] = "137"
    r = client.post("/ethereum/scan/eip-712", json=body)
    assert r.status_code == 422 and r.json()["code"] == 2
    del body["msg"]["data"]["primaryType"]
    assert client.post("/ethereum/scan/eip-712", json=body).status_code == 400


def test_report_url_serves_stored_simulation(ctx):
    client, *_ = ctx
    r = client.post("/ethereum/scan/tx", json=_tx())
    url = ld.parse_descriptor(bytes.fromhex(r.json()["descriptor"][2:]))[
        ld.W3C_TINY_URL
    ].decode()
    rid = url.rsplit("/", 1)[1]
    assert len(rid) == 7
    assert len(settings.ledger_report_base_url + '/' + rid) <= 30
    got = client.get(f"/r/{rid}")
    assert got.status_code == 200 and got.json()["block"] == 21680884
    html = client.get(f"/r/{rid}", headers={"accept": "text/html"})
    assert html.headers["content-type"].startswith("text/html")
    assert client.get("/r/nope").status_code == 404


def test_rolling_purge(ctx):
    _, _, _, db = ctx
    now = datetime(2026, 10, 15)
    with Session(db) as s:
        for rid, age in (("old", 31), ("fresh", 29), ("edge", 30)):
            ledger_reports.store_report(
                s, family="ethereum", kind="tx", block=1,
                request_json={}, simulation_json={}, report_id=rid,
            )
            row = s.get(LedgerReport, rid)
            row.last_accessed_at = now - timedelta(days=age, minutes=-1)
            s.add(row)
        s.commit()
        # accessing "old" bumps its window, so it survives
        s.get(LedgerReport, "old").last_accessed_at = now - timedelta(days=31)
        s.commit()
        ledger_reports.get_report(s, "old", now=now)
        assert ledger_reports.purge_expired(s, 30, now=now) == 0
        row = s.get(LedgerReport, "fresh")
        row.last_accessed_at = now - timedelta(days=31)
        s.add(row)
        s.commit()
        assert ledger_reports.purge_expired(s, 30, now=now) == 1
        assert s.get(LedgerReport, "fresh") is None
        assert s.get(LedgerReport, "old") is not None
