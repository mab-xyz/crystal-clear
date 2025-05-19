from fastapi import APIRouter, Query, status, Depends
from sqlalchemy.orm import Session
from loguru import logger

from core.database import get_session
from schemas.analysis import (
    ContractDependenciesRequest,
    ContractDependenciesResponse,
    ContractRiskRequest,
    ContractRiskResponse,
)
from schemas.response import ErrorResponse
from services.analysis_service import (
    analyze_contract_dependencies,
    calculate_contract_risk,
)

router = APIRouter(
    prefix="/v1/analysis",
    tags=["analysis"],
)


@router.get(
    "/{address}/dependencies",
    response_model=ContractDependenciesResponse,
    responses={
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
        422: {
            "description": "Input validation error",
            "model": ErrorResponse,
        },
    },
    status_code=status.HTTP_200_OK,
    summary="Get contract dependencies",
    description="Analyze and return the dependency network for a given contract address.",
)
async def get_contract_dependencies(
    address: str,
    from_block: str = Query(None, description="Start block"),
    to_block: str = Query(None, description="End block"),
    session: Session = Depends(get_session),
):
    """
    Get the dependency network for a contract.

    - **address**: Ethereum contract address
    - **from_block**: Optional start block for analysis
    - **to_block**: Optional end block for analysis
    """
    request = ContractDependenciesRequest(
        address=address, from_block=from_block, to_block=to_block
    )

    network = analyze_contract_dependencies(
        session=session,
        address=request.address,
        from_block=request.from_block,
        to_block=request.to_block,
    )

    return ContractDependenciesResponse(
        address=request.address,
        from_block=network["from_block"],
        to_block=network["to_block"],
        n_nodes=network["n_nodes"],
        nodes=network["nodes"],
        edges=network["edges"],
    )


@router.get(
    "/{address}/risk",
    response_model=ContractRiskResponse,
        responses={
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
        422: {
            "description": "Input validation error",
            "model": ErrorResponse,
        },
    },
    status_code=status.HTTP_200_OK,
    summary="Get contract risk assessment",
    description="Calculate and return the risk assessment for a given contract address.",
)
async def get_contract_risk(address: str):
    """
    Get the risk assessment for a contract.

    - **address**: Ethereum contract address
    """
    request = ContractRiskRequest(address=address)

    risk_data = calculate_contract_risk(address=request.address)

    return ContractRiskResponse(
        address=request.address,
        risk_score=risk_data["risk_score"],
        risk_factors=risk_data["risk_factors"],
    )
