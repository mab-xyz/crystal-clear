from api.crud.contract import (
    create_contract,
    delete_contract,
    get_contract,
    get_contracts,
    update_contract,
)
from api.models.contract import ContractCreate, ContractUpdate


def test_create_and_get_contract(session):
    # Create contract
    contract_data = ContractCreate(
        address="0xABCDEF", protocol="Uniswap", version="1.0"
    )
    created = create_contract(session, contract_data)

    assert created.address == "0xabcdef"  # address should be lowercased
    assert created.protocol == "Uniswap"

    # Get contract
    fetched = get_contract(session, "0xABCDEF")
    assert fetched is not None
    assert fetched.address == "0xabcdef"
    assert fetched.protocol == "Uniswap"


def test_update_contract(session):
    contract_data = ContractCreate(
        address="0x12345", protocol="SushiSwap", version="2.0"
    )
    create_contract(session, contract_data)

    update_data = ContractUpdate(version="2.1")
    updated = update_contract(session, "0x12345", update_data)

    assert updated.version == "2.1"
    assert updated.last_updated > updated.date_added

    # Update non-existing contract returns None
    result = update_contract(session, "0xdeadbeef", update_data)
    assert result is None


def test_delete_contract(session):
    contract_data = ContractCreate(
        address="0xDEAD", protocol="Curve", version="1.0"
    )
    create_contract(session, contract_data)

    # Delete existing
    deleted = delete_contract(session, "0xDEAD")
    assert deleted is True

    # Delete again should return False
    deleted_again = delete_contract(session, "0xDEAD")
    assert deleted_again is False

    # Ensure contract is gone
    assert get_contract(session, "0xDEAD") is None


def test_get_contracts_with_filters(session):
    contracts_data = [
        ContractCreate(address="0xAAA", protocol="Uniswap", version="1.0"),
        ContractCreate(address="0xBBB", protocol="Uniswap", version="2.0"),
        ContractCreate(address="0xCCC", protocol="SushiSwap", version=None),
    ]

    for data in contracts_data:
        create_contract(session, data)

    # Filter by version
    version_1_contracts = get_contracts(session, version="1.0")
    assert len(version_1_contracts) == 1
    assert version_1_contracts[0].address == "0xaaa"

    # Filter by protocol and version
    filtered = get_contracts(session, protocol="Uniswap", version="2.0")
    assert len(filtered) == 1
    assert filtered[0].address == "0xbbb"

    # Filter where version is None
    none_version_contracts = get_contracts(session, version=None)
    assert len(none_version_contracts) == 1
    assert none_version_contracts[0].address == "0xccc"
