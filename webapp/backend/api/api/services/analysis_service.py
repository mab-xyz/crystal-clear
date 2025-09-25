from typing import Any, Dict, Optional, List


from loguru import logger

from sqlmodel import Session

from api.core.config import settings, cc
from api.core.exceptions import InputValidationError, InternalServerError
from api.core.database import get_session
from api.services.info_service import get_verification_data, get_proxy_data, get_permissions_data, get_scorecard_data
from api.services.contract_service import ContractService
from api.crud import label as label_crud
from crystal_clear.traces import CallGraph

def analyze_contract_dependencies(
    session: Session,
    address: str,
    from_block: Optional[str] = None,
    to_block: Optional[str] = None,
) -> CallGraph:
    """
    Analyze contract dependencies.

    Args:
        address: Contract address to analyze
        from_block: Start block (optional)
        to_block: End block (optional)

    Returns:
        Dict containing the analysis results

    Raises:
        InputValidationError: If the input is invalid
        InternalServerError: If the analysis fails
    """
    try:
        # Perform analysis
        logger.info(f"Analyzing contract {address}")

        _validate_block_range(from_block, to_block)
        callgraph: CallGraph = cc.get_dependencies_full(
            address=address, from_block=from_block, to_block=to_block
        )
        callgraph.nodes = _process_node_labels(session, callgraph)
        logger.info(f"Analysis completed for {address}")
        return callgraph

    except ValueError as e:
        logger.error(f"Analyze contract dependencies: {e}")
        raise InputValidationError(str(e)) from e
    except Exception as e:
        logger.error(f"Internal server error: {e}")
        raise InternalServerError(f"Failed to analyze contract: {str(e)}") from e

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

def _process_node_labels(session: Session, callgraph: CallGraph) -> List[str]:
    nodes = list(callgraph.nodes.keys())
    logger.info("Processing node labels.")
    logger.info("Fetching labels from database.")
    stored_labels = label_crud.get_labels(
        session, label_crud.AddressList(addresses=nodes)
    )
    logger.info(f"Stored labels: {stored_labels}")

    logger.info("Labels fetched from database.")
    missing_addresses = set(nodes) - set(stored_labels.keys())
    
    if not missing_addresses:
            return stored_labels

    # Fetch and store missing labels
    allium_labels = cc.allium_client.get_labels(list(missing_addresses))
    new_labels = {}

    for addr in missing_addresses:
        if allium_labels and addr.lower() in allium_labels:
            label = allium_labels[addr.lower()]
            new_labels[addr] = label
            logger.info(f"Label for {addr}: {label}")
            label_crud.create_label(
                session,
                label_crud.LabelCreate(address=addr, label=label)
            )
            logger.info(f"Label {label} for {addr} stored in database.")
        else:
            new_labels[addr] = addr
    return {**stored_labels, **new_labels}


async def assess_contract_risk(address: str, session: Session) -> Dict[str, Any]:
    """
    Assess risk factors for a contract.

    Args:
        address: Contract address to analyze
        session: Database session for ContractService

    Returns:
        Dict containing risk factors

    Raises:
        ContractAnalysisError: If the analysis fails
        ExternalServiceError: If the external service is unavailable
    """
    logger.info(f"Analysing risk of contract {address}.")
    contract_service = ContractService(session)
    risk_factors = {}

    try:
        logger.info("Fetching verification data.")
        verification_data = get_verification_data(address)
        if verification_data.verification == "not-verified":
            risk_factors["verification"] = "Contract not verified"
    except Exception as e:
        logger.error(f"Verification data fetch error: {e}")
        risk_factors["verification"] = "Contract not verified"

    try:
        logger.info("Fetching proxy data.")
        data = get_proxy_data(address)
        if data.is_upgradeable:
            risk_factors["mutability"] = "Contract is an Upgradeable Proxy"
    except Exception as e:
        logger.error(f"Proxy data fetch error: {e}")
    try:
        logger.info("Fetching permissions data.")
        permissions_data = get_permissions_data(address)
        if len(permissions_data.permissions) > 0:
            risk_factors["permissions"] = "Contract has special permissions"
    except Exception as e:
        logger.error(f"Permissions data fetch error: {e}")

    try:
        logger.info("Fetching scorecard data.")
        scorecard_data = await get_scorecard_data(session, address)
        print(scorecard_data)
        scorecard_score = scorecard_data["raw"]["score"]
        if scorecard_score < 5:
            risk_factors["scorecard"] = f"Low scorecard score: {scorecard_score}/10"
    except Exception as e:
        logger.error(f"Scorecard data fetch error: {e}")
        risk_factors["repository"] = "Not available"

    try:
        logger.info("Fetching contract audits.")
        audits_data = await contract_service.get_contract_audits(address)
        if not audits_data["audits"]:
            risk_factors["audits"] = "No audits found"
    except Exception as e:
        logger.error(f"Contract audits fetch error: {e}")
        risk_factors["audits"] = "No audits found"

    return {
        "risk_factors": risk_factors,
    }
