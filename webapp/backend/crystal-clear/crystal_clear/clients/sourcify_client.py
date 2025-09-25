from .base_client import BaseClient
from typing import Dict
from .models import VerificationDetails

class SourcifyClient(BaseClient):
    def __init__(self):
        super().__init__(
            base_url="https://sourcify.dev/server/v2"
        )

    def check_contract_verified(self, address: str) -> VerificationDetails:
        """
        Check if a contract is verified on Sourcify.

        Args:
            address: Ethereum address to check
        Returns:
            bool: True if the contract is verified, False otherwise
        """

        response = self.get(f"contract/1/{address}")
        match_mapping = {"exact_match": "fully-verified", "match": "verified", "not_match": "not-verified"}
        if response:
            return VerificationDetails(
                address=response["address"],
                verification=match_mapping.get(response["match"], "not-verified"),
                verifiedAt=response["verifiedAt"]
            )
        return VerificationDetails(
            address=address,
            verification= "not-verified",
            verifiedAt="N/A"
        )
