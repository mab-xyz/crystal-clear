from slither.slither import Slither
from slither.detectors.proxy.proxy_patterns import ProxyPatterns
from permissions import detect_permissions
from typing import List

class Analyzer:
    def __init__(self, etherscan_api_key: str, address: str):
        self.etherscan_api_key = etherscan_api_key
        self.address = address
        self.slither = Slither(self.address, etherscan_api_key=self.etherscan_api_key, disallow_partial=True)
    def get_main_contract_name(self) -> str:
        return next(iter(self.slither._crytic_compile.compilation_units.keys()))
    
    def get_proxy_info(self) -> dict:
        self.slither.register_detector(ProxyPatterns)
        results = self.slither.run_detectors()

        assert len(results) == 1
        mainContract = self.get_main_contract_name()

        proxy_info = {}
        proxy_info["description"] = ""
        for result in results[0]:
            if result["contract"].startswith(mainContract):
                proxy_info["description"] = result["description"]
       

        contract = self.slither.get_contract_from_name(mainContract)[0]
        proxy_info["is_upgradeable"] = contract._is_upgradeable_proxy
        proxy_info["is_proxy"] = contract._is_proxy

        return proxy_info
    
    def get_permissions_info(self) -> List[dict]:
        permissions = detect_permissions(self.slither)
        return permissions
    
    def analyze(self) -> dict:
        analysis = {}
        analysis["proxy_info"] = self.get_proxy_info()
        analysis["permissions_info"] = self.get_permissions_info()
        return analysis

# if __name__ == "__main__":
    # analyzer = Analyzer(etherscan_api_key="", address="")
    # result = analyzer.analyze()
