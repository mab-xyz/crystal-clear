"""Block receipt retrieval."""

from __future__ import annotations

import logging
from collections.abc import Mapping

from .rpc import JsonRpcError, RpcCall, RpcClient

LOGGER = logging.getLogger(__name__)


class ReceiptLoader:
    def __init__(
        self, rpc: RpcClient, *, batch_size: int = 100
    ) -> None:
        self.rpc = rpc
        self.batch_size = batch_size
        self._block_receipts_supported: bool | None = None

    def get_for_block(
        self, block_number: int, transactions: tuple[dict, ...]
    ) -> dict[str, dict]:
        if self._block_receipts_supported is not False:
            try:
                receipts = self.rpc.call(
                    "eth_getBlockReceipts", [hex(block_number)]
                )
                if not isinstance(receipts, list):
                    raise ValueError("eth_getBlockReceipts did not return a list")
                self._block_receipts_supported = True
                return self._index(receipts)
            except JsonRpcError as exc:
                if exc.code not in {-32601, -32004}:
                    raise
                self._block_receipts_supported = False
                LOGGER.info(
                    "eth_getBlockReceipts unavailable; using receipt batches"
                )

        hashes = [tx.get("hash") for tx in transactions]
        if any(not isinstance(tx_hash, str) for tx_hash in hashes):
            raise ValueError(
                f"block {block_number} contains a transaction without a hash"
            )

        receipts: list[dict] = []
        for offset in range(0, len(hashes), self.batch_size):
            chunk = hashes[offset : offset + self.batch_size]
            responses = self.rpc.batch_call(
                RpcCall("eth_getTransactionReceipt", [tx_hash])
                for tx_hash in chunk
            )
            receipts.extend(responses)
        return self._index(receipts)

    @staticmethod
    def _index(receipts: list) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for receipt in receipts:
            if not isinstance(receipt, Mapping):
                raise ValueError("receipt response contains a non-object value")
            tx_hash = receipt.get("transactionHash")
            if not isinstance(tx_hash, str):
                raise ValueError("receipt response is missing transactionHash")
            result[tx_hash.lower()] = dict(receipt)
        return result
