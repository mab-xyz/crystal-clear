"""Report store behind the Ledger tiny URL: 8-char ids, rolling retention."""

from __future__ import annotations

import secrets
from base64 import urlsafe_b64encode
from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, delete
from sqlmodel import Session, col

from src.api.models.ledger_report import LedgerReport


def new_report_id() -> str:
    # 6 random bytes -> 8 base64url chars, no padding.
    return urlsafe_b64encode(secrets.token_bytes(6)).decode()


def tiny_url(base_url: str, report_id: str) -> str:
    return f"{base_url.rstrip('/')}/{report_id}"


def store_report(
    session: Session,
    *,
    family: str,
    kind: str,
    block: int | None,
    request_json: dict[str, Any],
    simulation_json: dict[str, Any],
    report_id: str | None = None,
) -> LedgerReport:
    report = LedgerReport(
        id=report_id or new_report_id(),
        family=family,
        kind=kind,
        block=block,
        request_json=request_json,
        simulation_json=simulation_json,
    )
    session.add(report)
    session.commit()
    return report


def get_report(
    session: Session, report_id: str, now: datetime | None = None
) -> LedgerReport | None:
    """Fetch and bump last_accessed_at (rolling window)."""
    report = session.get(LedgerReport, report_id)
    if report is not None:
        report.last_accessed_at = now or datetime.utcnow()
        session.add(report)
        session.commit()
    return report


def purge_expired(
    session: Session, retention_days: int, now: datetime | None = None
) -> int:
    cutoff = (now or datetime.utcnow()) - timedelta(days=retention_days)
    res = cast(CursorResult, session.execute(
        delete(LedgerReport).where(col(LedgerReport.last_accessed_at) < cutoff)
    ))
    session.commit()
    return res.rowcount or 0
