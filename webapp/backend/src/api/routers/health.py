import asyncio

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import text

from src.api.core.config import get_eth_node_url
from src.api.core.database import engine
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
    "/db",
    status_code=status.HTTP_200_OK,
    summary="Database health check",
    description="Runs SELECT 1 on Postgres (5 s timeout); 503 when it fails.",
)
async def db_health_check():
    def _probe() -> None:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    try:
        await asyncio.wait_for(asyncio.to_thread(_probe), timeout=5)
    except Exception as exc:  # noqa: BLE001 - any failure means unhealthy
        logger.error("database health check failed: {}", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "component": "postgres"},
        )
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
