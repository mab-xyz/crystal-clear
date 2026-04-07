from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.core.database import get_session
from src.api.integrations.crystal_clear_adapter import get_risk_engine
from src.api.routers import analysis


class _FakeRiskEngine:
    def simulate_and_check(self, *_args, **_kwargs):
        return {
            "0x3333333333333333333333333333333333333333": {
                "verification": {"verification": "verified"},
                "depth": 1,
                "types": {"CALL": 1},
            }
        }

    def simulate_from_tx(self, *_args, **_kwargs):
        return {
            "0x3333333333333333333333333333333333333333": {
                "first_time": True,
                "verification": {"verification": "verified"},
                "depth": 1,
                "types": {"CALL": 1},
            }
        }


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(analysis.router)
    app.dependency_overrides[get_risk_engine] = lambda: _FakeRiskEngine()
    app.dependency_overrides[get_session] = lambda: object()
    return TestClient(app)


# Ensures /tx-risk returns OK when interaction scan reports no dangerous types.
def test_tx_risk_post_success(monkeypatch):
    monkeypatch.setattr(
        analysis,
        "seed_interaction_scan_state_from_tx",
        lambda **_k: 0,
    )
    monkeypatch.setattr(
        analysis,
        "_evaluate_interaction_scan_risk",
        lambda **_k: ({}, {}, [], [], [], []),
    )
    client = _build_client()
    response = client.post(
        "/v1/analysis/tx-risk",
        json={
            "from_addr": "0x1111111111111111111111111111111111111111",
            "to_addr": "0x2222222222222222222222222222222222222222",
            "data": "0x",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "OK"


# Rejects invalid transaction hash format with HTTP 422.
def test_tx_risk_by_hash_invalid_hash():
    client = _build_client()

    response = client.get("/v1/analysis/tx-risk/not-a-hash")

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid tx_hash format"


# Marks tx hash analysis as dangerous when first-time interaction is flagged.
def test_tx_risk_by_hash_marks_dangerous_when_first_time():
    client = _build_client()

    response = client.get(
        "/v1/analysis/tx-risk/0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "DANGEROUS"


# Rejects malformed raw transaction payload before decode/simulation.
def test_tx_risk_raw_rejects_invalid_hex():
    client = _build_client()

    response = client.post("/v1/analysis/tx-risk-raw", json={"raw_tx": "oops"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid raw_tx hex format"
