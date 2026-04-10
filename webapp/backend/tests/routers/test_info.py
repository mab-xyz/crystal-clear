from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

from src.api.core.database import get_session
from src.api.routers import info


class _DummyVerificationData:
    def model_dump(self):
        return {
            "address": "0x1111111111111111111111111111111111111111",
            "verification": "verified",
            "verifiedAt": "na",
            "is_eip7702": False,
            "delegate_address": None,
        }


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(info.router)
    app.dependency_overrides[get_session] = lambda: object()
    FastAPICache.init(InMemoryBackend(), prefix="test-cache")
    return TestClient(app)


def test_get_latest_block(monkeypatch):
    monkeypatch.setattr(info, "get_latest_block_number", lambda: 123)
    client = _build_client()

    response = client.get("/info/block-latest")

    assert response.status_code == 200
    assert response.json() == {"block_number": 123}


def test_get_deployment_info(monkeypatch):
    monkeypatch.setattr(
        info,
        "get_deployment_data",
        lambda _session, _address: {
            "address": "0x1111111111111111111111111111111111111111",
            "deployer": "0x2222222222222222222222222222222222222222",
            "deployer_eoa": "0x3333333333333333333333333333333333333333",
            "tx_hash": "0xabc",
            "block_number": 42,
        },
    )
    client = _build_client()

    response = client.get(
        "/info/deployment/0x1111111111111111111111111111111111111111"
    )

    assert response.status_code == 200
    assert response.json()["block_number"] == 42


def test_get_verification_info(monkeypatch):
    monkeypatch.setattr(info, "get_verification_data", lambda _address: _DummyVerificationData())
    client = _build_client()

    response = client.get(
        "/info/verification/0x1111111111111111111111111111111111111111"
    )

    assert response.status_code == 200
    assert response.json()["verification"] == "verified"


def test_get_scorecard_info(monkeypatch):
    async def _fake_scorecard(_session, _address):
        return {
            "source": "api",
            "repo": "org/repo",
            "raw": {"score": 7.1, "date": "2025-01-01", "checks": []},
        }

    monkeypatch.setattr(info, "get_scorecard_data", _fake_scorecard)
    client = _build_client()

    response = client.get(
        "/info/reposcore/0x1111111111111111111111111111111111111111"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["repo_info"] == "org/repo"
    assert body["source"] == "public_api"
    assert body["score"] == 7.1


def test_get_permissions_info(monkeypatch):
    monkeypatch.setattr(
        info,
        "get_permissions_data",
        lambda _address: [{"function": "transfer(address,uint256)"}],
    )
    client = _build_client()

    response = client.get(
        "/info/permissions/0x1111111111111111111111111111111111111111"
    )

    assert response.status_code == 200
    assert response.json() == {
        "address": "0x1111111111111111111111111111111111111111",
        "functions": ["transfer(address,uint256)"],
    }
