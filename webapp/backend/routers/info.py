from fastapi import APIRouter, status, Depends
from sqlalchemy.orm import Session
from loguru import logger

from core.database import get_session
from schemas.info import (
    LatestBlockResponse,
    DeploymentInfoResponse,
    VerificationInfoResponse,
)
from schemas.response import ErrorResponse
from services.info_service import (
    get_latest_block_number,
    get_deployment_data,
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
    return LatestBlockResponse(
        block_number=latest_block
    )

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
        404: {
            "description": "Contract information not found",
            "model": ErrorResponse,
        },
    },
    summary="Get contract information",
    description="Fetch contract information for a given address.",
)
async def get_contract_info(
    address: str,
):
    """
    Get contract information for a given address.
    """

    data = get_verification_data(address)

    mapping = {"match": "verified", "exact_match": "fully-verified"}
    
    return VerificationInfoResponse(
        address=data["address"],
        verfication=mapping[data["match"]],
        verifiedAt=data["verifiedAt"],
    )