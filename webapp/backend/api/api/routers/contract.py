from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from api.models.contract import (
    ContractCreate,
    ContractUpdate,
    ContractResponse,
    ContractListResponse
)

from api.services.contract_service import ContractService
from api.core.database import get_session
from api.schemas.contract import (
    ContractAuditCheckResponse, 
    ContractRepositoryResponse,
    ContractAuditCreate,
    ContractRepositoryCreate
)
from api.schemas.response import ErrorResponse

router = APIRouter(
    prefix="/contract",
    tags=["contract"],
)

def get_contract_service(session: Session = Depends(get_session)) -> ContractService:
    return ContractService(session)

@router.post(
    "/",
    response_model=ContractResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Contract already exists"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        },
    },
    summary="Create a new contract",
)
async def create_contract(
    contract_data: ContractCreate,
    service: ContractService = Depends(get_contract_service),
) -> ContractResponse:
    return await service.create_contract(contract_data)

@router.get(
    "/{address}",
    response_model=ContractResponse,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Contract not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        },
    },
    summary="Get contract by address",
)
async def get_contract(
    address: str,
    service: ContractService = Depends(get_contract_service),
) -> ContractResponse:
    return await service.get_contract(address)

@router.put(
    "/{address}",
    response_model=ContractResponse,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Contract not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        },
    },
    summary="Update contract by address",
)
async def update_contract(
    address: str,
    contract_data: ContractUpdate,
    service: ContractService = Depends(get_contract_service),
) -> ContractResponse:
    return await service.update_contract(address, contract_data)

@router.delete(
    "/{address}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Contract not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        },
    },
    summary="Delete contract by address",
)
async def delete_contract(
    address: str,
    service: ContractService = Depends(get_contract_service),
) -> None:
    await service.delete_contract(address)

@router.get(
    "/",
    response_model=ContractListResponse,
    responses={
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        },
    },
    summary="List contracts with optional filters",
)
async def get_contracts(
    protocol: str | None = None,
    version: str | None = None,
    service: ContractService = Depends(get_contract_service),
) -> ContractListResponse:
    contracts = await service.get_contracts(protocol, version)
    return ContractListResponse(
        total=len(contracts),
        items=contracts
    )

@router.get(
    "/{address}/audits",
    response_model=ContractAuditCheckResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Contract not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        },
    },
    summary="Check if contract has audits",
    description="Check if a contract has associated audit reports based on protocol and version.",
)
async def get_contract_audits(
    address: str,
    service: ContractService = Depends(get_contract_service),
):
    """
    Check if a contract has associated audits.
    
    Args:
        address: The contract address to check
        
    Returns:
        Response containing:
        - contract: Contract details
        - audits: List of audit details if found
    """
    result = await service.get_contract_audits(address)
    return ContractAuditCheckResponse(**result)

@router.get(
    "/{address}/repository",
    response_model=ContractRepositoryResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Contract not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        },
    },
    summary="Get contract repository",
    description="Fetch the repository for a contract by its address.",
)
async def get_contract_repository(
    address: str,
    service: ContractService = Depends(get_contract_service),
):
    """
    Get the repository for a contract by its address.
    
    Args:
        address: The contract address to fetch repository for
        
    Returns:
        Response containing:
        - contract: Contract details
        - repository: repository content
    """
    result = await service.get_contract_repository(address)
    return result

@router.post(
    "/{address}/audits",
    response_model=ContractAuditCheckResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Contract not found"
        },
        400: {
            "model": ErrorResponse,
            "description": "Audit already exists"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        },
    },
    summary="Add audit to contract",
    description="Add a new audit report for a contract using its protocol and version.",
)
async def add_contract_audit(
    address: str,
    audit_data: ContractAuditCreate,
    service: ContractService = Depends(get_contract_service),
):
    """
    Add a new audit for a contract.
    
    Args:
        address: The contract address
        audit_data: Audit details including company and URL
        
    Returns:
        Response containing:
        - contract: Contract details
        - audits: List containing the new audit
    """
    result = await service.add_contract_audit(address, audit_data)
    return ContractAuditCheckResponse(**result)

@router.post(
    "/{address}/repository",
    response_model=ContractRepositoryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Contract not found"
        },
        400: {
            "model": ErrorResponse,
            "description": "Repository already exists"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        },
    },
    summary="Add repository to contract",
    description="Add repository repository URL for a contract using its protocol and version.",
)
async def add_contract_source_code(
    address: str,
    repository_data: ContractRepositoryCreate,
    service: ContractService = Depends(get_contract_service),
):
    """
    Add repository for a contract.
    
    Args:
        address: The contract address
        repository_data: repository details including URL
        
    Returns:
        Response containing:
        - contract: Contract details
        - repository: Added repository details
    """
    result = await service.add_contract_repository(address, repository_data)
    return ContractRepositoryResponse(**result)