import logging
from typing import Any, Dict

from pydantic import BaseModel, Field
from slither.detectors.proxy.proxy_patterns import ProxyPatterns
from slither.slither import Slither

from crystal_clear.clients import (
    EtherscanClient,
    SourcifyClient,
    VerificationDetails,
)

from .permissions import PermissionsInfo, detect_permissions


class ProxyInfo(BaseModel):
    """Model representing proxy information of a contract."""

    description: str = Field(
        ..., description="Description of the proxy pattern detected"
    )
    implementation_slot: str = Field(
        ..., description="Storage slot of the implementation contract address"
    )
    implementation_variable: str = Field(
        ..., description="Variable holding the implementation contract address"
    )
    is_upgradeable: bool = Field(
        ..., description="Indicates if the contract is upgradeable"
    )
    is_proxy: bool = Field(..., description="Indicates if the contract is a proxy")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class RiskFactors(BaseModel):
    """Model representing risk information of a contract."""

    upgradeability: bool = Field(None, description="Contract is upgradeable")
    permissioned: bool = Field(None, description="Contract has permissioned functions")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def __str__(self):
        str_parts = []
        if self.upgradeability:
            str_parts.append("Contract is upgradeable.")
        if self.permissioned:
            str_parts.append("Contract has permissioned functions.")

        return " ".join(str_parts) if str_parts else "No risk factors identified."


class Risk(BaseModel):
    verified: bool = Field(..., description="Indicates if the contract is verified")
    risk_factors: RiskFactors = Field(
        ..., description="Identified risk factors of the contract"
    )
    details: Dict[str, Any] | None = Field(
        default=None, description="Detailed analysis results"
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class Analyzer:
    def __init__(self, etherscan_api_key: str, address: str, log_level: str = "INFO"):
        self.etherscan_api_key = etherscan_api_key
        self.address = address
        self.slither = None
        self.log_level = log_level.upper()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(getattr(logging, self.log_level))
        crytic_logger = logging.getLogger("CryticCompile")
        crytic_logger.setLevel(getattr(logging, self.log_level))

    def _initialize_slither(self):
        if not self.slither:
            try:
                self.slither = Slither(
                    self.address,
                    etherscan_api_key=self.etherscan_api_key,
                    disallow_partial=True,
                    disable_solc_warnings=True,
                )
            except Exception as e:
                verification = self.get_verification_info_etherscan()
                if verification.verification == "not-verified":
                    raise ValueError(
                        f"Contract at address {self.address} is not verified on Etherscan."
                    ) from None
                raise ValueError(
                    f"Failed to initialize Slither for address {self.address}: {e}"
                ) from e

    def get_main_contract_name(self) -> str:
        self._initialize_slither()
        return next(iter(self.slither._crytic_compile.compilation_units.keys()))

    def get_proxy_info(self) -> ProxyInfo:
        self._initialize_slither()
        self.slither.register_detector(ProxyPatterns)
        results = self.slither.run_detectors()

        assert len(results) == 1
        mainContract = self.get_main_contract_name()

        proxy_info = ProxyInfo(
            description="Not a Proxy",
            implementation_slot="N/A",
            implementation_variable="N/A",
            is_upgradeable=False,
            is_proxy=False,
        )
        for result in results[0]:
            if result["contract"].startswith(mainContract):
                proxy_info.description = result.get("description", "")
                proxy_info.implementation_slot = result["features"].get(
                    "impl_address_slot", ""
                )
                proxy_info.implementation_variable = result["features"].get(
                    "impl_address_variable", ""
                )

        contract = self.slither.get_contract_from_name(mainContract)[0]
        proxy_info.is_upgradeable = contract._is_upgradeable_proxy
        proxy_info.is_proxy = contract._is_proxy

        return proxy_info

    def get_permissions_info(self) -> PermissionsInfo:
        self._initialize_slither()
        permissions = detect_permissions(self.slither)
        return permissions

    def get_verification_info_etherscan(self) -> VerificationDetails:
        etherscan_client = EtherscanClient(self.etherscan_api_key)
        verification_info = etherscan_client.check_contract_verified(self.address)
        return verification_info

    def get_veritification_info(self) -> VerificationDetails:
        sourcify_client = SourcifyClient()
        verification = sourcify_client.check_contract_verified(self.address)
        if verification.verification == "not-verified":
            verification = self.get_verification_info_etherscan()
        return verification

    def risk(self) -> Risk:
        risk_factors = RiskFactors(upgradeability=False, permissioned=False)
        risk_result = Risk(verified=False, risk_factors=risk_factors, details={})
        verification = self.get_veritification_info()
        risk_result.details["verification_info"] = verification.to_dict()
        if verification.verification == "not-verified":
            return risk_result
        risk_result.verified = True
        try:
            self._initialize_slither()
        except Exception as e:
            risk_result.details[
                "slither_error"
            ] = f"Failed to analyze contract with Slither: {e}"
            return risk_result
        proxy_info = self.get_proxy_info()
        if proxy_info.is_proxy and proxy_info.is_upgradeable:
            risk_result.risk_factors.upgradeability = True
        permissions_info = self.get_permissions_info()
        permissioned_functions = len(permissions_info.permissions)
        if permissioned_functions > 0:
            risk_result.risk_factors.permissioned = True
        risk_result.details["proxy_info"] = proxy_info.to_dict()
        risk_result.details["permissions_info"] = permissions_info.to_dict()
        return risk_result
