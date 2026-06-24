"""Tests for backward scanning and hole-filling logic in backfill_first_time_interactions_core."""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

# Import only the pure helpers and models — no Ethereum node needed.
from backfill_first_time_interactions_core import (  # noqa: E402
    _resolve_scan_range_backward,
    _get_backward_progress,
    _upsert_backward_progress,
    _fill_skipped_ranges_for_row,
    _scan_chunk,
)
from src.api.models.interaction_scan_backward_progress import (  # noqa: E402
    InteractionScanBackwardProgress,
)
from src.api.models.interaction_scan_skipped_range import InteractionScanSkippedRange  # noqa: E402
from src.api.models.interaction_scan_state import InteractionScanState  # noqa: E402

_ENGINE = create_engine("sqlite:///:memory:")


@pytest.fixture(autouse=True)
def _fresh_db():
    SQLModel.metadata.create_all(_ENGINE)
    yield
    SQLModel.metadata.drop_all(_ENGINE)


# ---------------------------------------------------------------------------
# _resolve_scan_range_backward — pure function, no DB
# ---------------------------------------------------------------------------

class TestResolveBackward:
    def test_fresh_row_starts_at_target(self):
        result = _resolve_scan_range_backward(
            effective_start=100, target_block=1000, last_backward_block=None, chunk_size=500
        )
        assert result == (501, 1000)

    def test_chunk_does_not_go_below_effective_start(self):
        result = _resolve_scan_range_backward(
            effective_start=100, target_block=1000, last_backward_block=None, chunk_size=2000
        )
        assert result == (100, 1000)

    def test_continues_from_last_backward_block(self):
        result = _resolve_scan_range_backward(
            effective_start=0, target_block=1000, last_backward_block=501, chunk_size=200
        )
        # scan_end = 501-1 = 500; scan_start = max(0, 500-200+1) = 301
        assert result == (301, 500)

    def test_final_chunk_clips_to_effective_start(self):
        result = _resolve_scan_range_backward(
            effective_start=450, target_block=1000, last_backward_block=501, chunk_size=200
        )
        assert result == (450, 500)

    def test_done_when_already_at_effective_start(self):
        result = _resolve_scan_range_backward(
            effective_start=100, target_block=1000, last_backward_block=100, chunk_size=500
        )
        assert result is None

    def test_done_when_below_effective_start(self):
        result = _resolve_scan_range_backward(
            effective_start=100, target_block=1000, last_backward_block=50, chunk_size=500
        )
        assert result is None

    def test_target_below_effective_start_returns_none(self):
        result = _resolve_scan_range_backward(
            effective_start=500, target_block=200, last_backward_block=None, chunk_size=100
        )
        assert result is None

    def test_single_block_range(self):
        result = _resolve_scan_range_backward(
            effective_start=5, target_block=5, last_backward_block=None, chunk_size=100
        )
        assert result == (5, 5)


# ---------------------------------------------------------------------------
# _get_backward_progress / _upsert_backward_progress — DB helpers
# ---------------------------------------------------------------------------

class TestBackwardProgressPersistence:
    def test_returns_none_when_no_record(self):
        with Session(_ENGINE) as session:
            result = _get_backward_progress(session, "0xaaa", "0xbbb", "contract_direct")
        assert result is None

    def test_upsert_creates_and_retrieves(self):
        with Session(_ENGINE) as session:
            _upsert_backward_progress(session, "0xaaa", "0xbbb", "contract_direct", 12345)
            session.commit()
            result = _get_backward_progress(session, "0xaaa", "0xbbb", "contract_direct")
        assert result == 12345

    def test_upsert_updates_existing(self):
        with Session(_ENGINE) as session:
            _upsert_backward_progress(session, "0xaaa", "0xbbb", "contract_direct", 12345)
            session.commit()
            _upsert_backward_progress(session, "0xaaa", "0xbbb", "contract_direct", 9000)
            session.commit()
            result = _get_backward_progress(session, "0xaaa", "0xbbb", "contract_direct")
        assert result == 9000

    def test_different_types_are_independent(self):
        with Session(_ENGINE) as session:
            _upsert_backward_progress(session, "0xaaa", "0xbbb", "contract_direct", 100)
            _upsert_backward_progress(session, "0xaaa", "0xbbb", "sender_direct", 200)
            session.commit()
            assert _get_backward_progress(session, "0xaaa", "0xbbb", "contract_direct") == 100
            assert _get_backward_progress(session, "0xaaa", "0xbbb", "sender_direct") == 200


# ---------------------------------------------------------------------------
# _fill_skipped_ranges_for_row
# ---------------------------------------------------------------------------

