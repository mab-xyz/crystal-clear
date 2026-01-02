from datetime import datetime
from typing import List

from sqlmodel import Session, select

from api.models.contract import Contract, ContractCreate, ContractUpdate


def create_contract(session: Session, contract_data: ContractCreate) -> Contract:
    contract_data.address = contract_data.address.lower()
    contract = Contract(**contract_data.model_dump())
    session.add(contract)
    session.commit()
    session.refresh(contract)
    return contract


def get_contract(session: Session, address: str) -> Contract | None:
    return session.get(Contract, address.lower())


def update_contract(
    session: Session, address: str, contract_data: ContractUpdate
) -> Contract | None:
    """
    Update a contract with optional fields.
    Only updates fields that are provided in contract_data.

    Args:
        session: Database session
        address: Address of the contract to update
        contract_data: ContractUpdate model with optional fields

    Returns:
        Updated Contract object or None if not found
    """
    contract = get_contract(session, address.lower())
    if not contract:
        return None

    # Only update fields that are not None
    update_data = contract_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(contract, key, value)

    contract.last_updated = datetime.now()
    session.add(contract)
    session.commit()
    session.refresh(contract)
    return contract


def delete_contract(session: Session, address: str) -> bool:
    contract = get_contract(session, address)
    if not contract:
        return False

    session.delete(contract)
    session.commit()
    return True


def get_contracts(
    session: Session, protocol: str | None = None, version: str | None = None
) -> List[Contract]:
    stmt = select(Contract)

    if protocol:
        stmt = stmt.where(Contract.protocol == protocol)
    if version is not None:
        stmt = stmt.where(Contract.version == version)
    else:
        stmt = stmt.where(Contract.version.is_(None))

    return session.exec(stmt).all()
