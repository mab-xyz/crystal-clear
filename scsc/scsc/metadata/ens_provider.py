from typing import Dict, Optional

from ens import ENS
from web3 import Web3

from .base_provider import BaseProvider


class ENSProvider(BaseProvider):
    def __init__(self, url: str):
        w3 = Web3(Web3.HTTPProvider(url))
        self.ns = ENS.from_web3(w3)

    def get_label(self, address: str) -> Optional[str]:
        try:
            return self.ns.name(address)
        except Exception:
            return None

    def get_labels(self, addresses: list[str]) -> Dict[str, str]:
        return {
            addr: label
            for addr in addresses
            if (label := self.get_label(addr)) is not None
        }

    def get_metadata(self, address: str) -> Dict[str, str]:
        metadata = {}
        try:
            name = self.ns.name(address)
            print(name)
            if name:
                metadata["name"] = name
                try:
                    metadata["url"] = self.ns.get_text(name, "url")
                except Exception:
                    pass
                try:
                    metadata["owner"] = self.ns.owner(name)
                except Exception:
                    pass
        except Exception:
            pass
        return metadata


# if __name__ == "__main__":
# w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
# ns = ENS.from_web3(w3)
# # res =  ns.address("ethereum.eth")
# # print(res)
# # print(ns.namehash("ethereum.eth"))
# # print(ns.resolver("ethereum.eth").address)
# # eth_address = ns.address('monicajin.eth')
# # assert eth_address == '0xFe89cc7aBB2C4183683ab71653C4cdc9B02D44b7'
# # print(eth_address)
# address = ns.address('uniswap.eth')
# print(address)
# print(ns.name('0x225f137127d9067788314bc7fcc1f36746a3c3B5'))
# url = ns.get_text('uniswap.eth', 'url')
# print(url)
# owner = ns.owner('uniswap.eth')
# print(owner)
# # print(ns.name('0x1a9C8182C09F50C8318d769245beA52c32BE35BC'))
# # print(ns.resolver("ethereum.eth"))

# # eth_address = ns.address('ens.eth', coin_type=60)  # ETH is coin_type 60
# # assert eth_address == '0xFe89cc7aBB2C4183683ab71653C4cdc9B02D44b7'
# # domain = ns.name('0xFe89cc7aBB2C4183683ab71653C4cdc9B02D44b7')

# # print(domain)
# # assert domain == 'ens.eth'
