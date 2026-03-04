from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.core.database import get_session
from src.api.core.security import require_admin_if_enabled
from src.api.routers import audit


_NOW = datetime.utcnow()


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(audit.router)
    app.dependency_overrides[require_admin_if_enabled] = lambda: {"admin": True}
    app.dependency_overrides[get_session] = lambda: object()
    return TestClient(app)


def _audit_payload(protocol: str = "uniswap", company: str = "trail") -> dict:
    return {
        "protocol": protocol,
        "version": None,
        "company": company,
        "url": "https://example.com/audit.pdf",
        "date_added": _NOW,
        "last_updated": _NOW,
    }


def test_create_audit(monkeypatch):
    monkeypatch.setattr(audit.crud, "create_audit", lambda _s, _d: _audit_payload())
    client = _build_client()

    response = client.post(
        "/audit/",
        json={
            "protocol": "uniswap",
            "version": None,
            "company": "trail",
            "url": "https://example.com/audit.pdf",
        },
    )

    assert response.status_code == 201
    assert response.json()["protocol"] == "uniswap"


def test_get_audit_not_found(monkeypatch):
    monkeypatch.setattr(audit.crud, "get_audit", lambda *_args, **_kwargs: None)
    client = _build_client()

    response = client.get("/audit/uniswap/trail")

    assert response.status_code == 404
    assert response.json()["detail"] == "Audit not found"


def test_list_audits(monkeypatch):
    monkeypatch.setattr(
        audit.crud,
        "get_audits",
        lambda *_args, **_kwargs: [_audit_payload()],
    )
    client = _build_client()

    response = client.get("/audit/")

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_delete_audit_not_found(monkeypatch):
    monkeypatch.setattr(audit.crud, "delete_audit", lambda *_args, **_kwargs: False)
    client = _build_client()

    response = client.delete("/audit/uniswap/trail")

    assert response.status_code == 404
    assert response.json()["detail"] == "Audit not found"
