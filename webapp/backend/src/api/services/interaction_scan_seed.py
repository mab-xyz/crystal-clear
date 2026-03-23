from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from src.api.models.interaction_scan_state import InteractionScanState


def _normalize_address(address: str | None) -> Optional[str]:
    if not address:
        return None
    value = address.strip().lower()
    if not value.startswith("0x"):
        return None
    return value


def _candidate_rows(
    sender_address: str,
    root_contract: str | None,
    touched_addresses: set[str],
) -> set[tuple[str, str, str]]:
    rows: set[tuple[str, str, str]] = set()

    sender_norm = _normalize_address(sender_address)
    root_norm = _normalize_address(root_contract)
    if not sender_norm:
        return rows

    for target in touched_addresses:
        if sender_norm == target:
            continue
        rows.add((sender_norm, target, "sender_direct"))
        rows.add((sender_norm, target, "sender_transitive"))

    if not root_norm:
        return rows

    for target in touched_addresses:
        if root_norm == target:
            continue
        rows.add((root_norm, target, "contract_direct"))
        rows.add((root_norm, target, "contract_transitive"))

    return rows


def seed_interaction_scan_state_from_tx(
    session: Session,
    sender_address: str,
    root_contract: str | None,
    touched_addresses: Iterable[str],
) -> int:
    """
    Insert missing interaction scan rows for addresses observed in a tx-risk run.

    This seeds the scan queue only; heavy historical counting is left to the
    backfill worker script.
    """

    normalized_targets = {
        addr for addr in (_normalize_address(x) for x in touched_addresses) if addr
    }
    candidates = _candidate_rows(sender_address, root_contract, normalized_targets)
    if not candidates:
        return 0

    now = datetime.utcnow()
    inserted = 0
    for from_address, to_address, interaction_type in candidates:
        existing = session.exec(
            select(InteractionScanState).where(
                InteractionScanState.from_address == from_address,
                InteractionScanState.to_address == to_address,
                InteractionScanState.interaction_type == interaction_type,
            )
        ).first()
        if existing:
            existing.last_requested_at = now
            session.add(existing)
            continue

        session.add(
            InteractionScanState(
                from_address=from_address,
                to_address=to_address,
                interaction_type=interaction_type,
                from_block=0,
                last_analyzed_block=None,
                how_many_times=0,
                first_time_interact=True,
                needs_creation_retry=False,
                last_requested_at=now,
            )
        )
        inserted += 1

    session.commit()
    return inserted

