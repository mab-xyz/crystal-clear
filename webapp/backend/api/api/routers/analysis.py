from fastapi import APIRouter, Query, status, Depends
from sqlalchemy.orm import Session
from fastapi_cache.decorator import cache

from api.core.config import settings
from api.core.database import get_session
from api.schemas.analysis import (
    ContractDependenciesRequest,
    ContractDependenciesResponse,
    ContractRiskRequest,
    RiskAnalysisResponse,
)
from api.schemas.response import ErrorResponse
from api.services.analysis_service import (
    analyze_contract_dependencies,
    assess_contract_risk,
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
@cache(expire=settings.cache_ttl)
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

    callGraph = analyze_contract_dependencies(
        session=session,
        address=request.address,
        from_block=request.from_block,
        to_block=request.to_block,
    )

    return ContractDependenciesResponse(
        **callGraph.model_dump()
    )


@router.get(
    "/{address}/risk",
    response_model=RiskAnalysisResponse,
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
@cache(expire=settings.cache_ttl)
async def get_contract_risk(
    address: str,
    from_block: str = Query(None, description="Start block"),
    to_block: str = Query(None, description="End block"),
    session: Session = Depends(get_session)
):
    """
    Get the risk assessment for a contract.

    - **address**: Ethereum contract address
    """
    request = ContractRiskRequest(address=address, from_block=from_block, to_block=to_block)

    risk_data = await assess_contract_risk(session, request.address, request.from_block, request.to_block)

    return risk_data
