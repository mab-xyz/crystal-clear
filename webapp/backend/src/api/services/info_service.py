import json
import subprocess
from typing import Dict, Optional

import requests
from src.api.clients.allium_client import AlliumClient
from fastapi import HTTPException
from loguru import logger
from sqlmodel import Session
from web3 import Web3

import src.api.crud.deployment as crud_deployment
from src.api.core.config import get_eth_node_url, settings
from src.api.core.rpc_health import make_tracked_w3
from src.api.core.exceptions import (
    InputValidationError,
    InternalServerError,
    NotFoundError,
)
from src.api.core.proxy import detect_delegatecall_and_address
from src.api.models.deployment import DeploymentCreate
from src.api.services.contract_service import ContractService
from src.api.core.permissions import get_permissions


def get_latest_block_number() -> int:
    """
    Get the latest block number from the Ethereum network.

    Returns:
        Latest block number
    """
    try:
        w3 = make_tracked_w3(get_eth_node_url())
        latest_block = w3.eth.get_block_number()
        return latest_block
    except Exception as e:
        logger.error(f"Error fetching latest block: {e}")
        raise InternalServerError(
            f"Failed to get latest block: {str(e)}"
        ) from e


def get_deployment_data(
    session: Session, address: str
) -> Optional[Dict[str, str]]:
    """
    Get the deployment information for a given contract address.

    Args:
        address: Ethereum contract address

    Returns:
        Deployment information
    """
    try:
        # check if address is valid for ethereum
        if not Web3.is_address(address):
            raise InputValidationError(f"Invalid Ethereum address: {address}")

        deployment_info = crud_deployment.get_deployment(
            session, address.lower()
        )
        if not deployment_info:
            client = AlliumClient(settings.allium_api_key)
            deployment_info = client.get_deployment(address)
            if not deployment_info:
                raise NotFoundError(
                    f"No deployment information found for {address}"
                )
            entry = DeploymentCreate(
                address=deployment_info["address"],
                deployer=deployment_info["deployer"],
                deployer_eoa=deployment_info["deployer_eoa"],
                tx_hash=deployment_info["transaction_hash"],
                block_number=deployment_info["block_number"],
            )
            deployment_info = crud_deployment.create_deployment(session, entry)
            if not deployment_info:
                raise InternalServerError(
                    f"Failed to create deployment entry for {address}"
                ) from None
        return deployment_info
    except (InputValidationError, NotFoundError) as e:
        logger.error(f"Error: {e}")
        raise e
    except Exception as e:
        logger.error(f"Error fetching deployment data: {e}")
        raise InternalServerError(
            f"Failed to get deployment data: {str(e)}"
        ) from e


def get_verification_data(address: str) -> Optional[Dict[str, str]]:
    """
    Get the verification information for a given contract address.

    Args:
        address: Ethereum contract address

    Returns:
        Verification information
    """
    try:
        # check if address is valid for ethereum
        if not Web3.is_address(address):
            raise InputValidationError(f"Invalid Ethereum address: {address}")

        request_url = f"https://sourcify.dev/server/v2/contract/1/{address}"

        response = requests.get(request_url)
        verification_info = response.json()

        if (
            response.status_code != 200
            or not verification_info
            or verification_info.get("match") == "null"
        ):
            etherscan_url = f"https://api.etherscan.io/api?module=contract&action=getsourcecode&address={address}&apikey={settings.etherscan_api_key}"
            response = requests.get(etherscan_url)
            if response.status_code == 200:
                etherscan_data = response.json()["result"]
                if (
                    len(etherscan_data) > 0
                    and len(etherscan_data[0].get("SourceCode")) > 0
                ):
                    return {
                        "address": address,
                        "match": "match",
                        "verifiedAt": "na",
                    }

                return {
                    "address": address,
                    "match": "not_match",
                    "verifiedAt": "na",
                }

        return verification_info
    except InputValidationError as e:
        logger.error(f"Error: {e}")
        raise e
    except Exception as e:
        logger.error(f"Error fetching verification data: {e}")
        raise InternalServerError(
            f"Failed to get verification data: {str(e)}"
        ) from e


