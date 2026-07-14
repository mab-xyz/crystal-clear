"""Ordered, resumable block ingestion orchestration."""

from __future__ import annotations

import logging
import time
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol

from .address_filter import normalize_address
from .checkpoint import resolve_start_block
from .config import IndexerConfig
from .models import BlockData, BlockWrite, InteractionEdge, hex_to_int
from .receipts import ReceiptLoader
from .rpc import RpcClient
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

    def write_blocks(
        self,
        blocks: list[BlockWrite],
        *,
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
    rpc_block_seconds: float = 0.0
    receipt_seconds: float = 0.0
    trace_seconds: float = 0.0
    neo4j_write_seconds: float = 0.0

    def add(self, other: IngestStats) -> None:
        self.blocks_processed += other.blocks_processed
        self.transactions_processed += other.transactions_processed
        self.nodes_upserted += other.nodes_upserted
        self.relationships_upserted += other.relationships_upserted
        self.rpc_block_seconds += other.rpc_block_seconds
        self.receipt_seconds += other.receipt_seconds
        self.trace_seconds += other.trace_seconds
        self.neo4j_write_seconds += other.neo4j_write_seconds


@dataclass(frozen=True, slots=True)
class ProcessedBlock:
    block: BlockData
    edges: list[InteractionEdge]
    rpc_block_seconds: float = 0.0
    receipt_seconds: float = 0.0
    trace_seconds: float = 0.0
    skipped: bool = False


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
        rpc: RpcClient,
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
        self._custom_receipt_loader = receipt_loader
        self._custom_trace_loader = trace_loader

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
        with _EndpointExecutors(
            self._build_endpoint_worker_groups()
        ) as executors:
            futures: dict[int, tuple[Future[ProcessedBlock], int]] = {}
            next_to_submit = start
            commit_batch: list[ProcessedBlock] = []

            def submit_available() -> None:
                nonlocal next_to_submit
                while (
                    next_to_submit <= end
                    and len(futures) < executors.total_capacity
                ):
                    endpoint_index = executors.next_available_index()
                    if endpoint_index is None:
                        return
                    endpoint_rpc = executors.endpoint_rpc(endpoint_index)
                    future = executors.submit(
                        endpoint_index,
                        self._process_block,
                        next_to_submit,
                        endpoint_rpc,
                    )
                    futures[next_to_submit] = (future, endpoint_index)
                    next_to_submit += 1

            submit_available()
            for block_number in range(start, end + 1):
                future, endpoint_index = futures.pop(block_number)
                executors.mark_completed(endpoint_index)
                submit_available()
                processed = self._resolve_processed_block(
                    future,
                    block_number=block_number,
                )
                commit_batch.append(processed)
                if (
                    len(commit_batch) >= self.config.commit_batch_size
                    or block_number == end
                ):
                    self._commit_processed_blocks(
                        commit_batch,
                        stats=stats,
                        head=head,
                        end=end,
                    )
                    commit_batch = []
        return stats

    def _process_block(
        self, block_number: int, rpc: RpcClient | None = None
    ) -> ProcessedBlock:
        rpc_client = rpc or self.rpc
        block_start = time.monotonic()
        block = self._get_block(block_number, rpc_client)
        block_end = time.monotonic()
        receipt_start = time.monotonic()
        receipt_loader = self._receipt_loader_for(rpc_client)
        receipts = (
            receipt_loader.get_for_block(block.number, block.transactions)
            if needs_receipts(block)
            else {}
        )
        receipt_end = time.monotonic()
        edges = parse_external_interactions(block, receipts)
        trace_start = time.monotonic()
        trace_loader = self._trace_loader_for(rpc_client)
        try:
            edges.extend(trace_loader.get_for_block(block.number, block.transactions))
        except Exception:
            LOGGER.exception(
                "Trace processing failed",
                extra={"block_number": block.number},
            )
            if not self.config.continue_on_trace_error:
                raise
        trace_end = time.monotonic()
        return ProcessedBlock(
            block,
            edges,
            rpc_block_seconds=block_end - block_start,
            receipt_seconds=receipt_end - receipt_start,
            trace_seconds=trace_end - trace_start,
        )

    def _resolve_processed_block(
        self,
        future: Future[ProcessedBlock],
        *,
        block_number: int,
    ) -> ProcessedBlock:
        try:
            return future.result()
        except Exception:
            LOGGER.exception(
                "Block processing failed",
                extra={"block_number": block_number},
            )
            if not self.config.continue_on_error:
                raise
            # Deliberately checkpoint a skipped block so continue-on-error
            # can make progress. The gap is explicit in the error log.
            return ProcessedBlock(
                BlockData(block_number, "ERROR_SKIPPED", ()),
                [],
                skipped=True,
            )

    def _commit_processed_blocks(
        self,
        blocks: list[ProcessedBlock],
        *,
        stats: IngestStats,
        head: int,
        end: int,
    ) -> None:
        write_start = time.monotonic()
        nodes, relationships = self.store.write_blocks(
            [
                BlockWrite(
                    edges=processed.edges,
                    block_number=processed.block.number,
                    block_hash=processed.block.block_hash,
                )
                for processed in blocks
            ],
            checkpoint_id=self.config.checkpoint_id,
            batch_size=self.config.batch_size,
        )
        write_end = time.monotonic()
        stats.neo4j_write_seconds += write_end - write_start
        stats.nodes_upserted += nodes
        stats.relationships_upserted += relationships
        for processed in blocks:
            if processed.skipped:
                continue
            stats.blocks_processed += 1
            stats.transactions_processed += len(processed.block.transactions)
            stats.rpc_block_seconds += processed.rpc_block_seconds
            stats.receipt_seconds += processed.receipt_seconds
            stats.trace_seconds += processed.trace_seconds

        current_block = blocks[-1].block.number
        if (
            stats.blocks_processed % self.config.progress_interval == 0
            or current_block == end
        ):
            self._log_progress(stats, current_block, head)

    def _get_block(self, block_number: int, rpc: RpcClient) -> BlockData:
        payload = rpc.call(
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

    def _build_endpoint_worker_groups(self) -> list[tuple[RpcClient, int]]:
        if (
            self.config.endpoint_concurrency is not None
            and hasattr(self.rpc, "clients")
        ):
            clients = tuple(self.rpc.clients)
            if len(clients) != len(self.config.endpoint_concurrency):
                raise ValueError(
                    "endpoint concurrency does not match RPC client count"
                )
            return list(
                zip(clients, self.config.endpoint_concurrency, strict=True)
            )
        return [(self.rpc, self.config.concurrent_blocks)]

    def _receipt_loader_for(self, rpc: RpcClient):
        if rpc is self.rpc or self._custom_receipt_loader is not None:
            return self.receipts
        return ReceiptLoader(rpc, batch_size=self.config.receipt_batch_size)

    def _trace_loader_for(self, rpc: RpcClient):
        if rpc is self.rpc or self._custom_trace_loader is not None:
            return self.traces
        return TraceLoader(rpc, self.config.trace_mode)

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
                "rpc_block_seconds": round(stats.rpc_block_seconds, 3),
                "receipt_seconds": round(stats.receipt_seconds, 3),
                "trace_seconds": round(stats.trace_seconds, 3),
                "neo4j_write_seconds": round(stats.neo4j_write_seconds, 3),
            },
        )


