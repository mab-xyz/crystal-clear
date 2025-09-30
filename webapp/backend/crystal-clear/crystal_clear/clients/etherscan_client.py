from typing import Any, Dict, Optional

from .base_client import BaseClient
from .models import VerificationDetails


class EtherscanClient(BaseClient):
    def __init__(self, api_key: str, log_level: str = "INFO"):
        super().__init__(
            base_url="https://api.etherscan.io/v2/api",
            log_level=log_level,
        )
        self.etherscan_api_key = api_key

    def get_contract_source(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Get contract source code for a given Ethereum address.

        Args:
            address: Ethereum address to lookup
        Returns:
            dict: Dictionary containing contract source code information
        """

        params = {
            "module": "contract",
            "action": "getsourcecode",
            "chainid": 1,
            "address": address,
            "apikey": self.etherscan_api_key,
        }
        response = self.get("", params=params)
        if response and response.get("status") == "1" and "result" in response:
            return response["result"][0] if response["result"] else None
        return None

    def check_contract_verified(self, address: str) -> Dict[str, str]:
        """
        Check if a contract is verified on Etherscan.

        Args:
            address: Ethereum address to check
        Returns:
            bool: True if the contract is verified, False otherwise
        """

        contract_source = self.get_contract_source(address)

        if contract_source and len(contract_source.get("SourceCode")) > 0:
            return VerificationDetails(
                address=address,
                verification="verified",
                verifiedAt="N/A",
                source="etherscan",
            )
        return VerificationDetails(
            address=address,
            verification="not-verified",
            verifiedAt="N/A",
            source="etherscan",
        )
