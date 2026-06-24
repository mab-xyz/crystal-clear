import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.core.database import get_session
from src.api.integrations.crystal_clear_adapter import get_risk_engine
from src.api.routers import analysis

_TX_HASH = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_SENDER = "0x1111111111111111111111111111111111111111"
_CONTRACT = "0x2222222222222222222222222222222222222222"
_BLOCK = 21000000

_FAKE_TX = {
    "from": _SENDER,
    "to": _CONTRACT,
    "input": b"",
    "value": 0,
    "gas": 21000,
    "gasPrice": 1000000000,
    "blockNumber": _BLOCK,
    "type": 0,
}


class _FakeRiskEngine:
    def __init__(self, tx=None, simulate_result=None, raise_get_tx=False):
        self._tx = tx if tx is not None else _FAKE_TX
        self._simulate_result = simulate_result or {
            _CONTRACT: {
                "verification": {"verification": "verified"},
                "depth": 1,
                "types": {"CALL": 1},
                "is_eip7702": False,
                "delegate_address": None,
            }
        }
        self._raise_get_tx = raise_get_tx

    def get_transaction(self, tx_hash):
        if self._raise_get_tx:
            raise RuntimeError("node unavailable")
        return self._tx

    def simulate_and_check(self, call_object, **kwargs):
        self._last_call = (call_object, kwargs)
        return self._simulate_result


def _build_client(engine=None) -> TestClient:
    app = FastAPI()
    app.include_router(analysis.router)
    app.dependency_overrides[get_risk_engine] = lambda: (
        engine if engine is not None else _FakeRiskEngine()
    )
    app.dependency_overrides[get_session] = lambda: object()
    return TestClient(app)


def _patch_interaction_helpers(
    monkeypatch,
    contract_dangerous_types=None,
    sender_dangerous_types=None,
    contract_missing_types=None,
    sender_missing_types=None,
    interaction_first_time=None,
    interaction_state=None,
):
    monkeypatch.setattr(analysis, "seed_interaction_scan_state_from_tx", lambda **_k: 0)
    monkeypatch.setattr(
        analysis,
        "_evaluate_interaction_scan_risk",
        lambda **_k: (
            interaction_first_time or {},
            interaction_state or {},
            contract_dangerous_types or [],
            sender_dangerous_types or [],
            contract_missing_types or [],
            sender_missing_types or [],
        ),
    )


def test_tx_risk_hash_invalid_hash():
    client = _build_client()
    response = client.get("/v1/analysis/tx-risk-hash/not-a-hash")
    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid tx_hash format"


def test_tx_risk_hash_get_transaction_failure():
    engine = _FakeRiskEngine(raise_get_tx=True)
    client = _build_client(engine)
    response = client.get(f"/v1/analysis/tx-risk-hash/{_TX_HASH}")
    assert response.status_code == 422
    assert "Failed to fetch transaction" in response.json()["detail"]


def test_tx_risk_hash_ok_status(monkeypatch):
    _patch_interaction_helpers(monkeypatch)
    client = _build_client()
    response = client.get(f"/v1/analysis/tx-risk-hash/{_TX_HASH}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"
    assert isinstance(data["details"], list)
    assert len(data["details"]) == 1
    assert data["details"][0]["address"] == _CONTRACT


def test_tx_risk_hash_dangerous_first_time(monkeypatch):
    _patch_interaction_helpers(
        monkeypatch,
        contract_dangerous_types=["contract_direct"],
        interaction_first_time={_CONTRACT.lower(): {"contract_direct": True}},
        interaction_state={_CONTRACT.lower(): {"contract_direct": "FOUND"}},
    )
    client = _build_client()
    response = client.get(f"/v1/analysis/tx-risk-hash/{_TX_HASH}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DANGEROUS"
    assert data["danger_reason"] == "FIRST_TIME_INTERACTION"


def test_tx_risk_hash_dangerous_unverified(monkeypatch):
    engine = _FakeRiskEngine(
        simulate_result={
            _CONTRACT: {
                "verification": {"verification": "not-verified"},
                "depth": 1,
                "types": {"CALL": 1},
                "is_eip7702": False,
                "delegate_address": None,
            }
        }
    )
    _patch_interaction_helpers(monkeypatch)
    client = _build_client(engine)
    response = client.get(f"/v1/analysis/tx-risk-hash/{_TX_HASH}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DANGEROUS"
    assert data["danger_reason"] == "UNVERIFIED"


def test_tx_risk_hash_uses_tx_block_tag(monkeypatch):
    _patch_interaction_helpers(monkeypatch)
    engine = _FakeRiskEngine()
    client = _build_client(engine)
    client.get(f"/v1/analysis/tx-risk-hash/{_TX_HASH}")
    call_object, kwargs = engine._last_call
    assert kwargs["block_tag"] == hex(_BLOCK)
    assert kwargs["to_block"] == hex(_BLOCK - 1)


def test_tx_risk_hash_response_shape_matches_tx_risk_raw(monkeypatch):
    """Verify the response includes the same top-level fields as tx-risk-raw."""
    _patch_interaction_helpers(monkeypatch)
    client = _build_client()
    response = client.get(f"/v1/analysis/tx-risk-hash/{_TX_HASH}")
    assert response.status_code == 200
    data = response.json()
    for field in ("status", "interaction_status", "details", "dangerous_interaction_types", "danger_reason", "ok_reason"):
        assert field in data, f"Missing field: {field}"
    item = data["details"][0]
    for field in ("address", "verification", "depth", "types", "first_time", "interaction_first_time", "interaction_state"):
        assert field in item, f"Missing item field: {field}"


def test_tx_risk_hash_missing_block_number_uses_latest(monkeypatch):
    tx_no_block = {**_FAKE_TX, "blockNumber": None}
    engine = _FakeRiskEngine(tx=tx_no_block)
    _patch_interaction_helpers(monkeypatch)
    client = _build_client(engine)
    response = client.get(f"/v1/analysis/tx-risk-hash/{_TX_HASH}")
    assert response.status_code == 200
    _, kwargs = engine._last_call
    assert kwargs["block_tag"] == "latest"
    assert kwargs["to_block"] is None
