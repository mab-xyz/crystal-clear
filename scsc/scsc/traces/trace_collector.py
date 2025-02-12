import logging
from typing import Any, Dict, List, Set

from hexbytes import HexBytes
from web3 import Web3


class TraceCollector:
    def __init__(self, url: str):
        """
        Initializes the TraceCollector with a URL and log level.
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        self.w3 = Web3(Web3.HTTPProvider(url))
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to the Ethereum node.")
        self.logger.info("Connected to the Ethereum node.")

        # Reference bytecode for "x0" - this should be the actual bytecode
        self.x0_bytecode = "x0"  # Replace with actual x0 bytecode

    def _validate_contract(self, address: str, block: str) -> bool:
        """
        Validates contract address and checks if it's different from x0
        """
        if not Web3.is_address(address):
            self.logger.error(f"Invalid contract address format: {address}")
            return False

        try:
            code = self.w3.eth.get_code(address, block_identifier=block)
            if len(code) == 0:
                self.logger.error(f"No code at address: {address}")
                return False

            if code.hex() == self.x0_bytecode:
                self.logger.info(f"Contract at {address} matches x0 contract")
                return False

            return True
        except Exception as e:
            self.logger.error(f"Error validating contract: {e}")
            return False

    def _filter_txs_from(
        self, from_block: str, to_block: str, contract_address: str
    ) -> Set[str]:
        """
        Filters transactions from a given block range and contract address.
        """
        self.logger.info(
            f"Filtering transactions from block {from_block} \
              to {to_block} for contract {contract_address}."
        )
        filter_params = {
            "fromBlock": from_block,
            "toBlock": to_block,
            "fromAddress": [contract_address],
        }
        try:
            res = self.w3.tracing.trace_filter(filter_params)
        except Exception as e:
            self.logger.error(f"Error filtering transactions: {e}")
            return set()

        if res is None:
            return set()
        tx_hashes = {
            (
                r["transactionHash"].to_0x_hex()
                if type(r["transactionHash"]) is HexBytes
                else r["transactionHash"]
            )
            for r in res
            if r["type"] == "call"
        }
        self.logger.info(f"Found {len(tx_hashes)} transactions.")
        return tx_hashes

    def _get_calls_from_tx(self, tx_hash: str) -> Dict[str, Any]:
        """
        Gets calls from a transaction hash.
        """
        self.logger.info(f"Tracing transaction {tx_hash}.")
        try:
            res = self.w3.geth.debug.trace_transaction(
                tx_hash, {"tracer": "callTracer"}
            )
        except Exception as e:
            self.logger.error(f"Error tracing transaction {tx_hash}: {e}")
            return {}
        return res

    def _extract_all_subcalls(
        self, call: Dict[str, Any], calls: List[Dict[str, str]]
    ) -> None:
        """
        Recursively extracts all subcalls from a call.
        """
        calls.append(
            {"from": call["from"], "to": call["to"], "type": call["type"]}
        )
        for subcall in call.get("calls", []):
            self._extract_all_subcalls(subcall, calls)

    def _extract_calls(
        self,
        call: Dict[str, Any],
        contract_address: str,
        calls: List[Dict[str, str]],
    ) -> None:
        """
        Extracts calls from a call and its subcalls.
        """
        if call["from"].lower() == contract_address.lower():
            calls.append(
                {"from": call["from"], "to": call["to"], "type": call["type"]}
            )
            for subcall in call.get("calls", []):
                self._extract_all_subcalls(subcall, calls)
        for subcall in call.get("calls", []):
            self._extract_calls(subcall, contract_address, calls)

    def get_calls(
        self, tx_hashes: Set[str], contract_address: str
    ) -> List[Dict[str, str]]:
        """
        Gets calls for a given set of transaction hashes and contract address.
        """
        self.logger.info(f"Getting calls for contract {contract_address}.")
        calls = []
        for h in tx_hashes:
            res = self._get_calls_from_tx(h)
            if res:
                self._extract_calls(res, contract_address, calls)
        self.logger.info(f"Extracted {len(calls)} calls.")
        return calls

    def _filter_contract_calls(
        self, calls: List[Dict[str, str]], to_block
    ) -> List[Dict[str, str]]:
        """
        Filters calls to contract addresses.
        """
        return [
            c
            for c in calls
            if self._validate_contract(c["to"], to_block)
            and self._validate_contract(c["from"], to_block)
        ]

    def get_calls_from(
        self, from_block: str, to_block: str, contract_address: str
    ) -> List[Dict[str, str]]:
        """
        Gets calls from a given block range and contract address.
        """
        self.logger.info(
            f"Getting calls from block {from_block} \
            to {to_block} for contract {contract_address}."
        )
        if not self._validate_contract(contract_address, to_block):
            raise ValueError("Invalid contract address or bytecode.")
        tx_hashes = self._filter_txs_from(
            from_block, to_block, contract_address
        )
        calls = self.get_calls(tx_hashes, contract_address)
        return self._filter_contract_calls(calls, to_block)
