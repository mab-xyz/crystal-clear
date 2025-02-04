from typing import List, Dict, Any, Set
from web3 import Web3

class TraceCollector:
    def __init__(self, url: str):
        self.w3 = Web3(Web3.HTTPProvider(url))
        assert self.w3.is_connected()
    
    def _filter_txs_from(self, from_block: int, to_block: int, contract_address: str) -> Set[str]:
        filter_params = {
            "fromBlock": from_block,
            "toBlock": to_block,
            "fromAddress": [contract_address]
        }
        res = self.w3.tracing.trace_filter(filter_params)

        if res is None:
            return set()
        tx_hashes = set()
        for r in res:
            if r['type'] == 'call':
                tx_hashes.add(r['transactionHash'])
        return tx_hashes
    
    def _get_calls_from_tx(self, tx_hash: str) -> Dict[str, Any]:
        res = self.w3.geth.debug.trace_transaction(tx_hash, {"tracer": "callTracer"})
        return res
    
    def _extract_all_subcalls(self, call: Dict[str, Any], calls: List[Dict[str, str]]) -> None:
        calls.append({
                'from': call['from'],
                'to': call['to'],
                'type': call['type']
        })
        if 'calls' in call:
            for subcall in call['calls']:
                self._extract_all_subcalls(subcall, calls)

    def _extract_calls(self, call: Dict[str, Any], contract_address: str, calls: List[Dict[str, str]]) -> None:
        if call['from'].lower() == contract_address.lower():
            calls.append({
                'from': call['from'],
                'to': call['to'],
                'type': call['type']
            })
            if 'calls' in call:
                for subcall in call['calls']:
                    self._extract_all_subcalls(subcall, calls)
        if 'calls' in call:
            for subcall in call['calls']:
                self._extract_calls(subcall, contract_address, calls)

    def get_calls(self, tx_hashes: Set[str], contract_address: str) -> List[Dict[str, str]]:
        calls = []
        for h in tx_hashes:
            res = self._get_calls_from_tx(h)
            self._extract_calls(res, contract_address, calls)
        return calls

    def get_calls_from(self, from_block: int, to_block: int, contract_address: str) -> List[Dict[str, str]]:
        tx_hashes = self._filter_txs_from(from_block, to_block, contract_address)
        return self.get_calls(tx_hashes, contract_address)