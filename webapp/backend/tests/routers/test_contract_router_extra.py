from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.core.security import require_admin_if_enabled
from src.api.routers.contract import get_contract_service
from src.api.routers import contract


_NOW = datetime.utcnow()


class _FakeService:
    async def get_contract_repository(self, _address):
        return {
            "contract": {
                "address": "0xabc",
                "protocol": "P",
                "version": None,
                "date_added": _NOW,
                "last_updated": _NOW,
            },
            "repository": {
                "protocol": "P",
                "version": None,
                "url": "https://repo",
                "date_added": _NOW,
                "last_updated": _NOW,
            },
        }

    async def add_contract_audit(self, _address, _audit_data):
        return {
            "contract": {
                "address": "0xabc",
                "protocol": "P",
                "version": None,
                "date_added": _NOW,
                "last_updated": _NOW,
            },
            "audits": [
                {
                    "protocol": "P",
                    "version": None,
                    "company": "c",
                    "url": "u",
                    "date_added": _NOW,
                    "last_updated": _NOW,
                }
            ],
        }

    async def add_contract_repository(self, _address, _repository_data):
        return {
            "contract": {
                "address": "0xabc",
                "protocol": "P",
                "version": None,
                "date_added": _NOW,
                "last_updated": _NOW,
            },
            "repository": {
                "protocol": "P",
                "version": None,
                "url": "https://repo",
                "date_added": _NOW,
                "last_updated": _NOW,
            },
        }


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(contract.router)
    app.dependency_overrides[get_contract_service] = lambda: _FakeService()
    app.dependency_overrides[require_admin_if_enabled] = lambda: {"admin": True}
    return TestClient(app)


def test_get_contract_repository_endpoint():
    response = _client().get("/contract/0xabc/repository")
    assert response.status_code == 200
    assert response.json()["repository"]["url"] == "https://repo"


def test_add_contract_audit_endpoint():
    response = _client().post("/contract/0xabc/audits", json={"company": "c", "url": "u"})
    assert response.status_code == 201
    assert len(response.json()["audits"]) == 1


def test_add_contract_repository_endpoint():
    response = _client().post("/contract/0xabc/repository", json={"url": "https://repo"})
    assert response.status_code == 201
    assert response.json()["repository"]["url"] == "https://repo"
