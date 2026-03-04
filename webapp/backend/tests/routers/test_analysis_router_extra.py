from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

from src.api.core.database import get_session
from src.api.integrations.crystal_clear_adapter import get_risk_engine
from src.api.routers import analysis


class _Engine:
    def simulate_and_check(self, *_a, **_k):
        return {
            "0x3333333333333333333333333333333333333333": {
                "first_time": False,
                "verification": {"verification": "fully-verified"},
                "depth": 1,
                "types": {"CALL": 1},
            }
        }

    def simulate_from_tx(self, *_a, **_k):
        return {
            "0x3333333333333333333333333333333333333333": {
                "first_time": False,
                "verification": {"verification": "not-verified"},
                "depth": 1,
                "types": {"CALL": 1},
            }
        }



def _client() -> TestClient:
    app = FastAPI()
    app.include_router(analysis.router)
    app.dependency_overrides[get_risk_engine] = lambda: _Engine()
    app.dependency_overrides[get_session] = lambda: object()
    FastAPICache.init(InMemoryBackend(), prefix="test-cache")
    return TestClient(app)


# Confirms dependencies endpoint maps service graph output into API response.
def test_dependencies_endpoint(monkeypatch):
    monkeypatch.setattr(
        analysis,
        "analyze_contract_dependencies",
        lambda **_k: type(
            "Graph",
            (),
            {
                "model_dump": lambda self: {
                    "address": "0x1111111111111111111111111111111111111111",
                    "from_block": 1,
                    "to_block": 2,
                    "n_nodes": 1,
                    "nodes": {"0x1111111111111111111111111111111111111111": "A"},
                    "edges": [],
                    "dependency_depths": {},
                    "n_matching_transactions": 0,
                }
            },
        )(),
    )

    response = _client().get("/v1/analysis/0x1111111111111111111111111111111111111111/dependencies")

    assert response.status_code == 200
    assert response.json()["n_nodes"] == 1


# Confirms risk endpoint returns aggregated risk payload from service layer.
def test_risk_endpoint(monkeypatch):
    async def _fake_assess(*_a, **_k):
        return {
            "root_address": "0x1111111111111111111111111111111111111111",
            "from_block": None,
            "to_block": None,
            "dependencies": [],
            "aggregated_risks": {
                "verified": True,
                "risk_factors": {
                    "upgradeability": False,
                    "permissioned": False,
                    "repository": True,
                    "audits": True,
                    "scorecard": 8.0,
                },
                "details": None,
            },
        }

    monkeypatch.setattr(
        analysis,
        "assess_contract_risk",
        _fake_assess,
    )

    response = _client().get("/v1/analysis/0x1111111111111111111111111111111111111111/risk")

    assert response.status_code == 200
    assert response.json()["aggregated_risks"]["verified"] is True


# Marks tx hash response dangerous when verification result is not verified.
def test_tx_risk_by_hash_marks_dangerous_for_not_verified():
    response = _client().get(
        "/v1/analysis/tx-risk/0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "DANGEROUS"


# Enforces sender requirement for unsigned raw Type-1/2 transactions.
def test_tx_risk_raw_unsigned_requires_sender(monkeypatch):
    class _TypedTx:
        @staticmethod
        def from_bytes(_b):
            raise RuntimeError("typed fail")

    monkeypatch.setattr(analysis, "TypedTransaction", _TypedTx)
    monkeypatch.setattr(analysis.rlp, "decode", lambda _b: [b""] * 8)

    response = _client().post(
        "/v1/analysis/tx-risk-raw",
        json={"raw_tx": "0x01" + "00" * 10},
    )

    assert response.status_code == 422
    assert "sender_address" in response.json()["detail"]
