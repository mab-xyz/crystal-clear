from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import datetime

from src.api.core.database import get_session
from src.api.core.security import require_admin_if_enabled
from src.api.routers import audit


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(audit.router)
    app.dependency_overrides[require_admin_if_enabled] = lambda: {"admin": True}
    app.dependency_overrides[get_session] = lambda: object()
    return TestClient(app)


def _audit_payload(protocol: str = "p", company: str = "c") -> dict:
    now = datetime.utcnow()
    return {
        "protocol": protocol,
        "version": None,
        "company": company,
        "url": "https://example.com/audit.pdf",
        "date_added": now,
        "last_updated": now,
    }


def test_create_audit_value_error(monkeypatch):
    monkeypatch.setattr(
        audit.crud,
        "create_audit",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("dup")),
    )
    client = _build_client()

    response = client.post(
        "/audit/",
        json={"protocol": "p", "version": None, "company": "c", "url": "u"},
    )

    assert response.status_code == 400


def test_create_audit_internal_error(monkeypatch):
    monkeypatch.setattr(
        audit.crud,
        "create_audit",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    client = _build_client()

    response = client.post(
        "/audit/",
        json={"protocol": "p", "version": None, "company": "c", "url": "u"},
    )

    assert response.status_code == 500


def test_update_audit_value_error(monkeypatch):
    monkeypatch.setattr(
        audit.crud,
        "update_audit",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("bad")),
    )
    client = _build_client()

    response = client.put("/audit/p/c", json={"url": "new"})

    assert response.status_code == 400


def test_get_audit_success(monkeypatch):
    monkeypatch.setattr(
        audit.crud,
        "get_audit",
        lambda *_a, **_k: _audit_payload("uni", "trail"),
    )
    client = _build_client()

    response = client.get("/audit/uni/trail")

    assert response.status_code == 200
    assert response.json()["protocol"] == "uni"


def test_update_audit_not_found(monkeypatch):
    monkeypatch.setattr(audit.crud, "update_audit", lambda *_a, **_k: None)
    client = _build_client()

    response = client.put("/audit/p/c", json={"url": "https://new.example/a.pdf"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Audit not found"


def test_update_audit_success(monkeypatch):
    monkeypatch.setattr(
        audit.crud,
        "update_audit",
        lambda *_a, **_k: _audit_payload("p", "c"),
    )
    client = _build_client()

    response = client.put("/audit/p/c", json={"url": "https://new.example/a.pdf"})

    assert response.status_code == 200
    assert response.json()["company"] == "c"
