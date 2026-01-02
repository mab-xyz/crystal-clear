from crystal_clear.code_analyzer.analyzer import PermissionsInfo, ProxyInfo
from fastapi import APIRouter, Depends, status
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session

from src.api.core.config import settings
from src.api.core.database import get_session
from src.api.schemas.info import (
    LatestBlockResponse,
    DeploymentInfoResponse,
    LatestBlockResponse,
    PermissionsInfoResponse,
    ProxyInfoResponse,
    ScorecardResponse,
    VerificationInfoResponse,
)
from src.api.schemas.response import ErrorResponse
from src.api.services.info_service import (
    get_latest_block_number,
    get_deployment_data,
    get_latest_block_number,
    get_permissions_data,
    get_proxy_data,
    get_scorecard_data,
    get_verification_data,
)

router = APIRouter(
    prefix="/info",
    tags=["info"],
)


@router.get(
    "/block-latest",
    status_code=status.HTTP_200_OK,
    response_model=LatestBlockResponse,
    responses={
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        }
    },
    summary="Get latest block number",
    description="Fetch the latest block number from the Ethereum network.",
)
async def get_latest_block():
    """
    Get the latest block number from the Ethereum network.
    """
    latest_block = get_latest_block_number()
    return LatestBlockResponse(block_number=latest_block)


@router.get(
    "/deployment/{address}",
    status_code=status.HTTP_200_OK,
    response_model=DeploymentInfoResponse,
    responses={
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
        422: {
            "description": "Input validation error",
            "model": ErrorResponse,
        },
        404: {
            "description": "Deployment information not found",
            "model": ErrorResponse,
        },
    },
    summary="Get deployment information",
    description="Fetch deployment information for a given contract address.",
)
@cache(expire=settings.cache_ttl)
async def get_deployment_info(
    address: str,
    session: Session = Depends(get_session),
):
    """
    Get deployment information for a contract address.
    """
    return get_deployment_data(session, address)


@router.get(
    "/verification/{address}",
    status_code=status.HTTP_200_OK,
    response_model=VerificationInfoResponse,
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
    summary="Get contract information",
    description="Fetch contract information for a given address.",
)
@cache(expire=settings.cache_ttl)
async def get_contract_info(
    address: str,
):
    """
    Get contract information for a given address.
    """

    data = get_verification_data(address)

    return VerificationInfoResponse(**data.model_dump())


@router.get(
    "/reposcore/{address}",
    status_code=status.HTTP_200_OK,
    response_model=ScorecardResponse,
    responses={
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
        422: {
            "description": "Input validation error",
            "model": ErrorResponse,
        },
        404: {
            "description": "Scorecard data not found",
            "model": ErrorResponse,
        },
    },
    summary="Get scorecard data",
    description="Fetch scorecard data for a given repository.",
)
@cache(expire=settings.cache_ttl)
async def get_scorecard_info(
    address: str,
    session: Session = Depends(get_session),
):
    """
    Get scorecard data for a given smart contract address.
    """

    scorecard_data = await get_scorecard_data(session, address)

    source = (
        "public_api"
        if scorecard_data["source"] == "api"
        else "scorecard_docker"
    )
    org_repo = scorecard_data["repo"]

    return ScorecardResponse(
        repo_info=org_repo,
        source=source,
        score=scorecard_data["raw"]["score"],
        date=scorecard_data["raw"]["date"],
        checks=scorecard_data["raw"]["checks"],
    )


@router.get(
    "/proxy/{address}",
    status_code=status.HTTP_200_OK,
    response_model=ProxyInfoResponse,
    responses={
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
        422: {
            "description": "Input validation error",
            "model": ErrorResponse,
        },
        404: {
            "description": "Proxy information not found",
            "model": ErrorResponse,
        },
    },
    summary="Get proxy information",
    description="Fetch proxy information for a given address.",
)
@cache(expire=settings.cache_ttl)
async def get_proxy_info(
    address: str,
):
    """
    Get proxy information for a given contract address.
    """
    data: ProxyInfo = get_proxy_data(address)
    return ProxyInfoResponse(
        address=address,
        description=data.description,
        implementation_slot=data.implementation_slot,
        implementation_variable=data.implementation_variable,
        is_upgradeable=data.is_upgradeable,
        is_proxy=data.is_proxy,
    )


@router.get(
    "/permissions/{address}",
    status_code=status.HTTP_200_OK,
    response_model=PermissionsInfoResponse,
    responses={
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
        504: {
            "description": "Request timed out",
            "model": ErrorResponse,
        },
        422: {
            "description": "Input validation error",
            "model": ErrorResponse,
        },
        404: {
            "description": "Permissions information not found",
            "model": ErrorResponse,
        },
    },
    summary="Get permissioned functions for a contract",
    description="Fetch functions that have permission checks for a given contract address.",
)
@cache(expire=settings.cache_ttl)
async def get_permissions_info(address: str):
    """
    Get permissioned functions for a contract address.
    """

    data: PermissionsInfo = get_permissions_data(address)

    return PermissionsInfoResponse(
        address=address, permissions=data.permissions
    )
