from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.api.core.security import require_admin_if_enabled
from src.api.routers.contract import get_contract_service
from src.api.routers import contract


_NOW = datetime.utcnow()


class _FakeContractService:
    async def create_contract(self, _contract_data):
        return {
            "address": "0xabc",
            "protocol": "Uniswap",
            "version": "1.0",
            "date_added": _NOW,
            "last_updated": _NOW,
        }

    async def get_contract(self, address: str):
        if address == "0xmissing":
            raise HTTPException(status_code=404, detail="not found")
        return {
            "address": "0xabc",
            "protocol": "Uniswap",
            "version": "1.0",
            "date_added": _NOW,
            "last_updated": _NOW,
        }

    async def get_contracts(self, _protocol=None, _version=None):
        return [
            {
                "address": "0xabc",
                "protocol": "Uniswap",
                "version": "1.0",
                "date_added": _NOW,
                "last_updated": _NOW,
            }
        ]

    async def get_contract_audits(self, _address: str):
        return {
            "contract": {
                "address": "0xabc",
                "protocol": "Uniswap",
                "version": "1.0",
                "date_added": _NOW,
                "last_updated": _NOW,
            },
            "audits": [
                {
                    "protocol": "Uniswap",
                    "version": "1.0",
                    "company": "trail",
                    "url": "https://example.com",
                    "date_added": _NOW,
                    "last_updated": _NOW,
                }
            ],
        }



def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(contract.router)
    app.dependency_overrides[get_contract_service] = lambda: _FakeContractService()
    app.dependency_overrides[require_admin_if_enabled] = lambda: {"admin": True}
    return TestClient(app)


def test_create_contract():
    client = _build_client()

    response = client.post(
        "/contract/",
        json={"address": "0xAbc", "protocol": "Uniswap", "version": "1.0"},
    )

    assert response.status_code == 201
    assert response.json()["protocol"] == "Uniswap"


def test_get_contract_not_found():
    client = _build_client()

    response = client.get("/contract/0xmissing")

    assert response.status_code == 404


def test_list_contracts():
    client = _build_client()

    response = client.get("/contract/")

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_get_contract_audits():
    client = _build_client()

    response = client.get("/contract/0xabc/audits")

    assert response.status_code == 200
    assert response.json()["contract"]["address"] == "0xabc"
    assert len(response.json()["audits"]) == 1
