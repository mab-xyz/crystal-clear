from typing import Any, Dict, Optional, List

from loguru import logger
from scsc.supply_chain import SupplyChain

from sqlmodel import Session

from core.config import settings
from core.exceptions import ContractAnalysisError, ExternalServiceError
from core.metadata import get_labels
from core.database import get_session
import crud.label


def analyze_contract_dependencies(
    session: Session,
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

        _validate_block_range(from_block, to_block)
        sc = SupplyChain(settings.eth_node_url, address)
        network = sc.get_network(from_block, to_block)
        network["nodes"] = _process_node_labels(session, network)
        logger.info(f"Analysis completed for {address}")
        return network

    except ValueError as e:
        logger.error(f"Contract analysis error: {e}")
        raise ContractAnalysisError(str(e)) from e
    except Exception as e:
        logger.error(f"External service error: {e}")
        raise ExternalServiceError(f"Failed to analyze contract: {str(e)}") from e

def _validate_block_range(from_block: Optional[str], to_block: Optional[str]) -> None:
    """Validate the block range if provided."""
    if to_block is not None and from_block is not None:
        try:
            if int(to_block) - int(from_block) > settings.MAX_BLOCK_RANGE:
                raise ValueError(
                    f"Block range exceeds maximum limit of {settings.MAX_BLOCK_RANGE} blocks."
                )
        except ValueError:
            raise ValueError("Block numbers must be valid integers")

def _process_node_labels(session: Session, network: Optional[Dict[str, Any]]) -> List[str]:
    if not network:
            raise ContractAnalysisError("No network data found")
    if "nodes" not in network:
        raise ContractAnalysisError("No nodes found in network data")
    if not isinstance(network["nodes"], list):
        raise ContractAnalysisError("Nodes data is not a list")
    nodes = network["nodes"]
    logger.info("Processing node labels.")
    logger.info("Fetching labels from database.")
    stored_labels = crud.label.get_labels(
        session, crud.label.AddressList(addresses=nodes)
    )
    logger.info(f"Stored labels: {stored_labels}")

    logger.info("Labels fetched from database.")
    missing_addresses = set(nodes) - set(stored_labels.keys())
    
    if not missing_addresses:
            return stored_labels

    # Fetch and store missing labels
    allium_labels = get_labels(list(missing_addresses), settings.allium_api_key)
    new_labels = {}

    for addr in missing_addresses:
        if allium_labels and addr.lower() in allium_labels:
            label = allium_labels[addr.lower()]
            new_labels[addr] = label
            logger.info(f"Label for {addr}: {label}")
            crud.label.create_label(
                session,
                crud.label.LabelCreate(address=addr, label=label)
            )
            logger.info(f"Label {label} for {addr} stored in database.")
        else:
            new_labels[addr] = addr
    return {**stored_labels, **new_labels}

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
