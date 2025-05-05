from typing import Any, Dict, Optional

from loguru import logger
from scsc.supply_chain import SupplyChain

from web3 import Web3

from typing import Tuple

from core.config import settings
from core.exceptions import ContractAnalysisError, ExternalServiceError


def analyze_contract_dependencies(
    address: str,
    from_block: Optional[str] = None,
    to_block: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze contract dependencies.

    Args:
        address: Contract address to analyze
        from_block: Start block (optional)
        to_block: End block (optional)

    Returns:
        Dict containing the analysis results

    Raises:
        ContractAnalysisError: If the analysis fails
        ExternalServiceError: If the external service is unavailable
    """
    try:
        # Perform analysis
        logger.info(f"Analyzing contract {address}")

        if to_block is not None and from_block is not None:
            if int(to_block) - int(from_block) > settings.MAX_BLOCK_RANGE:
                raise ValueError(
                    f"Block range exceeds maximum limit of {settings.MAX_BLOCK_RANGE} blocks."
                )
        sc = SupplyChain(settings.eth_node_url, address)
        network = sc.get_network(from_block, to_block)

        logger.info(f"Analysis completed for {address}")
        return network

    except ValueError as e:
        logger.error(f"Contract analysis error: {e}")
        raise ContractAnalysisError(str(e)) from e
    except Exception as e:
        logger.error(f"External service error: {e}")
        raise ExternalServiceError(f"Failed to analyze contract: {str(e)}") from e


def calculate_contract_risk(address: str) -> Dict[str, Any]:
    """
    Calculate risk score for a contract.

    Args:
        address: Contract address to analyze

    Returns:
        Dict containing risk score and factors

    Raises:
        ContractAnalysisError: If the analysis fails
        ExternalServiceError: If the external service is unavailable
    """
    try:
        logger.info(f"Analysing risk of contract {address}.")

        return {"risk_score": 42, "risk_factors": {"TBD": "TBD"}}

    except Exception as e:
        logger.error(f"Risk analysis error: {e}")
        raise ExternalServiceError(f"Failed to analyse risk: {str(e)}") from e

def calculate_block_range(days: int) -> Tuple[int, int]:
    """
    Get block range for the last n days.

    Args:
        days: Number of days to look back

    Returns:
        Tuple containing start and end block numbers
    """
    try:
        logger.info(f"Getting block range for the last {days} days.")
        
        w3 = Web3(Web3.HTTPProvider(settings.eth_node_url))
        latest_block = w3.eth.get_block_number()
        average_block_time = 12
        # 86400 = 24*60*60 seconds in a day
        blocks_in_n_days = (days * 86400) // average_block_time 
        from_block = latest_block - blocks_in_n_days
        to_block = latest_block

        return from_block, to_block

    except Exception as e:
        logger.error(f"Error getting block range: {e}")
        raise ExternalServiceError(f"Failed to get block range: {str(e)}") from e
