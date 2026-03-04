import json

import pytest
from fastapi import HTTPException

from src.api.core.exceptions import (
    InputValidationError,
    InternalServerError,
    NotFoundError,
)
from src.api.services import info_service


def test_get_latest_block_number_success(monkeypatch):
    class _Eth:
        @staticmethod
        def get_block_number():
            return 123

    class _Web3:
        eth = _Eth()

        @staticmethod
        def HTTPProvider(_url):
            return object()

        def __init__(self, _provider):
            pass

    monkeypatch.setattr(info_service, "Web3", _Web3)

    assert info_service.get_latest_block_number() == 123


def test_get_latest_block_number_error(monkeypatch):
    class _BrokenWeb3:
        @staticmethod
        def HTTPProvider(_url):
            raise RuntimeError("boom")

    monkeypatch.setattr(info_service, "Web3", _BrokenWeb3)

    with pytest.raises(InternalServerError):
        info_service.get_latest_block_number()


def test_get_deployment_data_invalid_address(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: False)

    with pytest.raises(InputValidationError):
        info_service.get_deployment_data(object(), "bad")


def test_get_deployment_data_fetches_from_allium_when_cache_miss(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)
    monkeypatch.setattr(info_service.crud_deployment, "get_deployment", lambda *_a: None)

    class _Client:
        def __init__(self, _api_key):
            pass

        @staticmethod
        def get_deployment(_address):
            return {
                "address": "0xabc",
                "deployer": "0xdef",
                "deployer_eoa": "0x123",
                "transaction_hash": "0xtx",
                "block_number": 7,
            }

    monkeypatch.setattr(info_service, "AlliumClient", _Client)
    monkeypatch.setattr(
        info_service.crud_deployment,
        "create_deployment",
        lambda _s, entry: {
            "address": entry.address,
            "deployer": entry.deployer,
            "deployer_eoa": entry.deployer_eoa,
            "tx_hash": entry.tx_hash,
            "block_number": entry.block_number,
        },
    )

    result = info_service.get_deployment_data(object(), "0xabc")

    assert result["address"] == "0xabc"
    assert result["block_number"] == 7


def test_get_verification_data_falls_back_to_etherscan(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)

    class _Resp:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    calls = {"n": 0}

    def _fake_get(_url):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp(404, {})
        return _Resp(200, {"result": [{"SourceCode": "contract X{}"}]})

    monkeypatch.setattr(info_service.requests, "get", _fake_get)

    result = info_service.get_verification_data(
        "0x1111111111111111111111111111111111111111"
    )

    assert result == {
        "address": "0x1111111111111111111111111111111111111111",
        "match": "match",
        "verifiedAt": "na",
    }


@pytest.mark.asyncio
async def test_get_scorecard_data_api_success(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)

    class _RepoObj:
        url = "https://github.com/acme/protocol"

    class _ContractService:
        def __init__(self, _session):
            pass

        async def get_contract_repository(self, _address):
            return {"repository": _RepoObj()}

    class _Resp:
        status_code = 200

        @staticmethod
        def json():
            return {"score": 8.2, "date": "2025-01-01", "checks": []}

    monkeypatch.setattr(info_service, "ContractService", _ContractService)
    monkeypatch.setattr(info_service.requests, "get", lambda _url: _Resp())

    result = await info_service.get_scorecard_data(object(), "0xabc")

    assert result["source"] == "api"
    assert result["repo"] == "acme/protocol"
    assert result["raw"]["score"] == 8.2


@pytest.mark.asyncio
async def test_get_scorecard_data_docker_fallback(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)

    class _RepoObj:
        url = "https://github.com/acme/protocol"

    class _ContractService:
        def __init__(self, _session):
            pass

        async def get_contract_repository(self, _address):
            return {"repository": _RepoObj()}

    class _Resp:
        status_code = 404

        @staticmethod
        def json():
            return {}

    class _RunResult:
        returncode = 0
        stdout = json.dumps({"score": 5.5, "date": "2025-01-01", "checks": []})
        stderr = ""

    monkeypatch.setattr(info_service, "ContractService", _ContractService)
    monkeypatch.setattr(info_service.requests, "get", lambda _url: _Resp())
    monkeypatch.setattr(info_service.subprocess, "run", lambda *a, **k: _RunResult())

    result = await info_service.get_scorecard_data(object(), "0xabc")

    assert result["source"] == "docker"
    assert result["repo"] == "acme/protocol"


def test_get_proxy_data_and_permissions_data(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)
    monkeypatch.setattr(
        info_service,
        "detect_delegatecall_and_address",
        lambda _a, _u: ("transparent", "ok", []),
    )
    monkeypatch.setattr(
        info_service,
        "get_permissions",
        lambda _a: {"functions": ["owner()"]},
    )

    proxy = info_service.get_proxy_data("0xabc")
    perms = info_service.get_permissions_data("0xabc")

    assert proxy["type"] == "transparent"
    assert perms == {"functions": ["owner()"]}


def test_get_permissions_data_maps_value_error(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)

    def _boom(_a):
        raise ValueError("missing")

    monkeypatch.setattr(info_service, "get_permissions", _boom)

    with pytest.raises(NotFoundError):
        info_service.get_permissions_data("0xabc")


@pytest.mark.asyncio
async def test_get_scorecard_data_preserves_http_exception(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)

    class _ContractService:
        def __init__(self, _session):
            pass

        async def get_contract_repository(self, _address):
            raise HTTPException(status_code=404, detail="missing")

    monkeypatch.setattr(info_service, "ContractService", _ContractService)

    with pytest.raises(HTTPException) as exc:
        await info_service.get_scorecard_data(object(), "0xabc")
    assert exc.value.status_code == 404
