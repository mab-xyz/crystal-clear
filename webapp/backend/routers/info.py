from fastapi import APIRouter, Query, status, Depends
from sqlalchemy.orm import Session
from loguru import logger
from pydantic import ValidationError

from core.database import get_session
from core.exceptions import ExternalServiceError
from schemas.info import (
    LatestBlockResponse,
    DeploymentInfoResponse,
)
from services.info_service import (
    get_latest_block_number,
    get_deployment_data,
)

router = APIRouter(
    prefix="/info",
    tags=["info"],
)

@router.get(
    "/block-latest",
    status_code=status.HTTP_200_OK,
    response_model=LatestBlockResponse,
    summary="Get latest block number",
    description="Fetch the latest block number from the Ethereum network.",
)
async def get_latest_block():
    """
    Get the latest block number from the Ethereum network.
    """
    try:
        latest_block = get_latest_block_number()
        return LatestBlockResponse(
            block_number=latest_block
        )
    except Exception as e:
        logger.error(f"Error fetching latest block: {e}")
        raise ExternalServiceError(f"An unexpected error occurred: {str(e)}") from e

@router.get(
    "/deployment/{address}",
    status_code=status.HTTP_200_OK,
    response_model=DeploymentInfoResponse,
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
    try:
        deployment_info = get_deployment_data(session, address)
        if not deployment_info:
            raise ValueError("No deployment information found.")
        print(deployment_info)
        return deployment_info
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise ExternalServiceError(f"Invalid input: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error fetching deployment info: {e}")
        raise ExternalServiceError(f"An unexpected error occurred: {str(e)}") from e
