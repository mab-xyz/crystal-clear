"""Checkpoint resume policy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Checkpoint:
    last_processed_block: int
    last_processed_block_hash: str


def resolve_start_block(
    configured_start: int,
    checkpoint_last_processed: int | None,
    *,
    resume: bool,
) -> int:
    if (
        resume
        and checkpoint_last_processed is not None
        and checkpoint_last_processed >= configured_start
    ):
        return checkpoint_last_processed + 1
    return configured_start
