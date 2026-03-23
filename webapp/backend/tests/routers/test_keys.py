from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.core.database import get_session
from src.api.core.security import require_admin_api_key
from src.api.routers import keys


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(keys.router)
    app.dependency_overrides[require_admin_api_key] = lambda: {"admin": True}
    app.dependency_overrides[get_session] = lambda: object()
    return TestClient(app)


def test_create_key(monkeypatch):
    monkeypatch.setattr(
        keys,
        "create_api_key",
        lambda _session, payload: {
            "id": 1,
            "name": payload.name,
            "prefix": "abc12345",
            "created_at": datetime.utcnow(),
            "revoked_at": None,
            "last_used_at": None,
            "key": "secret",
        },
    )
    client = _build_client()

    response = client.post("/keys/", json={"name": "ci"})

    assert response.status_code == 201
    assert response.json()["name"] == "ci"
    assert response.json()["key"] == "secret"


def test_list_keys(monkeypatch):
    monkeypatch.setattr(
        keys,
        "list_api_keys",
        lambda _session, include_revoked=False: [
            {
                "id": 1,
                "name": "ci",
                "prefix": "abc12345",
                "created_at": datetime.utcnow(),
                "revoked_at": None,
                "last_used_at": None,
            }
        ],
    )
    client = _build_client()

    response = client.get("/keys/")

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_revoke_key_not_found(monkeypatch):
    monkeypatch.setattr(keys, "revoke_api_key", lambda _session, _key_id: None)
    client = _build_client()

    response = client.delete("/keys/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Key not found or already revoked"


def test_revoke_key_success(monkeypatch):
    monkeypatch.setattr(
        keys,
        "revoke_api_key",
        lambda _session, _key_id: {
            "id": 7,
            "name": "ci",
            "prefix": "abc12345",
            "created_at": datetime.utcnow(),
            "revoked_at": datetime.utcnow(),
            "last_used_at": None,
        },
    )
    client = _build_client()

    response = client.delete("/keys/7")

    assert response.status_code == 200
    assert response.json()["id"] == 7


def test_list_keys_include_revoked_query(monkeypatch):
    seen = {"include_revoked": None}

    def _list(_session, include_revoked=False):
        seen["include_revoked"] = include_revoked
        return []

    monkeypatch.setattr(keys, "list_api_keys", _list)
    client = _build_client()

    response = client.get("/keys/?include_revoked=true")

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert seen["include_revoked"] is True
