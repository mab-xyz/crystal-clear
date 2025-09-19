from base_client import BaseClient
from typing import Dict

class SourcifyClient(BaseClient):
    def __init__(self):
        super().__init__(
            base_url="https://sourcify.dev/server/v2"
        )

    def check_contract_verified(self, address: str) -> Dict[str, str]:
        """
        Check if a contract is verified on Sourcify.

        Args:
            address: Ethereum address to check
        Returns:
            bool: True if the contract is verified, False otherwise
        """

        response = self.get(f"contract/1/{address}")
        if response:
            return {"address": response["address"], "match": response["match"], "verifiedAt": response["verifiedAt"]}
        return {"address": address, "match": "not_match", "verifiedAt": "na"}
