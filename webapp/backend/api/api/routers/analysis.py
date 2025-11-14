from fastapi import APIRouter, Depends, Query, status, HTTPException
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
    if body.gasPrice:
        call_object["gasPrice"] = body.gasPrice
    if body.maxFeePerGas:
        call_object["maxFeePerGas"] = body.maxFeePerGas
    if body.maxPriorityFeePerGas:
        call_object["maxPriorityFeePerGas"] = body.maxPriorityFeePerGas
    if body.tx_type:
        call_object["type"] = body.tx_type

    # Treat empty strings as None for block bounds
    fb = (
        body.from_block
        if (body.from_block and body.from_block.strip() != "")
        else None
    )
    tb = (
        body.to_block if (body.to_block and body.to_block.strip() != "") else None
    )

    results = cc.simulate_and_check(
        call_object,
        block_tag=body.block_tag or "latest",
        from_block=fb,
        to_block=tb,
        latest_offset=body.latest_offset,
    )
    items = [
        {
            "address": addr,
            "first_time": info.get("first_time", False),
            "verification": info.get("verification"),
            "depth": info.get("depth"),
            "types": info.get("types"),
        }
        for addr, info in results.items()
    ]

    # Derive global status without short-circuiting; keep all details
    status = "OK"
    for it in items:
        if it.get("first_time", False):
            status = "DANGEROUS"
        else:
            v = it.get("verification") or {}
            ver = str(v.get("verification", "")).lower() if isinstance(v, dict) else ""
            if ver not in {"verified", "fully-verified"}:
                status = "DANGEROUS"

    return SimulationResponse(status=status, details=items)


def _validate_tx_hash(tx_hash: str) -> str:
    s = (tx_hash or "").strip().lower()
    if s.startswith("0x") and len(s) == 66 and all(c in "0123456789abcdef" for c in s[2:]):
        return s
    raise HTTPException(status_code=422, detail="Invalid tx_hash format")


@router.get(
    "/tx-risk/{tx_hash}",
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
    summary="Transaction risk by tx hash",
    description=(
        "Analyze a confirmed transaction by hash, list all touched contracts (including DELEGATECALL), "
        "and report whether it's the first interaction by the sender and the verification status."
    ),
)
async def get_tx_risk(
    tx_hash: str,
    from_block: str | None = Query(None, description="Lower bound block for first-time checks"),
    to_block: str | None = Query(None, description="Upper bound block for first-time checks"),
    latest_offset: int | None = Query(100, description="Limit first-time checks to N latest blocks"),
) -> SimulationResponse:
    # Basic tx hash validation and sanitize empty bounds
    tx_hash = _validate_tx_hash(tx_hash)
    fb = from_block if (from_block and from_block.strip() != "") else None
    tb = to_block if (to_block and to_block.strip() != "") else None
    lo = latest_offset

    results = cc.simulate_from_tx(
        tx_hash,
        from_block=fb,
        to_block=tb,
        latest_offset=lo,
    )
    items = [
        {
            "address": addr,
            "first_time": info.get("first_time", False),
            "verification": info.get("verification"),
            "depth": info.get("depth"),
            "types": info.get("types"),
        }
        for addr, info in results.items()
    ]

    status = "OK"
    for it in items:
        if it.get("first_time", False):
            status = "DANGEROUS"
        else:
            v = it.get("verification") or {}
            ver = str(v.get("verification", "")).lower() if isinstance(v, dict) else ""
            if ver not in {"verified", "fully-verified"}:
                status = "DANGEROUS"

    return SimulationResponse(status=status, details=items)