def _make_scan_state(session: Session, from_addr: str, to_addr: str, itype: str) -> InteractionScanState:
    row = InteractionScanState(
        from_address=from_addr,
        to_address=to_addr,
        interaction_type=itype,
        from_block=0,
        last_analyzed_block=None,
        how_many_times=0,
        first_time_interact=True,
        needs_creation_retry=False,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _make_hole(
    session: Session, from_addr: str, to_addr: str, itype: str, start: int, end: int
) -> InteractionScanSkippedRange:
    hole = InteractionScanSkippedRange(
        from_address=from_addr,
        to_address=to_addr,
        interaction_type=itype,
        range_start=start,
        range_end=end,
        reason="scan_error",
    )
    session.add(hole)
    session.commit()
    return hole


class TestFillSkippedRanges:
    def test_no_holes_returns_zero(self):
        with Session(_ENGINE) as session:
            row = _make_scan_state(session, "0xaaa", "0xbbb", "contract_direct")
            mock_w3 = MagicMock()
            hits, filled = _fill_skipped_ranges_for_row(
                session, mock_w3, row, 50, "contract_direct", dry_run=False
            )
        assert hits == 0
        assert filled == 0

    def test_successful_retry_removes_hole_and_counts_hits(self, monkeypatch):
        def fake_scan_chunk(w3, from_addr, to_addr, scan_start, scan_end, page_size, ntype):
            return 3, []  # 3 hits, no skipped ranges

        monkeypatch.setattr(
            "backfill_first_time_interactions_core._scan_chunk", fake_scan_chunk
        )
        with Session(_ENGINE) as session:
            row = _make_scan_state(session, "0xaaa", "0xbbb", "contract_direct")
            _make_hole(session, "0xaaa", "0xbbb", "contract_direct", 1000, 2000)

            mock_w3 = MagicMock()
            hits, filled = _fill_skipped_ranges_for_row(
                session, mock_w3, row, 50, "contract_direct", dry_run=False
            )

            remaining = session.exec(
                select(InteractionScanSkippedRange).where(
                    InteractionScanSkippedRange.from_address == "0xaaa"
                )
            ).all()

        assert hits == 3
        assert filled == 1
        assert len(remaining) == 0

    def test_still_failing_hole_stays_recorded(self, monkeypatch):
        def fake_scan_chunk(w3, from_addr, to_addr, scan_start, scan_end, page_size, ntype):
            return 0, [(scan_start, scan_end)]  # still fails

        monkeypatch.setattr(
            "backfill_first_time_interactions_core._scan_chunk", fake_scan_chunk
        )
        with Session(_ENGINE) as session:
            row = _make_scan_state(session, "0xaaa", "0xbbb", "contract_direct")
            _make_hole(session, "0xaaa", "0xbbb", "contract_direct", 1000, 2000)

            mock_w3 = MagicMock()
            hits, filled = _fill_skipped_ranges_for_row(
                session, mock_w3, row, 50, "contract_direct", dry_run=False
            )

            remaining = session.exec(
                select(InteractionScanSkippedRange).where(
                    InteractionScanSkippedRange.from_address == "0xaaa"
                )
            ).all()

        assert hits == 0
        assert filled == 0
        assert len(remaining) == 1

    def test_dry_run_does_not_delete_hole(self, monkeypatch):
        def fake_scan_chunk(w3, from_addr, to_addr, scan_start, scan_end, page_size, ntype):
            return 5, []

        monkeypatch.setattr(
            "backfill_first_time_interactions_core._scan_chunk", fake_scan_chunk
        )
        with Session(_ENGINE) as session:
            row = _make_scan_state(session, "0xaaa", "0xbbb", "contract_direct")
            _make_hole(session, "0xaaa", "0xbbb", "contract_direct", 1000, 2000)

            mock_w3 = MagicMock()
            hits, filled = _fill_skipped_ranges_for_row(
                session, mock_w3, row, 50, "contract_direct", dry_run=True
            )

            remaining = session.exec(
                select(InteractionScanSkippedRange).where(
                    InteractionScanSkippedRange.from_address == "0xaaa"
                )
            ).all()

        assert hits == 5
        assert filled == 1
        assert len(remaining) == 1  # hole preserved in dry-run

    def test_successful_retry_updates_how_many_times(self, monkeypatch):
        def fake_scan_chunk(w3, from_addr, to_addr, scan_start, scan_end, page_size, ntype):
            return 7, []

        monkeypatch.setattr(
            "backfill_first_time_interactions_core._scan_chunk", fake_scan_chunk
        )
        with Session(_ENGINE) as session:
            row = _make_scan_state(session, "0xaaa", "0xbbb", "contract_direct")
            row.how_many_times = 2
            session.add(row)
            session.commit()
            _make_hole(session, "0xaaa", "0xbbb", "contract_direct", 1000, 2000)

            mock_w3 = MagicMock()
            _fill_skipped_ranges_for_row(
                session, mock_w3, row, 50, "contract_direct", dry_run=False
            )
            session.refresh(row)

        assert row.how_many_times == 9  # 2 existing + 7 from hole
