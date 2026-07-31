"""Configuration and command-line value validation."""

from __future__ import annotations

from dataclasses import dataclass

TRACE_MODES = {"none", "trace_block", "debug_traceBlockByNumber"}
POST_MERGE_START_BLOCK = 15_537_394


def parse_rpc_urls(value: str) -> tuple[str, ...]:
    urls = tuple(url.strip() for url in value.split(",") if url.strip())
    if not urls:
        raise ValueError("at least one RPC URL is required")
    return urls


def parse_endpoint_concurrency(
    value: str | None,
) -> tuple[int, ...] | None:
    if value is None:
        return None
    counts = tuple(
        int(item.strip()) for item in value.split(",") if item.strip()
    )
    if not counts:
        raise ValueError("at least one endpoint concurrency value is required")
    if any(count < 1 for count in counts):
        raise ValueError("endpoint concurrency values must be positive")
    return counts


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"expected a boolean value, got {value!r}")


@dataclass(frozen=True, slots=True)
class IndexerConfig:
    rpc_url: str
    postgres_dsn: str
    endpoint_concurrency: tuple[int, ...] | None = None
    start_block: int = POST_MERGE_START_BLOCK
    end_block: int | None = None
    batch_size: int = 1000
    receipt_batch_size: int = 100
    commit_batch_size: int = 10
    concurrent_blocks: int = 4
    trace_mode: str = "trace_block"
    resume: bool = True
    continue_on_error: bool = False
    continue_on_trace_error: bool = False
    follow: bool = False
    poll_interval: float = 12.0
    request_timeout: float = 60.0
    max_retries: int = 4
    retry_backoff: float = 0.5
    progress_interval: int = 10
    checkpoint_id: str = "default"

    def __post_init__(self) -> None:
        rpc_urls = parse_rpc_urls(self.rpc_url)
        if not self.postgres_dsn.strip():
            raise ValueError("PostgreSQL DSN is required")
        if self.start_block < 0:
            raise ValueError("start block must be non-negative")
        if self.end_block is not None and self.end_block < self.start_block:
            raise ValueError("end block must be greater than or equal to start block")
        if self.follow and self.end_block is not None:
            raise ValueError("follow mode cannot be used with end block")
        if (
            self.batch_size < 1
            or self.receipt_batch_size < 1
            or self.commit_batch_size < 1
        ):
            raise ValueError("batch sizes must be positive")
        if self.concurrent_blocks < 1:
            raise ValueError("concurrent blocks must be positive")
        if self.endpoint_concurrency is not None:
            if len(self.endpoint_concurrency) != len(rpc_urls):
                raise ValueError(
                    "endpoint concurrency count must match the number of RPC URLs"
                )
            if sum(self.endpoint_concurrency) != self.concurrent_blocks:
                raise ValueError(
                    "endpoint concurrency must sum to concurrent blocks"
                )
        if self.trace_mode not in TRACE_MODES:
            choices = ", ".join(sorted(TRACE_MODES))
            raise ValueError(f"trace mode must be one of: {choices}")
        if self.request_timeout <= 0:
            raise ValueError("request timeout must be positive")
        if self.poll_interval <= 0:
            raise ValueError("poll interval must be positive")
        if self.max_retries < 0:
            raise ValueError("max retries must be non-negative")
        if self.progress_interval < 1:
            raise ValueError("progress interval must be positive")
