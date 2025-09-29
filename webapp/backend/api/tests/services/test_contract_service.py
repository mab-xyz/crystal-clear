import pytest
import pytest_asyncio
from fastapi import HTTPException

from api.crud.contract import create_contract
from api.models.contract import ContractCreate, ContractUpdate
from api.services.contract_service import ContractService


@pytest_asyncio.fixture
async def service(session):
    """Provides a ContractService instance with a fresh session."""
    return ContractService(session)


@pytest.mark.asyncio
async def test_create_and_get_contract(service, session):
    contract_data = ContractCreate(
        address="0xABC123", protocol="Uniswap", version="1.0"
    )

    # Create contract
    created = await service.create_contract(contract_data)
    assert created.address == "0xABC123".lower()
    assert created.protocol == "Uniswap"

    # Get contract
    fetched = await service.get_contract("0xABC123")
    assert fetched.address == "0xABC123".lower()

    # Get non-existent contract raises 404
    with pytest.raises(HTTPException) as exc:
        await service.get_contract("0xDEAD")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_contract(service, session):
    # Setup
    contract_data = ContractCreate(
        address="0x12345", protocol="SushiSwap", version="2.0"
    )
    create_contract(session, contract_data)

    update_data = ContractUpdate(version="2.1")
    updated = await service.update_contract("0x12345", update_data)
    assert updated.version == "2.1"

    # Update non-existent contract raises 404
    with pytest.raises(HTTPException) as exc:
        await service.update_contract("0xDEAD", update_data)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_contract(service, session):
    # Setup
    contract_data = ContractCreate(
        address="0xDEAD", protocol="Curve", version="1.0"
    )
    create_contract(session, contract_data)

    # Delete existing
    await service.delete_contract("0xDEAD")

    # Ensure deletion
    with pytest.raises(HTTPException) as exc:
        await service.get_contract("0xDEAD")
    assert exc.value.status_code == 404

    # Delete non-existent raises 404
    with pytest.raises(HTTPException) as exc:
        await service.delete_contract("0xDEAD")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_contracts(service, session):
    # Setup multiple contracts
    contracts_data = [
        ContractCreate(address="0xAAA", protocol="Uniswap", version="1.0"),
        ContractCreate(address="0xBBB", protocol="Uniswap", version="1.0"),
        ContractCreate(address="0xCCC", protocol="SushiSwap", version=None),
    ]
    for data in contracts_data:
        create_contract(session, data)

    filtered = await service.get_contracts(protocol="Uniswap", version="1.0")
    assert len(filtered) == 2
    assert all(c.protocol == "Uniswap" for c in filtered)


@pytest.mark.asyncio
async def test_add_contract_audit(service, session):
    # Setup contract
    contract_data = ContractCreate(
        address="0xAAA", protocol="Uniswap", version="1.0"
    )
    create_contract(session, contract_data)

    audit_data = {"company": "Trail-of-Bits", "url": "http://audit.com"}

    result = await service.add_contract_audit(
        "0xAAA", type("AuditData", (), audit_data)()
    )
    assert result["contract"].address == "0xAAA".lower()
    assert len(result["audits"]) == 1
    assert result["audits"][0].company == "Trail-of-Bits"


@pytest.mark.asyncio
async def test_add_contract_repository(service, session):
    # Setup contract
    contract_data = ContractCreate(
        address="0xBBB", protocol="SushiSwap", version=None
    )
    create_contract(session, contract_data)

    repo_data = {"url": "http://repo.com"}
    result = await service.add_contract_repository(
        "0xBBB", type("RepoData", (), repo_data)()
    )
    assert result["contract"].address == "0xBBB".lower()
    assert result["repository"].url == "http://repo.com"
