"""Pure helpers for backward scan and hole-filling — no app config dependency."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlmodel import Session, select

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.api.models.interaction_scan_backward_progress import InteractionScanBackwardProgress
from src.api.models.interaction_scan_skipped_range import InteractionScanSkippedRange
from src.api.models.interaction_scan_state import InteractionScanState


def resolve_scan_range_backward(
    effective_start: int,
    target_block: int,
    last_backward_block: Optional[int],
    chunk_size: int,
) -> Optional[tuple[int, int]]:
    """Return next (scan_start, scan_end) for the backward pass, or None when done."""
    if last_backward_block is not None and last_backward_block <= effective_start:
        return None
    scan_end = (last_backward_block - 1) if last_backward_block is not None else target_block
    if scan_end < effective_start:
        return None
    scan_start = max(effective_start, scan_end - chunk_size + 1)
    return scan_start, scan_end


def get_backward_progress(
    session: Session,
    from_address: str,
    to_address: str,
    interaction_type: str,
) -> Optional[int]:
    """Return last_backward_block for the pair, or None if not started."""
    rec = session.exec(
        select(InteractionScanBackwardProgress).where(
            InteractionScanBackwardProgress.from_address == from_address,
            InteractionScanBackwardProgress.to_address == to_address,
            InteractionScanBackwardProgress.interaction_type == interaction_type,
        )
    ).first()
    return rec.last_backward_block if rec else None


def upsert_backward_progress(
    session: Session,
    from_address: str,
    to_address: str,
    interaction_type: str,
    last_backward_block: int,
) -> None:
    rec = session.exec(
        select(InteractionScanBackwardProgress).where(
            InteractionScanBackwardProgress.from_address == from_address,
            InteractionScanBackwardProgress.to_address == to_address,
            InteractionScanBackwardProgress.interaction_type == interaction_type,
        )
    ).first()
    if rec is None:
        rec = InteractionScanBackwardProgress(
            from_address=from_address,
            to_address=to_address,
            interaction_type=interaction_type,
            last_backward_block=last_backward_block,
            updated_at=datetime.utcnow(),
        )
    else:
        rec.last_backward_block = last_backward_block
        rec.updated_at = datetime.utcnow()
    session.add(rec)


def fill_skipped_ranges_for_row(
    session: Session,
    scan_chunk_fn,
    w3,
    row: InteractionScanState,
    page_size: int,
    normalized_type: str,
    dry_run: bool,
) -> tuple[int, int]:
    """Retry recorded skipped ranges for a row. Returns (total_hits, ranges_filled)."""
    holes = session.exec(
        select(InteractionScanSkippedRange).where(
            InteractionScanSkippedRange.from_address == row.from_address,
            InteractionScanSkippedRange.to_address == row.to_address,
            InteractionScanSkippedRange.interaction_type == normalized_type,
        )
    ).all()
    if not holes:
        return 0, 0
    total_hits = 0
    filled = 0
    for hole in holes:
        hits, still_skipped = scan_chunk_fn(
            w3,
            row.from_address,
            row.to_address,
            hole.range_start,
            hole.range_end,
            page_size,
            normalized_type,
        )
        if not still_skipped:
            total_hits += hits
            filled += 1
            print(
                f"[fill-hole] id={row.id} type={normalized_type} "
                f"{row.from_address}->{row.to_address} "
                f"range={hole.range_start}-{hole.range_end} hits={hits}"
            )
            if not dry_run:
                session.delete(hole)
    if not dry_run and filled > 0:
        new_total = max(0, int(row.how_many_times)) + total_hits
        row.how_many_times = new_total
        row.first_time_interact = new_total == 0
        row.checked_at = datetime.utcnow()
        session.add(row)
        session.commit()
    return total_hits, filled