class _EndpointExecutors:
    def __init__(self, groups: list[tuple[RpcClient, int]]) -> None:
        self._groups = groups
        self._executors: list[Executor] = []
        self._inflight: list[int] = [0 for _ in groups]
        self._next_index = 0

    @property
    def total_capacity(self) -> int:
        return sum(capacity for _rpc, capacity in self._groups)

    def __enter__(self) -> _EndpointExecutors:
        self._executors = [
            ThreadPoolExecutor(max_workers=capacity)
            for _rpc, capacity in self._groups
        ]
        return self

    def __exit__(self, *_args: object) -> None:
        for executor in self._executors:
            executor.shutdown(wait=True)

    def endpoint_rpc(self, index: int) -> RpcClient:
        return self._groups[index][0]

    def next_available_index(self) -> int | None:
        for offset in range(len(self._groups)):
            index = (self._next_index + offset) % len(self._groups)
            if self._inflight[index] < self._groups[index][1]:
                self._inflight[index] += 1
                self._next_index = (index + 1) % len(self._groups)
                return index
        return None

    def submit(
        self,
        index: int,
        fn,
        *args: object,
    ) -> Future[ProcessedBlock]:
        return self._executors[index].submit(fn, *args)

    def mark_completed(self, index: int) -> None:
        self._inflight[index] -= 1
