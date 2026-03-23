import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.api.models.contract import ContractCreate
from src.api.services.contract_service import ContractService


@pytest.mark.asyncio
async def test_create_contract_empty_version_becomes_none(session):
    service = ContractService(session)

    created = await service.create_contract(
        ContractCreate(address="0xF00", protocol="P", version="")
    )

    assert created.version is None


@pytest.mark.asyncio
async def test_create_contract_maps_exception_to_http_400(session, monkeypatch):
    service = ContractService(session)

    monkeypatch.setattr(
        "src.api.services.contract_service.crud.create_contract",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("dup")),
    )

    with pytest.raises(HTTPException) as exc:
        await service.create_contract(ContractCreate(address="0x1", protocol="P", version=None))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_contract_repository_not_found(session, monkeypatch):
    service = ContractService(session)

    contract = await service.create_contract(
        ContractCreate(address="0xabc", protocol="P", version=None)
    )
    _ = contract

    monkeypatch.setattr(
        "src.api.services.contract_service.repository_crud.get_repository",
        lambda *_a, **_k: None,
    )

    with pytest.raises(HTTPException) as exc:
        await service.get_contract_repository("0xabc")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_add_contract_audit_integrity_error_maps_to_400(session, monkeypatch):
    service = ContractService(session)
    await service.create_contract(ContractCreate(address="0xaaa", protocol="P", version=None))

    def _raise(*_a, **_k):
        raise IntegrityError("stmt", "params", Exception("dup"))

    monkeypatch.setattr("src.api.services.contract_service.audit_crud.create_audit", _raise)

    with pytest.raises(HTTPException) as exc:
        await service.add_contract_audit("0xaaa", type("A", (), {"company": "c", "url": "u"})())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_add_contract_audit_generic_error_maps_to_500(session, monkeypatch):
    service = ContractService(session)
    await service.create_contract(ContractCreate(address="0xaab", protocol="P", version=None))

    monkeypatch.setattr(
        "src.api.services.contract_service.audit_crud.create_audit",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(HTTPException) as exc:
        await service.add_contract_audit("0xaab", type("A", (), {"company": "c", "url": "u"})())
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_add_contract_repository_integrity_error_rolls_back(session, monkeypatch):
    service = ContractService(session)
    await service.create_contract(ContractCreate(address="0xaac", protocol="P", version=None))

    called = {"rollback": False}

    def _rb():
        called["rollback"] = True

    monkeypatch.setattr(session, "rollback", _rb)

    def _raise(*_a, **_k):
        raise IntegrityError("stmt", "params", Exception("dup"))

    monkeypatch.setattr("src.api.services.contract_service.repository_crud.create_repository", _raise)

    with pytest.raises(HTTPException) as exc:
        await service.add_contract_repository("0xaac", type("R", (), {"url": "u"})())
    assert exc.value.status_code == 400
    assert called["rollback"] is True


@pytest.mark.asyncio
async def test_add_contract_repository_generic_error_maps_to_500(session, monkeypatch):
    service = ContractService(session)
    await service.create_contract(ContractCreate(address="0xaad", protocol="P", version=None))

    monkeypatch.setattr(
        "src.api.services.contract_service.repository_crud.create_repository",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(HTTPException) as exc:
        await service.add_contract_repository("0xaad", type("R", (), {"url": "u"})())
    assert exc.value.status_code == 500
