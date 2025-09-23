from .base_client import BaseClient
from typing import Optional, Dict, Any

class EtherscanClient(BaseClient):
    def __init__(self, api_key: str):
        super().__init__(
            base_url="https://api.etherscan.io/api",
            api_key=api_key
        )

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
            "address": address,
            "apikey": self.api_key
        }
        response = self.get("", params)

        if response and response.get('status') == '1' and 'result' in response:
            return response['result'][0] if response['result'] else None
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

        if contract_source and len(contract_source.get('SourceCode')) > 0:
            return {"address": address, "match": "match", "verifiedAt": "na"}
        return {"address": address, "match": "not_match", "verifiedAt": "na"}