from loguru import logger
from web3 import Web3
from typing import Dict, Optional

from core.config import settings
from core.exceptions import ExternalServiceError
from core.metadata import get_deployment

def get_latest_block_number() -> int:
    """
    Get the latest block number from the Ethereum network.

    Returns:
        Latest block number
    """
    try:
        w3 = Web3(Web3.HTTPProvider(settings.eth_node_url))
        latest_block = w3.eth.get_block_number()
        return latest_block
    except Exception as e:
        logger.error(f"Error fetching latest block: {e}")
        raise ExternalServiceError(f"Failed to get latest block: {str(e)}") from e


def get_deployment_data(address: str) -> Optional[Dict[str, str]]:
    """
    Get the deployment information for a given contract address.

    Args:
        address: Ethereum contract address

    Returns:
        Deployment information
    """
    return get_deployment(address, settings.allium_api_key)