"""Report store behind the Ledger tiny URL: 8-char ids, rolling retention."""

from __future__ import annotations

import secrets
from base64 import urlsafe_b64encode
from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, delete
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col

from src.api.models.ledger_report import LedgerReport


def new_report_id() -> str:
    # 5 random bytes -> 7 base64url chars (no padding): keeps
    # https://api2.mab.xyz/r/<id> within Ledger's 30-char tiny-URL limit.
    return urlsafe_b64encode(secrets.token_bytes(5)).decode()


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
    for _ in range(5):
        report = LedgerReport(
            id=report_id or new_report_id(),
            family=family,
            kind=kind,
            block=block,
            request_json=request_json,
            simulation_json=simulation_json,
        )
        session.add(report)
        try:
            session.commit()
            return report
        except IntegrityError:
            session.rollback()
            if report_id:
                raise
    raise RuntimeError("could not allocate a unique report id")


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
