from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.core.database import get_session
from src.api.core.security import require_admin_if_enabled
from src.api.routers import repository


_NOW = datetime.utcnow()


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(repository.router)
    app.dependency_overrides[require_admin_if_enabled] = lambda: {"admin": True}
    app.dependency_overrides[get_session] = lambda: object()
    return TestClient(app)


def _repo_payload(protocol: str = "uniswap") -> dict:
    return {
        "protocol": protocol,
        "version": None,
        "url": "https://github.com/org/repo",
        "date_added": _NOW,
        "last_updated": _NOW,
    }


def test_create_repository(monkeypatch):
    monkeypatch.setattr(
        repository.crud,
        "create_repository",
        lambda _s, _in: _repo_payload(),
    )
    client = _build_client()

    response = client.post(
        "/repository/",
        json={
            "protocol": "uniswap",
            "version": None,
            "url": "https://github.com/org/repo",
        },
    )

    assert response.status_code == 201
    assert response.json()["protocol"] == "uniswap"


def test_get_repository_not_found(monkeypatch):
    monkeypatch.setattr(repository.crud, "get_repository", lambda *_a, **_k: None)
    client = _build_client()

    response = client.get("/repository/uniswap")

    assert response.status_code == 404
    assert response.json()["detail"] == "Repository not found"


def test_list_repositories(monkeypatch):
    monkeypatch.setattr(
        repository.crud,
        "get_repositories",
        lambda *_a, **_k: [_repo_payload()],
    )
    client = _build_client()

    response = client.get("/repository/")

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_delete_repository_not_found(monkeypatch):
    monkeypatch.setattr(repository.crud, "delete_repository", lambda *_a, **_k: False)
    client = _build_client()

    response = client.delete("/repository/uniswap")

    assert response.status_code == 404
    assert response.json()["detail"] == "Repository not found"
