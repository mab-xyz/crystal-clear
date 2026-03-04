from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers import health


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(health.router)
    return TestClient(app)


def test_health_check_ok():
    client = _build_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_eth_node_health_check_connected(monkeypatch):
    class _FakeWeb3:
        @staticmethod
        def HTTPProvider(_url):
            return object()

        def __init__(self, _provider):
            pass

        def is_connected(self):
            return True

    monkeypatch.setattr(health, "Web3", _FakeWeb3)
    client = _build_client()

    response = client.get("/health/eth-node")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "eth_node": "connected",
    }


def test_eth_node_health_check_exception(monkeypatch):
    class _BrokenWeb3:
        @staticmethod
        def HTTPProvider(_url):
            raise RuntimeError("boom")

    monkeypatch.setattr(health, "Web3", _BrokenWeb3)
    client = _build_client()

    response = client.get("/health/eth-node")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unhealthy"
    assert body["eth_node"] == "disconnected"
    assert "boom" in body["error"]
