from typing import Any, Dict, Optional, List

from loguru import logger
from scsc.supply_chain import SupplyChain

from web3 import Web3
import requests

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
        if network and "nodes" in network:
            labels = get_labels(list(network["nodes"]), settings.allium_api_key)
            nodes = {}
            if labels:
                for node in network["nodes"]:
                    if node.lower() in labels:
                        nodes[node] = labels[node.lower()]
                    else:
                        nodes[node] = node
        network["nodes"] = nodes
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

def get_labels(addresses: list, ALLIUM_API_KEY: str) -> Optional[dict]:
    """
    Get labels for multiple Ethereum addresses from Etherscan.

    Args:
        addresses: List of Ethereum addresses to lookup

    Returns:
        dict: Dictionary mapping addresses to their labels
    """
    try:
        params = ""
        for address in addresses:
            # lowercase the address to ensure consistency
            params += f"'{address.lower()}',"
        params = params[:-1]  # Remove the last comma
        parameters = {"param_477":f"{params}"}
        print(parameters)

        response = requests.post(
            "https://api.allium.so/api/v1/explorer/queries/g23nJaD4vABOS6utYocZ/run",
            json=parameters,
            headers={"X-API-Key": ALLIUM_API_KEY},
        )

        print(response.json())
        json = response.json()
        if 'data' in json and len(json['data']) > 0:
            labels = {item['address']: item['name'] for item in json['data']}
            return labels
        else:
            return None
    except Exception as e:
        print(f"Error getting labels for addresses {addresses}: {e}")
        return None