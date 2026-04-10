import json

import pytest
from fastapi import HTTPException

from src.api.core.exceptions import InputValidationError, InternalServerError, NotFoundError
from src.api.services import info_service


def test_get_deployment_data_not_found_from_allium(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)
    monkeypatch.setattr(info_service.crud_deployment, "get_deployment", lambda *_a: None)

    class _Client:
        def __init__(self, _k):
            pass

        @staticmethod
        def get_deployment(_a):
            return None

    monkeypatch.setattr(info_service, "AlliumClient", _Client)

    with pytest.raises(NotFoundError):
        info_service.get_deployment_data(object(), "0xabc")


def test_get_deployment_data_create_returns_none(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)
    monkeypatch.setattr(info_service.crud_deployment, "get_deployment", lambda *_a: None)

    class _Client:
        def __init__(self, _k):
            pass

        @staticmethod
        def get_deployment(_a):
            return {
                "address": "0xabc",
                "deployer": "0xdef",
                "deployer_eoa": "0x123",
                "transaction_hash": "0xtx",
                "block_number": 7,
            }

    monkeypatch.setattr(info_service, "AlliumClient", _Client)
    monkeypatch.setattr(info_service.crud_deployment, "create_deployment", lambda *_a: None)

    with pytest.raises(InternalServerError):
        info_service.get_deployment_data(object(), "0xabc")


def test_get_verification_data_returns_sourcify_payload(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)

    class _Resp:
        status_code = 200

        @staticmethod
        def json():
            return {"address": "0xabc", "match": "match", "verifiedAt": "na"}

    monkeypatch.setattr(info_service.requests, "get", lambda _u: _Resp())

    out = info_service.get_verification_data("0xabc")
    assert out.verification == "verified"


def test_get_verification_data_fallback_not_match(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)

    class _Resp:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    calls = {"n": 0}

    def _get(_u):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp(404, {})
        return _Resp(200, {"result": [{"SourceCode": ""}]})

    monkeypatch.setattr(info_service.requests, "get", _get)

    out = info_service.get_verification_data("0xabc")
    assert out.verification == "not-verified"


def test_get_verification_data_invalid_address(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: False)

    with pytest.raises(InputValidationError):
        info_service.get_verification_data("bad")


def test_get_verification_data_request_error_maps_internal(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)

    def _boom(_u):
        raise RuntimeError("network down")

    monkeypatch.setattr(info_service.requests, "get", _boom)

    with pytest.raises(InternalServerError):
        info_service.get_verification_data("0xabc")


@pytest.mark.asyncio
async def test_get_scorecard_data_invalid_address(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: False)

    with pytest.raises(InputValidationError):
        await info_service.get_scorecard_data(object(), "bad")


@pytest.mark.asyncio
async def test_get_scorecard_data_not_found_error_passthrough(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)

    class _ContractService:
        def __init__(self, _session):
            pass

        async def get_contract_repository(self, _address):
            raise NotFoundError("missing")

    monkeypatch.setattr(info_service, "ContractService", _ContractService)

    with pytest.raises(NotFoundError):
        await info_service.get_scorecard_data(object(), "0xabc")


@pytest.mark.asyncio
async def test_get_scorecard_data_repo_lookup_generic_error(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)

    class _ContractService:
        def __init__(self, _session):
            pass

        async def get_contract_repository(self, _address):
            raise RuntimeError("unexpected")

    monkeypatch.setattr(info_service, "ContractService", _ContractService)

    with pytest.raises(InternalServerError):
        await info_service.get_scorecard_data(object(), "0xabc")


@pytest.mark.asyncio
async def test_get_scorecard_data_request_exception(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)

    class _RepoObj:
        url = "https://github.com/acme/protocol"

    class _ContractService:
        def __init__(self, _session):
            pass

        async def get_contract_repository(self, _address):
            return {"repository": _RepoObj()}

    def _boom(_u):
        raise info_service.requests.RequestException("down")

    monkeypatch.setattr(info_service, "ContractService", _ContractService)
    monkeypatch.setattr(info_service.requests, "get", _boom)

    with pytest.raises(InternalServerError):
        await info_service.get_scorecard_data(object(), "0xabc")


@pytest.mark.asyncio
async def test_get_scorecard_data_docker_nonzero(monkeypatch):
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
        returncode = 1
        stdout = ""
        stderr = "failed"

    monkeypatch.setattr(info_service, "ContractService", _ContractService)
    monkeypatch.setattr(info_service.requests, "get", lambda _u: _Resp())
    monkeypatch.setattr(info_service.subprocess, "run", lambda *a, **k: _RunResult())

    with pytest.raises(InternalServerError):
        await info_service.get_scorecard_data(object(), "0xabc")


@pytest.mark.asyncio
async def test_get_scorecard_data_subprocess_error_branch(monkeypatch):
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

    def _raise_subprocess(*_a, **_k):
        raise info_service.subprocess.SubprocessError("spawn error")

    monkeypatch.setattr(info_service, "ContractService", _ContractService)
    monkeypatch.setattr(info_service.requests, "get", lambda _u: _Resp())
    monkeypatch.setattr(info_service.subprocess, "run", _raise_subprocess)

    with pytest.raises(InternalServerError):
        await info_service.get_scorecard_data(object(), "0xabc")


@pytest.mark.asyncio
async def test_get_scorecard_data_docker_json_decode_error(monkeypatch):
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
        stdout = "{invalid json}"
        stderr = ""

    monkeypatch.setattr(info_service, "ContractService", _ContractService)
    monkeypatch.setattr(info_service.requests, "get", lambda _u: _Resp())
    monkeypatch.setattr(info_service.subprocess, "run", lambda *a, **k: _RunResult())

    with pytest.raises(InternalServerError):
        await info_service.get_scorecard_data(object(), "0xabc")


@pytest.mark.asyncio
async def test_get_scorecard_data_second_stage_input_validation(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)

    class _RepoObj:
        url = "https://github.com/acme/protocol"

    class _ContractService:
        def __init__(self, _session):
            pass

        async def get_contract_repository(self, _address):
            return {"repository": _RepoObj()}

    def _raise_input_validation(_u):
        raise InputValidationError("bad request")

    monkeypatch.setattr(info_service, "ContractService", _ContractService)
    monkeypatch.setattr(info_service.requests, "get", _raise_input_validation)

    with pytest.raises(InputValidationError):
        await info_service.get_scorecard_data(object(), "0xabc")


def test_get_proxy_data_invalid_address(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: False)

    with pytest.raises(InputValidationError):
        info_service.get_proxy_data("bad")


def test_get_proxy_data_runtime_error(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)
    monkeypatch.setattr(
        info_service,
        "detect_delegatecall_and_address",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(InternalServerError):
        info_service.get_proxy_data("0xabc")


def test_get_permissions_data_invalid_and_generic(monkeypatch):
    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: False)
    with pytest.raises(InputValidationError):
        info_service.get_permissions_data("bad")

    monkeypatch.setattr(info_service.Web3, "is_address", lambda _a: True)
    monkeypatch.setattr(
        info_service,
        "get_permissions",
        lambda _a: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    with pytest.raises(InternalServerError):
        info_service.get_permissions_data("0xabc")
