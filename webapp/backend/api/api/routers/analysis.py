from fastapi import APIRouter, Depends, Query, status
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session

from api.core.config import settings
from api.core.database import get_session
from api.schemas.analysis import (
    ContractDependenciesRequest,
    ContractDependenciesResponse,
    ContractRiskRequest,
    SimulationRequest,
    SimulationResponse,
    RiskAnalysisResponse,
)
from api.schemas.response import ErrorResponse
from api.services.analysis_service import (
    analyze_contract_dependencies,
    assess_contract_risk,
)
from api.core.config import cc

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

    return ContractDependenciesResponse(**callGraph.model_dump())


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
    session: Session = Depends(get_session),
):
    request = ContractRiskRequest(
        address=address, from_block=from_block, to_block=to_block
    )

    risk_data = await assess_contract_risk(
        session, request.address, request.from_block, request.to_block
    )

    return risk_data


@router.post(
    "/tx-risk",
    response_model=SimulationResponse,
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
    summary="Transaction risk: simulate and check",
    description=(
        "Simulate a transaction via Erigon trace_call, list all touched contracts (including DELEGATECALL), "
        "and report whether it's the first interaction by the sender and the verification status."
    ),
)
async def simulate_transaction(body: SimulationRequest) -> SimulationResponse:
    call_object = {"from": body.from_addr}
    if body.to_addr:
        call_object["to"] = body.to_addr
    if body.data:
        call_object["data"] = body.data
    if body.value:
        call_object["value"] = body.value
    if body.gas:
        call_object["gas"] = body.gas
    if body.maxFeePerGas:
        call_object["maxFeePerGas"] = body.maxFeePerGas
    if body.maxPriorityFeePerGas:
        call_object["maxPriorityFeePerGas"] = body.maxPriorityFeePerGas
    if body.tx_type:
        call_object["type"] = body.tx_type

    results = cc.simulate_and_check(
        call_object,
        block_tag=body.block_tag or "latest",
        allium_query_id=body.allium_query_id,
    )
    items = [
        {
            "address": addr,
            "first_time": info.get("first_time", False),
            "verification": info.get("verification"),
        }
        for addr, info in results.items()
    ]
    return SimulationResponse(results=items)