async def get_scorecard_data(session: Session, address: str) -> Optional[Dict]:
    """
    Run OpenSSF Scorecard on the given GitHub repo.(We only support GitHub for now)

    Args:
        repo_url: GitHub repository URL (e.g., https://github.com/org/repo)

    Returns:
        Scorecard JSON result

    """
    try:
        # check if address is valid for ethereum
        if not Web3.is_address(address):
            raise InputValidationError(f"Invalid Ethereum address: {address}")

        contract_service = ContractService(session)
        repo_data = await contract_service.get_contract_repository(address)
        url = repo_data["repository"].url
        url_elms = url.split("/")
        org, repo = url_elms[-2], url_elms[-1]
    except InputValidationError as e:
        logger.error(f"Input validation error: {e}")
        raise e
    except NotFoundError as e:
        logger.error(f"Repository not found: {e}")
        raise NotFoundError(
            f"No repository information found for {address}"
        ) from e
    except HTTPException as e:
        logger.error(f"HTTP error: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Error fetching repository data: {e}")
        raise InternalServerError(
            f"Failed to get repository data: {str(e)}"
        ) from e

    path = f"{org}/{repo}"

    try:
        api_url = (
            f"https://api.securityscorecards.dev/projects/github.com/{path}"
        )

        logger.info(f"Checking Scorecard API: {api_url}")
        response = requests.get(api_url)
        logger.info(f"status code: {response.status_code}")

        if response.status_code == 200:
            logger.info("Scorecard data found via public API.")
            return {"source": "api", "repo": path, "raw": response.json()}

        logger.warning(
            f"Scorecard not found via public API for {path}. Falling back to Docker..."
        )

        repo_url = f"github.com/{path}"

        command = [
            "docker",
            "run",
            "--rm",
            "-e",
            f"GITHUB_AUTH_TOKEN={settings.github_token}",
            "gcr.io/openssf/scorecard:stable",
            f"--repo={repo_url}",
            "--format=json",
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Scorecard Docker run failed: {result.stderr}")
            raise InternalServerError("Scorecard analysis failed.")

        return {
            "source": "docker",
            "repo": path,
            "raw": json.loads(result.stdout),
        }
    except InputValidationError as e:
        logger.error(f"Input validation error: {e}")
        raise e
    except requests.RequestException as e:
        logger.error(f"Scorecard API request error: {e}")
        raise InternalServerError(
            "Failed to reach Scorecard public API."
        ) from e
    except subprocess.SubprocessError as e:
        logger.error(f"Subprocess error: {e}")
        raise InternalServerError("Failed to run Scorecard subprocess.") from e
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        raise InternalServerError("Failed to parse Scorecard output.") from e
    except Exception as e:
        logger.error(f"Unexpected Scorecard error: {e}")
        raise InternalServerError(
            "Unexpected error during Scorecard analysis."
        ) from e


def get_proxy_data(address: str) -> Optional[Dict[str, str]]:
    """
    Get proxy information for a given contract address.

    Args:
        address: Ethereum contract address

    Returns:
        Proxy information
    """
    try:
        # check if address is valid for ethereum
        if not Web3.is_address(address):
            raise InputValidationError(f"Invalid Ethereum address: {address}")

        proxy_type, message, all_lines = detect_delegatecall_and_address(
            address, get_eth_node_url()
        )

        return {"address": address, "type": proxy_type, "message": message}
    except InputValidationError as e:
        logger.error(f"Error: {e}")
        raise e
    except Exception as e:
        logger.error(f"Error fetching proxy info: {e}")
        raise InternalServerError(f"Failed to get proxy info: {str(e)}") from e


def get_permissions_data(address: str) -> Dict[str, str]:
    """
    Get permissioned functions of a contract.

    Args:
        address: Ethereum contract address

    Returns:
        Permissioned functions
    """
    try:
        # check if address is valid for ethereum
        if not Web3.is_address(address):
            raise InputValidationError(f"Invalid Ethereum address: {address}")

        permissions = get_permissions(address)

        return permissions
    except InputValidationError as e:
        logger.error(f"Error: {e}")
        raise e
    except ValueError as ve:
        logger.error(f"Value error: {ve}")
        raise NotFoundError(f"No permissions data found for {address}") from ve
    except Exception as e:
        logger.error(f"Error fetching permissions data: {e}")
        raise InternalServerError(
            f"Failed to get permissions data: {str(e)}"
        ) from e
