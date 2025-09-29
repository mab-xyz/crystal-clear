from typing import Any, List, Optional

from crystal_clear import RiskAnalysis
from crystal_clear.traces import CallGraph
from loguru import logger
from sqlmodel import Session

from api.core.config import cc, settings
from api.core.exceptions import InputValidationError, InternalServerError
from api.crud import label as label_crud
from api.schemas.analysis import (
    AdditionalDependencyRisk,
    AdditionalRisk,
    AdditionalRiskFactors,
    RiskAnalysisResponse,
)
from api.services.contract_service import ContractService
from api.services.info_service import get_scorecard_data


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
            raise ValueError("Block numbers must be valid integers") from None


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
                session, label_crud.LabelCreate(address=addr, label=label)
            )
            logger.info(f"Label {label} for {addr} stored in database.")
        else:
            new_labels[addr] = addr
    return {**stored_labels, **new_labels}


async def assess_contract_risk(
    session: Session,
    address: str,
    from_block: Optional[str] = None,
    to_block: Optional[str] = None,
) -> RiskAnalysisResponse:
    """
    Assess risk factors for a contract.

    Args:
        address: Contract address to analyze.
        session: Database session for ContractService.
        from_block: Start block (optional).
        to_block: End block (optional).

    Returns:
        RiskAnalysisResponse containing risk factors.

    Raises:
        ContractAnalysisError: If the analysis fails.
        ExternalServiceError: If the external service is unavailable.
    """
    logger.info(f"Analyzing supply chain risk for contract {address}.")
    contract_service = ContractService(session)
    _validate_block_range(from_block, to_block)

    # Perform initial risk analysis
    analysis: RiskAnalysis = cc.get_risk_factors(
        address, scope="supply-chain", from_block=from_block, to_block=to_block
    )

    # Initialize the response object
    aggregated_risks = AdditionalRisk(
        verified=analysis.aggregated_risks.verified,
        risk_factors=AdditionalRiskFactors(
            audits=True,
            repository=True,
            scorecard=0,
            **analysis.aggregated_risks.risk_factors.to_dict(),
        ),
        details=None,
    )
    additional_risk_analysis = RiskAnalysisResponse(
        root_address=address,
        from_block=from_block,
        to_block=to_block,
        dependencies=[],
        aggregated_risks=aggregated_risks,
    )

    # Process dependencies
    for dep in analysis.dependencies:
        dep_risk = await _process_dependency_risk(session, contract_service, dep)
        additional_risk_analysis.dependencies.append(dep_risk)

        # Update aggregated risks based on dependency risks
        _update_aggregated_risks(aggregated_risks, dep_risk)

    # Finalize the scorecard average
    _finalize_scorecard_average(additional_risk_analysis)

    return additional_risk_analysis


async def _process_dependency_risk(
    session: Session,
    contract_service: ContractService,
    dependency: Any,
) -> AdditionalDependencyRisk:
    """
    Process the risk factors for a single dependency.

    Args:
        session: Database session.
        contract_service: Instance of ContractService.
        dependency: Dependency object from the analysis.

    Returns:
        AdditionalDependencyRisk object with calculated risk factors.
    """
    dep_risk = AdditionalDependencyRisk(
        address=dependency.address,
        dependency_depth=dependency.dependency_depth,
        verified=dependency.verified,
        risk_factors=AdditionalRiskFactors(
            audits=False,
            repository=False,
            scorecard=None,
            **dependency.risk_factors.to_dict(),
        ),
        details=dependency.details,
    )

    # Fetch scorecard data
    try:
        logger.info(f"Fetching scorecard data for {dependency.address}.")
        scorecard_data = await get_scorecard_data(session, dependency.address)
        dep_risk.risk_factors.scorecard = scorecard_data["raw"]["score"]
        dep_risk.risk_factors.repository = True
        dep_risk.details["scorecard"] = scorecard_data
        dep_risk.details["repository_url"] = scorecard_data["repo"]
    except Exception as e:
        logger.error(f"Error fetching scorecard data for {dependency.address}: {e}")

    # Fetch contract audits
    try:
        logger.info(f"Fetching contract audits for {dependency.address}.")
        audits_data = await contract_service.get_contract_audits(dependency.address)
        if audits_data["audits"]:
            dep_risk.risk_factors.audits = True
            dep_risk.details["audits"] = [
                audit.model_dump() for audit in audits_data["audits"]
            ]
    except Exception as e:
        logger.error(f"Error fetching contract audits for {dependency.address}: {e}")

    return dep_risk


def _update_aggregated_risks(
    aggregated_risks: AdditionalRisk, dep_risk: AdditionalDependencyRisk
) -> None:
    """
    Update the aggregated risks based on a dependency's risk factors.

    Args:
        aggregated_risks: Aggregated risks object to update.
        dep_risk: Dependency risk object to use for updates.
    """
    if not dep_risk.risk_factors.repository:
        aggregated_risks.risk_factors.repository = False
    if not dep_risk.risk_factors.audits:
        aggregated_risks.risk_factors.audits = False

    if dep_risk.risk_factors.scorecard is not None:
        if aggregated_risks.risk_factors.scorecard is not None:
            aggregated_risks.risk_factors.scorecard += dep_risk.risk_factors.scorecard
    else:
        aggregated_risks.risk_factors.scorecard = None


def _finalize_scorecard_average(risk_analysis: RiskAnalysisResponse) -> None:
    """
    Finalize the scorecard average for the aggregated risks.

    Args:
        risk_analysis: The risk analysis response object.
    """
    aggregated_risks = risk_analysis.aggregated_risks
    dependencies = risk_analysis.dependencies

    if aggregated_risks.risk_factors.scorecard is not None and len(dependencies) > 0:
        aggregated_risks.risk_factors.scorecard = round(
            aggregated_risks.risk_factors.scorecard / len(dependencies), 2
        )
