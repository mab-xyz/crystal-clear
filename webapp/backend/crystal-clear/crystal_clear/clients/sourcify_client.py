import logging

from .base_client import BaseClient
from .models import VerificationDetails


class SourcifyClient(BaseClient):
    def __init__(self, log_level: str = "INFO"):
        super().__init__(base_url="https://sourcify.dev/server/v2", log_level=log_level)
        self.logger = self.logger.getChild(self.__class__.__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))

    def check_contract_verified(self, address: str) -> VerificationDetails:
        """
        Check if a contract is verified on Sourcify.

        Args:
            address: Ethereum address to check
        Returns:
            bool: True if the contract is verified, False otherwise
        """
        try:
            response = self.get(f"contract/1/{address}")
            match_mapping = {
                "exact_match": "fully-verified",
                "match": "verified",
                "not_match": "not-verified",
            }
            if response:
                return VerificationDetails(
                    address=response["address"],
                    verification=match_mapping.get(response["match"], "not-verified"),
                    verifiedAt=response["verifiedAt"],
                    source="sourcify",
                )
            return VerificationDetails(
                address=address,
                verification="not-verified",
                verifiedAt="N/A",
                source="sourcify",
            )
        except Exception as e:
            self.logger.error(
                f"Error checking verification on Sourcify for {address}: {e}"
            )
            return VerificationDetails(
                address=address,
                verification="not-verified",
                verifiedAt="N/A",
                source="sourcify",
            )
