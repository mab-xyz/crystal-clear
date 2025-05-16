from loguru import logger
from web3 import Web3
from typing import Dict, Optional

from sqlmodel import Session

from core.config import settings
from core.exceptions import ExternalServiceError
from core.metadata import get_deployment

import crud.deployment
from models.deployment import DeploymentCreate

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


def get_deployment_data(session: Session, address: str) -> Optional[Dict[str, str]]:
    """
    Get the deployment information for a given contract address.

    Args:
        address: Ethereum contract address

    Returns:
        Deployment information
    """
    try:
        deployment_info = crud.deployment.get_deployment(session, address.lower())
        if not deployment_info:
            deployment_info = get_deployment(address, settings.allium_api_key)
            entry = DeploymentCreate(
                address=deployment_info["address"],
                deployer=deployment_info["deployer"],
                deployer_eoa=deployment_info["deployer_eoa"],
                tx_hash=deployment_info["transaction_hash"],
                block_number=deployment_info["block_number"]
            )
            deployment_info = crud.deployment.create_deployment(session, entry)
        return  deployment_info
    except Exception as e:
        logger.error(f"Error fetching deployment data: {e}")
        raise ExternalServiceError(f"Failed to get deployment data: {str(e)}") from e
