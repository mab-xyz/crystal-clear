from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import src.api.crud.audit as audit_crud
import src.api.crud.contract as crud
import src.api.crud.repository as repository_crud
from src.api.models.audit import AuditCreate
from src.api.models.contract import Contract, ContractCreate, ContractUpdate
from src.api.models.repository import RepositoryCreate
from src.api.schemas.contract import (
    ContractAuditCreate,
    ContractRepositoryCreate,
)


class ContractService:
    def __init__(self, session: Session):
        self.session = session

    async def create_contract(self, contract_data: ContractCreate) -> Contract:
        """Create a new contract"""
        try:
            # Convert empty string to None for version
            if contract_data.version == "":
                contract_data.version = None

            return crud.create_contract(self.session, contract_data)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Contract with address {contract_data.address} already exists",
            ) from e

    async def get_contract(self, address: str) -> Contract:
        """Get contract by address"""
        contract = crud.get_contract(self.session, address)
        if not contract:
            raise HTTPException(
                status_code=404,
                detail=f"Contract with address {address} not found",
            )
        return contract

    async def update_contract(
        self, address: str, contract_data: ContractUpdate
    ) -> Contract:
        """Update contract by address"""
        contract = crud.update_contract(self.session, address, contract_data)
        if not contract:
            raise HTTPException(
                status_code=404,
                detail=f"Contract with address {address} not found",
            ) from None
        return contract

    async def delete_contract(self, address: str) -> None:
        """Delete contract by address"""
        if not crud.delete_contract(self.session, address):
            raise HTTPException(
                status_code=404,
                detail=f"Contract with address {address} not found",
            ) from None

    async def get_contracts(
        self, protocol: str | None = None, version: str | None = None
    ) -> list[Contract]:
        """Get contracts with optional protocol and version filters"""
        return crud.get_contracts(self.session, protocol, version)

    async def get_contract_audits(self, address: str) -> dict:
        """Check if contract has associated audits"""
        contract = await self.get_contract(address)

        audits = audit_crud.get_audits(
            self.session, protocol=contract.protocol, version=contract.version
        )

        return {"contract": contract, "audits": audits}

    async def get_contract_repository(self, address: str) -> dict:
        """Get repository for a contract by address"""
        contract = await self.get_contract(address)

        repository = repository_crud.get_repository(
            self.session, protocol=contract.protocol, version=contract.version
        )

        if not repository:
            raise HTTPException(
                status_code=404,
                detail=f"Repository for contract {address} not found",
            ) from None

        return {"contract": contract, "repository": repository}

    async def add_contract_audit(
        self, address: str, audit_data: ContractAuditCreate
    ) -> dict:
        """Add audit for a contract"""
        contract = await self.get_contract(address)

        try:
            # Create new audit
            audit_create = AuditCreate(
                protocol=contract.protocol,
                version=contract.version,
                company=audit_data.company,
                url=audit_data.url,
            )

            audit = audit_crud.create_audit(self.session, audit_create)

            return {"contract": contract, "audits": [audit]}
        except IntegrityError as e:
            raise HTTPException(status_code=400, detail=str(e.orig)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def add_contract_repository(
        self, address: str, repository_data: ContractRepositoryCreate
    ) -> dict:
        """Add repository for a contract"""
        contract = await self.get_contract(address)

        try:
            repository_create = RepositoryCreate(
                protocol=contract.protocol,
                version=contract.version,
                url=repository_data.url,
            )

            repository = repository_crud.create_repository(
                self.session, repository_create
            )

            return {"contract": contract, "repository": repository}
        except IntegrityError as e:
            self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e.orig)) from e
        except Exception as e:
            raise HTTPException(
                status_code=500, detail="Internal server error: " + str(e)
            ) from e
