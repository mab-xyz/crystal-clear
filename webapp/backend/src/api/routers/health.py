from fastapi import APIRouter, status
from loguru import logger

from src.api.core.config import get_eth_node_url
from src.api.core.rpc_health import make_tracked_w3

router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if the API is running and healthy.",
)
async def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "healthy"}


@router.get(
    "/eth-node",
    status_code=status.HTTP_200_OK,
    summary="Ethereum node health check",
    description="Check if the Ethereum node connection is working.",
)
async def eth_node_health_check():
    """
    Check if the Ethereum node connection is working.
    """
    try:
        w3 = make_tracked_w3(get_eth_node_url())
        connected = w3.is_connected()
        return {
            "status": "healthy",
            "eth_node": "connected" if connected else "disconnected",
        }
    except Exception as e:
        logger.error(f"Ethereum node health check failed: {e}")
        return {
            "status": "unhealthy",
            "eth_node": "disconnected",
            "error": str(e),
        }
