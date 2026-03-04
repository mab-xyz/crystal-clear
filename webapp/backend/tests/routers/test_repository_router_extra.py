from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.core.database import get_session
from src.api.core.security import require_admin_if_enabled
from src.api.routers import repository


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(repository.router)
    app.dependency_overrides[require_admin_if_enabled] = lambda: {"admin": True}
    app.dependency_overrides[get_session] = lambda: object()
    return TestClient(app)


def test_create_repository_value_error(monkeypatch):
    monkeypatch.setattr(
        repository.crud,
        "create_repository",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("dup")),
    )
    client = _build_client()

    response = client.post(
        "/repository/",
        json={"protocol": "p", "version": None, "url": "u"},
    )

    assert response.status_code == 400


def test_create_repository_internal_error(monkeypatch):
    monkeypatch.setattr(
        repository.crud,
        "create_repository",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    client = _build_client()

    response = client.post(
        "/repository/",
        json={"protocol": "p", "version": None, "url": "u"},
    )

    assert response.status_code == 500


def test_update_repository_value_error(monkeypatch):
    monkeypatch.setattr(
        repository.crud,
        "update_repository",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("bad")),
    )
    client = _build_client()

    response = client.put("/repository/p", json={"url": "new"})

    assert response.status_code == 400
