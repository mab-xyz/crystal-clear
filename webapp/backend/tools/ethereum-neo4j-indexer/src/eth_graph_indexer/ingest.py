"""Ordered, resumable block ingestion orchestration."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import logging
import time
from dataclasses import dataclass
from typing import Protocol

from .address_filter import normalize_address
from .checkpoint import resolve_start_block
from .config import IndexerConfig
from .models import BlockData, InteractionEdge, hex_to_int
from .receipts import ReceiptLoader
from .rpc import JsonRpcClient
from .traces import TraceLoader

LOGGER = logging.getLogger(__name__)


class Store(Protocol):
    def ensure_schema(self) -> None: ...

    def verify_connectivity(self) -> None: ...

    def get_checkpoint(self, checkpoint_id: str): ...

    def write_block(
        self,
        *,
        edges: list[InteractionEdge],
        block_number: int,
        block_hash: str,
        checkpoint_id: str,
        batch_size: int,
    ) -> tuple[int, int]: ...


@dataclass(slots=True)
class IngestStats:
    blocks_processed: int = 0
    transactions_processed: int = 0
    nodes_upserted: int = 0
    relationships_upserted: int = 0
    started_at: float = 0.0

    def add(self, other: IngestStats) -> None:
        self.blocks_processed += other.blocks_processed
        self.transactions_processed += other.transactions_processed
        self.nodes_upserted += other.nodes_upserted
        self.relationships_upserted += other.relationships_upserted


@dataclass(frozen=True, slots=True)
class ProcessedBlock:
    block: BlockData
    edges: list[InteractionEdge]


def _safe_normalize(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return normalize_address(value)
    except ValueError:
        return None


def parse_external_interactions(
    block: BlockData, receipts: dict[str, dict]
) -> list[InteractionEdge]:
    edges: list[InteractionEdge] = []
    for tx in block.transactions:
        tx_hash = tx.get("hash")
        from_address = _safe_normalize(tx.get("from"))
        if not isinstance(tx_hash, str) or from_address is None:
            raise ValueError(
                f"block {block.number} contains a malformed transaction"
            )
        tx_hash = tx_hash.lower()
        to_raw = tx.get("to")
        if to_raw is None:
            receipt = receipts.get(tx_hash)
            if receipt is None:
                raise ValueError(
                    f"missing receipt for contract creation {tx_hash}"
                )
            to_address = _safe_normalize(receipt.get("contractAddress"))
            if to_address is None:
                # A failed creation has no resulting address and no graph edge.
                continue
            interaction_type = "contract_creation"
        else:
            to_address = _safe_normalize(to_raw)
            if to_address is None:
                raise ValueError(
                    f"transaction {tx_hash} has an invalid to address"
                )
            interaction_type = "external"
        edges.append(
            InteractionEdge(
                tx_hash=tx_hash,
                block_number=block.number,
                from_address=from_address,
                to_address=to_address,
                interaction_type=interaction_type,
                value_wei=str(hex_to_int(tx.get("value"))),
            )
        )
    return edges


def needs_receipts(block: BlockData) -> bool:
    return any(tx.get("to") is None for tx in block.transactions)


class Ingestor:
    def __init__(
        self,
        config: IndexerConfig,
        rpc: JsonRpcClient,
        store: Store,
        *,
        receipt_loader: ReceiptLoader | None = None,
        trace_loader: TraceLoader | None = None,
    ) -> None:
        self.config = config
        self.rpc = rpc
        self.store = store
        self.receipts = receipt_loader or ReceiptLoader(
            rpc, batch_size=config.receipt_batch_size
        )
        self.traces = trace_loader or TraceLoader(rpc, config.trace_mode)

    def run(self) -> IngestStats:
        self.store.verify_connectivity()
        self.store.ensure_schema()

        if not self.config.follow:
            return self._run_available_blocks()

        stats = IngestStats(started_at=time.monotonic())
        LOGGER.info(
            "Starting follow mode",
            extra={"poll_interval": self.config.poll_interval},
        )
        while True:
            stats.add(self._run_available_blocks())
            time.sleep(self.config.poll_interval)

    def _run_available_blocks(self) -> IngestStats:
        checkpoint = self.store.get_checkpoint(self.config.checkpoint_id)
        checkpoint_block = (
            checkpoint.last_processed_block if checkpoint is not None else None
        )
        start = resolve_start_block(
            self.config.start_block,
            checkpoint_block,
            resume=self.config.resume,
        )
        head = hex_to_int(self.rpc.call("eth_blockNumber"))
        end = (
            min(self.config.end_block, head)
            if self.config.end_block is not None
            else head
        )
        stats = IngestStats(started_at=time.monotonic())

        if start > end:
            LOGGER.info(
                "No blocks to process",
                extra={"start_block": start, "end_block": end, "head": head},
            )
            return stats

        LOGGER.info(
            "Starting ingestion",
            extra={"start_block": start, "end_block": end, "head": head},
        )
        with ThreadPoolExecutor(
            max_workers=self.config.concurrent_blocks
        ) as executor:
            futures: dict[int, Future[ProcessedBlock]] = {}
            next_to_submit = start

            def submit_available() -> None:
                nonlocal next_to_submit
                while (
                    next_to_submit <= end
                    and len(futures) < self.config.concurrent_blocks
                ):
                    futures[next_to_submit] = executor.submit(
                        self._process_block, next_to_submit
                    )
                    next_to_submit += 1

            submit_available()
            for block_number in range(start, end + 1):
                future = futures.pop(block_number)
                submit_available()
                self._commit_processed_block(
                    future,
                    block_number=block_number,
                    stats=stats,
                    head=head,
                    end=end,
                )
        return stats

    def _process_block(self, block_number: int) -> ProcessedBlock:
        block = self._get_block(block_number)
        receipts = (
            self.receipts.get_for_block(block.number, block.transactions)
            if needs_receipts(block)
            else {}
        )
        edges = parse_external_interactions(block, receipts)
        try:
            edges.extend(
                self.traces.get_for_block(block.number, block.transactions)
            )
        except Exception:
            LOGGER.exception(
                "Trace processing failed",
                extra={"block_number": block.number},
            )
            if not self.config.continue_on_trace_error:
                raise
        return ProcessedBlock(block, edges)

    def _commit_processed_block(
        self,
        future: Future[ProcessedBlock],
        *,
        block_number: int,
        stats: IngestStats,
        head: int,
        end: int,
    ) -> None:
        try:
            processed = future.result()
            block = processed.block
            nodes, relationships = self.store.write_block(
                edges=processed.edges,
                block_number=block.number,
                block_hash=block.block_hash,
                checkpoint_id=self.config.checkpoint_id,
                batch_size=self.config.batch_size,
            )
            stats.blocks_processed += 1
            stats.transactions_processed += len(block.transactions)
            stats.nodes_upserted += nodes
            stats.relationships_upserted += relationships
        except Exception:
            LOGGER.exception(
                "Block processing failed",
                extra={"block_number": block_number},
            )
            if not self.config.continue_on_error:
                raise
            # Deliberately checkpoint a skipped block so continue-on-error
            # can make progress. The gap is explicit in the error log.
            self.store.write_block(
                edges=[],
                block_number=block_number,
                block_hash="ERROR_SKIPPED",
                checkpoint_id=self.config.checkpoint_id,
                batch_size=self.config.batch_size,
            )

        if (
            stats.blocks_processed % self.config.progress_interval == 0
            or block_number == end
        ):
            self._log_progress(stats, block_number, head)

    def _get_block(self, block_number: int) -> BlockData:
        payload = self.rpc.call(
            "eth_getBlockByNumber", [hex(block_number), True]
        )
        if payload is None:
            raise ValueError(f"block {block_number} was not found")
        block = BlockData.from_rpc(payload)
        if block.number != block_number:
            raise ValueError(
                f"requested block {block_number}, received block {block.number}"
            )
        return block

    @staticmethod
    def _log_progress(
        stats: IngestStats, current_block: int, head: int
    ) -> None:
        elapsed = max(time.monotonic() - stats.started_at, 0.000001)
        LOGGER.info(
            "Ingestion progress",
            extra={
                "current_block": current_block,
                "head_block": head,
                "blocks_processed": stats.blocks_processed,
                "transactions_processed": stats.transactions_processed,
                "nodes_upserted": stats.nodes_upserted,
                "relationships_upserted": stats.relationships_upserted,
                "elapsed_seconds": round(elapsed, 2),
                "blocks_per_second": round(
                    stats.blocks_processed / elapsed, 3
                ),
            },
        )
