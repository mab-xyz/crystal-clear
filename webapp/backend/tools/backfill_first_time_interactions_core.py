#!/usr/bin/env python3
"""Incremental backfill for interaction scan state."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import time

import requests
from sqlmodel import SQLModel, Session, select
from web3 import Web3


ROOT = Path(__file__).resolve().parents[1]
MAX_TRACE_PAGES_PER_CALL = 2_000
DIRECT_INTERACTION_TYPES = {"contract_direct", "sender_direct"}
TRANSITIVE_INTERACTION_TYPES = {"contract_transitive", "sender_transitive"}
DEBUG_LOG_ENABLED = os.getenv("LOG_LEVEL", "").strip().upper() == "DEBUG"


def _load_env() -> None:
    """Populate os.environ with values from backend .env file (if present)."""

    candidates = [ROOT / ".env", ROOT / "api" / ".env"]
    for env_path in candidates:
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
        break


_load_env()

API_ROOT = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from crystal_clear.traces.trace_collector import TraceCollector

from src.api.clients.allium_client import AlliumClient
from src.api.core.config import settings
from src.api.core.database import engine
from src.api.crud import deployment as deployment_crud
from src.api.models.address_metadata import AddressMetadata
from src.api.models.deployment import Deployment, DeploymentCreate
from src.api.models.first_interaction import FirstInteraction
from src.api.models.interaction_scan_hot import InteractionScanHot
from src.api.models.interaction_scan_state import InteractionScanState
import backfill_interaction_checks as interaction_checks


def _normalize_address(address: str | None) -> Optional[str]:
    if not address:
        return None
    addr = address.strip().lower()
    return addr if addr.startswith("0x") else None


def _to_hex_block(value: int) -> str:
    return hex(max(0, int(value)))


def _trace_filter(w3: Web3, params: dict, label: str):
    if DEBUG_LOG_ENABLED:
        print(f"[trace-filter] mode={label} params={params}")
    return w3.tracing.trace_filter(params)


def _ensure_state_table() -> None:
    SQLModel.metadata.create_all(
        engine,
        tables=[
            InteractionScanState.__table__,
            AddressMetadata.__table__,
            InteractionScanHot.__table__,
        ],
    )


def _seed_scan_rows_from_first_time(
    session: Session,
    interaction_type: str,
    limit: Optional[int],
) -> int:
    inserted = 0
    seen: set[tuple[str, str]] = set()
    stmt = select(FirstInteraction)
    rows = session.exec(stmt)
    for row in rows:
        if limit and inserted >= limit:
            break
        from_addr = _normalize_address(row.from_address)
        to_addr = _normalize_address(row.to_address)
        if not from_addr or not to_addr:
            continue
        pair = (from_addr, to_addr)
        if pair in seen:
            continue
        seen.add(pair)

        existing = session.exec(
            select(InteractionScanState).where(
                InteractionScanState.from_address == from_addr,
                InteractionScanState.to_address == to_addr,
                InteractionScanState.interaction_type == interaction_type,
            )
        ).first()
        if existing:
            continue

        session.add(
            InteractionScanState(
                from_address=from_addr,
                to_address=to_addr,
                interaction_type=interaction_type,
                from_block=0,
                last_analyzed_block=None,
                how_many_times=0,
                first_time_interact=True,
                needs_creation_retry=False,
            )
        )
        inserted += 1

    if inserted > 0:
        session.commit()
    return inserted


def _iter_scan_rows(
    session: Session,
    interaction_types: list[str],
    only_retry: bool,
    from_filter: Optional[str],
    to_filter: Optional[str],
):
    stmt = select(InteractionScanState)
    if interaction_types:
        stmt = stmt.where(
            InteractionScanState.interaction_type.in_(interaction_types)
        )
    if only_retry:
        stmt = stmt.where(InteractionScanState.needs_creation_retry.is_(True))
    if from_filter:
        stmt = stmt.where(InteractionScanState.from_address == from_filter)
    if to_filter:
        stmt = stmt.where(InteractionScanState.to_address == to_filter)
    stmt = stmt.order_by(InteractionScanState.id)
    for row in session.exec(stmt):
        yield row


def _has_code_at_block(
    w3: Web3, checksum_address: str, block_number: int
) -> bool:
    try:
        code = w3.eth.get_code(checksum_address, block_identifier=block_number)
    except Exception:
        return False
    return bool(code and len(code) > 0)


def _find_creation_block_by_code(w3: Web3, address: str) -> Optional[int]:
    try:
        checksum = Web3.to_checksum_address(address)
        latest = int(w3.eth.block_number)
    except Exception:
        return None

    if latest < 0 or not _has_code_at_block(w3, checksum, latest):
        return None

    low = 0
    high = latest
    while low < high:
        mid = (low + high) // 2
        if _has_code_at_block(w3, checksum, mid):
            high = mid
        else:
            low = mid + 1
    return low


def _upsert_address_metadata(
    session: Session,
    address: str,
    *,
    address_type: str,
    creation_block: Optional[int] = None,
    first_tx_block: Optional[int] = None,
    source: Optional[str] = None,
    needs_retry: bool = False,
) -> None:
    normalized = _normalize_address(address)
    if not normalized:
        return
    record = session.get(AddressMetadata, normalized)
    if record is None:
        record = AddressMetadata(
            address=normalized,
            address_type=address_type,
            creation_block=creation_block,
            first_tx_block=first_tx_block,
            source=source,
            needs_retry=needs_retry,
            checked_at=datetime.utcnow(),
        )
    else:
        record.address_type = address_type or record.address_type
        if creation_block is not None:
            record.creation_block = int(creation_block)
        if first_tx_block is not None:
            record.first_tx_block = int(first_tx_block)
        if source:
            record.source = source
        record.needs_retry = bool(needs_retry)
        record.checked_at = datetime.utcnow()
    session.add(record)


def _resolve_creation_block(
    session: Session,
    w3: Web3,
    address: str,
    allium_client: Optional[AlliumClient],
    cache: dict[str, int],
    persist_deployment: bool = True,
) -> tuple[int, bool, str]:
    normalized = _normalize_address(address)
    if not normalized:
        return 0, True, "invalid"

    if normalized in cache:
        return cache[normalized], cache[normalized] == 0, "cache"

    metadata = session.get(AddressMetadata, normalized)
    if (
        metadata
        and metadata.address_type == "contract"
        and isinstance(metadata.creation_block, int)
        and metadata.creation_block >= 0
    ):
        block = int(metadata.creation_block)
        cache[normalized] = block
        return (
            block,
            bool(metadata.needs_retry),
            metadata.source or "address_metadata",
        )

    record = session.get(Deployment, normalized)
    if (
        record
        and isinstance(record.block_number, int)
        and record.block_number >= 0
    ):
        block = int(record.block_number)
        _upsert_address_metadata(
            session,
            normalized,
            address_type="contract",
            creation_block=block,
            source="deployment",
            needs_retry=False,
        )
        cache[normalized] = block
        return block, False, "deployment"

    if allium_client:
        data = allium_client.get_deployment(normalized)
        if data:
            try:
                block = int(data.get("block_number"))
            except (TypeError, ValueError):
                block = None
            if block is not None and block >= 0:
                entry = DeploymentCreate(
                    address=data.get("address", normalized).lower(),
                    deployer=data.get("deployer", ""),
                    deployer_eoa=data.get("deployer_eoa", ""),
                    tx_hash=data.get("transaction_hash", ""),
                    block_number=block,
                )
                if persist_deployment:
                    try:
                        deployment_crud.create_deployment(session, entry)
                    except Exception:
                        session.rollback()
                _upsert_address_metadata(
                    session,
                    normalized,
                    address_type="contract",
                    creation_block=block,
                    source="allium",
                    needs_retry=False,
                )
                cache[normalized] = block
                return block, False, "allium"

    block = _find_creation_block_by_code(w3, normalized)
    if block is not None:
        _upsert_address_metadata(
            session,
            normalized,
            address_type="contract",
            creation_block=block,
            source="rpc_binary",
            needs_retry=False,
        )
        cache[normalized] = block
        return block, False, "rpc_binary"

    _upsert_address_metadata(
        session,
        normalized,
        address_type=(metadata.address_type if metadata else "unknown"),
        source="unknown",
        needs_retry=True,
    )
    cache[normalized] = 0
    return 0, True, "unknown"


def _has_sender_activity_in_range(
    w3: Web3,
    sender_address: str,
    start_block: int,
    end_block: int,
) -> bool:
    if start_block > end_block:
        return False
    try:
        sender_checksum = Web3.to_checksum_address(sender_address)
    except Exception:
        return False

    params = {
        "fromBlock": _to_hex_block(start_block),
        "toBlock": _to_hex_block(end_block),
        "fromAddress": [sender_checksum],
        "count": 1,
        "after": 0,
    }
    try:
        traces = _trace_filter(w3, params, "sender_activity")
    except Exception:
        return False
    if not isinstance(traces, list) or not traces:
        return False
    for trace in traces:
        if _is_allowed_trace_type(trace):
            return True
    return False


def _find_first_sender_tx_block(
    w3: Web3, sender_address: str
) -> Optional[int]:
    try:
        latest = int(w3.eth.block_number)
    except Exception:
        return None
    if latest < 0:
        return None
    if not _has_sender_activity_in_range(w3, sender_address, 0, latest):
        return None

    low = 0
    high = latest
    while low < high:
        mid = (low + high) // 2
        if _has_sender_activity_in_range(w3, sender_address, 0, mid):
            high = mid
        else:
            low = mid + 1
    return low


def _find_first_sender_tx_block_etherscan(
    sender_address: str,
    etherscan_api_key: str | None,
) -> Optional[int]:
    if not etherscan_api_key:
        if DEBUG_LOG_ENABLED:
            print("[etherscan] skip: missing api key")
        return None

    normalized = _normalize_address(sender_address)
    if not normalized:
        if DEBUG_LOG_ENABLED:
            print(f"[etherscan] skip: invalid address sender={sender_address}")
        return None

    params = {
        "module": "account",
        "action": "txlist",
        "chainid": 1,
        "address": normalized,
        "page": 1,
        "offset": 1,
        "sort": "asc",
        "apikey": etherscan_api_key,
    }
    if DEBUG_LOG_ENABLED:
        print(
            f"[etherscan] query first-tx address={normalized} params={params}"
        )
    try:
        response = requests.get(
            "https://api.etherscan.io/v2/api",
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        print(f"[etherscan] request failed address={normalized} error={exc}")
        return None

    result = payload.get("result")
    if not isinstance(result, list) or not result:
        status = payload.get("status")
        message = payload.get("message")
        print(
            f"[etherscan] empty result address={normalized} "
            f"status={status} message={message}"
        )
        return None
    first = result[0] if isinstance(result[0], dict) else {}
    block_number = first.get("blockNumber")
    try:
        block = max(0, int(block_number))
        print(f"[etherscan] first-tx found address={normalized} block={block}")
        return block
    except (TypeError, ValueError):
        print(
            f"[etherscan] invalid blockNumber address={normalized} "
            f"value={block_number}"
        )
        return None


def _resolve_address_lower_bound(
    session: Session,
    w3: Web3,
    address: str,
    cache: dict[str, int],
    *,
    allium_client: Optional[AlliumClient] = None,
    etherscan_api_key: str | None = None,
    persist_deployment: bool = True,
) -> tuple[int, bool, str]:
    """
    Resolve lower-bound block for any address:
    - contract: creation block
    - EOA: first outbound tx block
    """
    normalized = _normalize_address(address)
    if not normalized:
        return 0, True, "invalid_address"

    if normalized in cache:
        val = cache[normalized]
        return val, val == 0, "address_cache"

    metadata = session.get(AddressMetadata, normalized)
    if metadata:
        if (
            metadata.address_type == "contract"
            and metadata.creation_block is not None
        ):
            block = max(0, int(metadata.creation_block))
            cache[normalized] = block
            return (
                block,
                bool(metadata.needs_retry),
                metadata.source or "address_metadata",
            )
        if (
            metadata.address_type == "eoa"
            and metadata.first_tx_block is not None
        ):
            block = max(0, int(metadata.first_tx_block))
            cache[normalized] = block
            return (
                block,
                bool(metadata.needs_retry),
                metadata.source or "address_metadata",
            )

    try:
        checksum = Web3.to_checksum_address(normalized)
        latest = int(w3.eth.block_number)
    except Exception:
        cache[normalized] = 0
        return 0, True, "address_lookup_failed"

    if _has_code_at_block(w3, checksum, latest):
        block, needs_retry, source = _resolve_creation_block(
            session,
            w3,
            normalized,
            allium_client,
            cache,
            persist_deployment=persist_deployment,
        )
        return block, needs_retry, source

    first_tx_etherscan = _find_first_sender_tx_block_etherscan(
        normalized,
        etherscan_api_key,
    )
    if first_tx_etherscan is not None:
        _upsert_address_metadata(
            session,
            normalized,
            address_type="eoa",
            first_tx_block=first_tx_etherscan,
            source="etherscan_txlist",
            needs_retry=False,
        )
        cache[normalized] = first_tx_etherscan
        return first_tx_etherscan, False, "etherscan_txlist"

    print(
        f"[etherscan] fallback trace_filter_sender address={normalized} "
        "reason=no_etherscan_first_tx"
    )
    first_tx = _find_first_sender_tx_block(w3, normalized)
    if first_tx is not None:
        _upsert_address_metadata(
            session,
            normalized,
            address_type="eoa",
            first_tx_block=first_tx,
            source="trace_filter_sender",
            needs_retry=False,
        )
        cache[normalized] = first_tx
        return first_tx, False, "trace_filter_sender"

    _upsert_address_metadata(
        session,
        normalized,
        address_type="eoa",
        source="trace_filter_sender",
        needs_retry=True,
    )
    cache[normalized] = 0
    return 0, True, "address_unknown"


def _sync_interaction_check_settings() -> None:
    interaction_checks.MAX_TRACE_PAGES_PER_CALL = MAX_TRACE_PAGES_PER_CALL
    interaction_checks.TRACE_FILTER_FN = _trace_filter


def _is_allowed_trace_type(trace: dict) -> bool:
    return interaction_checks._is_allowed_trace_type(trace)


def _normalize_interaction_type(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized == "direct":
        return "contract_direct"
    if normalized == "transitive":
        return "contract_transitive"
    return normalized


def _count_direct_interactions(
    w3: Web3,
    from_address: str,
    to_address: str,
    scan_start: int,
    scan_end: int,
    page_size: int,
    *,
    root_only: bool,
    mode_name: str,
) -> tuple[int, bool]:
    _sync_interaction_check_settings()
    return interaction_checks._count_direct_interactions(
        w3,
        from_address,
        to_address,
        scan_start,
        scan_end,
        page_size,
        root_only=root_only,
        mode_name=mode_name,
    )


def _count_contract_direct_interactions(
    w3: Web3,
    from_address: str,
    to_address: str,
    scan_start: int,
    scan_end: int,
    page_size: int,
) -> tuple[int, bool]:
    _sync_interaction_check_settings()
    return interaction_checks._count_contract_direct_interactions(
        w3,
        from_address,
        to_address,
        scan_start,
        scan_end,
        page_size,
    )


def _count_sender_direct_interactions(
    w3: Web3,
    sender_address: str,
    to_address: str,
    scan_start: int,
    scan_end: int,
    page_size: int,
) -> tuple[int, bool]:
    _sync_interaction_check_settings()
    return interaction_checks._count_sender_direct_interactions(
        w3,
        sender_address,
        to_address,
        scan_start,
        scan_end,
        page_size,
    )


def _trace_touches_target(call_node: dict, target_norm: str) -> bool:
    return interaction_checks._trace_touches_target(call_node, target_norm)


def _count_transitive_interactions(
    w3: Web3,
    from_address: str,
    to_address: str,
    scan_start: int,
    scan_end: int,
    page_size: int,
) -> int:
    _sync_interaction_check_settings()
    return interaction_checks._count_transitive_interactions(
        w3,
        from_address,
        to_address,
        scan_start,
        scan_end,
        page_size,
    )


def _resolve_scan_start(
    from_block: int,
    sender_lower_bound: int,
    last_analyzed_block: Optional[int],
    override_start: Optional[int],
) -> int:
    last_plus_one = (
        (last_analyzed_block + 1) if last_analyzed_block is not None else 0
    )
    candidates = [
        max(0, int(from_block)),
        max(0, int(sender_lower_bound)),
        max(0, int(last_plus_one)),
    ]
    if override_start is not None:
        candidates.append(max(0, int(override_start)))
    return max(candidates)


def _is_first_time_interact(total_interactions: int) -> bool:
    return int(total_interactions) == 0


def _get_hot_record(
    session: Session,
    from_address: str,
    to_address: str,
    interaction_type: str,
) -> Optional[InteractionScanHot]:
    return session.exec(
        select(InteractionScanHot).where(
            InteractionScanHot.from_address == from_address,
            InteractionScanHot.to_address == to_address,
            InteractionScanHot.interaction_type == interaction_type,
        )
    ).first()


def _is_hot_active(
    record: Optional[InteractionScanHot], now: datetime
) -> bool:
    return bool(record and record.hot_until and record.hot_until > now)


def _build_processing_order(
    fast_rows: list[InteractionScanState],
    hot_rows: list[InteractionScanState],
    fast_per_cycle: int,
    hot_per_cycle: int,
) -> list[InteractionScanState]:
    ordered: list[InteractionScanState] = []
    i = 0
    j = 0
    fast_step = max(1, int(fast_per_cycle))
    hot_step = max(1, int(hot_per_cycle))
    while i < len(fast_rows) or j < len(hot_rows):
        for _ in range(fast_step):
            if i >= len(fast_rows):
                break
            ordered.append(fast_rows[i])
            i += 1
        for _ in range(hot_step):
            if j >= len(hot_rows):
                break
            ordered.append(hot_rows[j])
            j += 1
        if i >= len(fast_rows) and j < len(hot_rows):
            ordered.extend(hot_rows[j:])
            break
        if j >= len(hot_rows) and i < len(fast_rows):
            ordered.extend(fast_rows[i:])
            break
    return ordered


def _collect_processing_rows(
    session: Session,
    *,
    interaction_types: list[str],
    only_retry: bool,
    from_filter: Optional[str],
    to_filter: Optional[str],
    include_hot: bool,
    fast_per_cycle: int,
    hot_per_cycle: int,
    limit: Optional[int],
) -> tuple[list[InteractionScanState], int, int]:
    candidates = list(
        _iter_scan_rows(
            session,
            interaction_types=interaction_types,
            only_retry=only_retry,
            from_filter=from_filter,
            to_filter=to_filter,
        )
    )
    if include_hot:
        processing_rows = candidates
        fast_lane_rows = len(candidates)
        hot_lane_rows = 0
    else:
        now = datetime.utcnow()
        fast_rows: list[InteractionScanState] = []
        hot_rows: list[InteractionScanState] = []
        for row in candidates:
            normalized_type = _normalize_interaction_type(row.interaction_type)
            hot = _get_hot_record(
                session,
                row.from_address,
                row.to_address,
                normalized_type,
            )
            if _is_hot_active(hot, now):
                hot_rows.append(row)
            else:
                fast_rows.append(row)
        fast_lane_rows = len(fast_rows)
        hot_lane_rows = len(hot_rows)
        processing_rows = _build_processing_order(
            fast_rows,
            hot_rows,
            fast_per_cycle=fast_per_cycle,
            hot_per_cycle=hot_per_cycle,
        )
    if limit is not None:
        processing_rows = processing_rows[: max(0, int(limit))]
    return processing_rows, fast_lane_rows, hot_lane_rows


def _mark_hot_pair(
    session: Session,
    from_address: str,
    to_address: str,
    interaction_type: str,
    reason: str,
    duration_ms: int,
    cooldown_seconds: int,
) -> None:
    now = datetime.utcnow()
    hot_until = now + timedelta(seconds=max(1, int(cooldown_seconds)))
    record = _get_hot_record(
        session, from_address, to_address, interaction_type
    )
    if record is None:
        record = InteractionScanHot(
            from_address=from_address,
            to_address=to_address,
            interaction_type=interaction_type,
            hot_until=hot_until,
            last_reason=reason,
            last_duration_ms=max(0, int(duration_ms)),
            hit_count=1,
            updated_at=now,
        )
    else:
        record.hot_until = hot_until
        record.last_reason = reason
        record.last_duration_ms = max(0, int(duration_ms))
        record.hit_count = int(record.hit_count or 0) + 1
        record.updated_at = now
    session.add(record)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Incremental backfill of interaction scan state.",
    )
    parser.add_argument(
        "--interaction-type",
        choices=[
            "contract_direct",
            "sender_direct",
            "contract_transitive",
            "sender_transitive",
            "direct",
            "transitive",
        ],
        default=None,
        help="Process only one interaction type",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=5000,
        help="Number of blocks processed per chunk",
    )
    parser.add_argument(
        "--max-chunks-per-row",
        type=int,
        default=1,
        help="Cap chunks processed per state row in one run",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=50,
        help="trace_filter pagination size",
    )
    parser.add_argument(
        "--scan-end",
        type=int,
        default=None,
        help="Upper block bound override (default: latest block)",
    )
    parser.add_argument(
        "--override-start",
        type=int,
        default=None,
        help="Force minimum scan start",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap number of state rows to process",
    )
    parser.add_argument(
        "--only-retry",
        action="store_true",
        help="Only process rows where creation block lookup previously failed",
    )
    parser.add_argument(
        "--from-address",
        dest="from_address",
        default=None,
        help="Restrict sender",
    )
    parser.add_argument(
        "--to-address",
        dest="to_address",
        default=None,
        help="Restrict target",
    )
    parser.add_argument(
        "--seed-from-first-time",
        action="store_true",
        help="Insert missing direct scan rows from first_time_interactions",
    )
    parser.add_argument(
        "--seed-limit",
        type=int,
        default=None,
        help="Cap seeded rows from first_time_interactions",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not persist updates",
    )
    parser.add_argument(
        "--hot-threshold-seconds",
        type=int,
        default=30,
        help="Mark row as hot when one chunk exceeds this duration",
    )
    parser.add_argument(
        "--hot-cooldown-seconds",
        type=int,
        default=600,
        help="Skip hot rows until now + cooldown seconds",
    )
    parser.add_argument(
        "--include-hot",
        action="store_true",
        help="Treat all rows as regular lane (ignore hot lane scheduling)",
    )
    parser.add_argument(
        "--row-time-budget-seconds",
        type=int,
        default=20,
        help="Per-row runtime budget before yielding and marking hot",
    )
    parser.add_argument(
        "--fast-per-cycle",
        type=int,
        default=20,
        help="Number of regular-lane rows to schedule per cycle",
    )
    parser.add_argument(
        "--hot-per-cycle",
        type=int,
        default=2,
        help="Number of hot-lane rows to schedule per cycle",
    )
    parser.add_argument(
        "--round-robin-until-target",
        action="store_true",
        help="Process one chunk per row per round until target block is reached",
    )
    return parser.parse_args()


def _interaction_types_for_run(selected: Optional[str]) -> list[str]:
    if selected:
        normalized = selected.strip().lower()
        if normalized == "direct":
            return ["contract_direct", "sender_direct"]
        if normalized == "transitive":
            return ["contract_transitive", "sender_transitive"]
        return [normalized]
    # Default mode: only direct types
    return ["contract_direct", "sender_direct"]


def main() -> None:
    args = _parse_args()
    selected_types = _interaction_types_for_run(args.interaction_type)

    _ensure_state_table()
    trace_collector = TraceCollector(
        settings.eth_node_url, log_level=settings.log_level
    )
    allium_client = (
        AlliumClient(settings.allium_api_key)
        if settings.allium_api_key
        else None
    )

    from_filter = (
        _normalize_address(args.from_address) if args.from_address else None
    )
    if args.from_address and not from_filter:
        raise SystemExit(f"Invalid --from-address value: {args.from_address}")

    to_filter = (
        _normalize_address(args.to_address) if args.to_address else None
    )
    if args.to_address and not to_filter:
        raise SystemExit(f"Invalid --to-address value: {args.to_address}")

    chunk_size = max(1, int(args.chunk_size))
    max_chunks_per_row = max(1, int(args.max_chunks_per_row))
    if args.round_robin_until_target:
        max_chunks_per_row = 1
    page_size = max(1, int(args.page_size))

    try:
        latest_block = int(trace_collector.w3.eth.block_number)
    except Exception:
        latest_block = 0
    target_block = (
        min(max(0, int(args.scan_end)), latest_block)
        if args.scan_end is not None
        else latest_block
    )

    processed = 0
    updated = 0
    scanned_chunks = 0
    total_hits = 0
    creation_failures = 0
    hot_marked = 0
    budget_preempted = 0
    fast_lane_rows = 0
    hot_lane_rows = 0
    rounds = 0

    with Session(engine) as session:
        if args.seed_from_first_time:
            seeded = 0
            # Seed only direct types from the old first_time_interactions table.
            for seed_type in selected_types:
                if seed_type not in DIRECT_INTERACTION_TYPES:
                    continue
                seeded += _seed_scan_rows_from_first_time(
                    session,
                    interaction_type=seed_type,
                    limit=args.seed_limit,
                )
            print(f"seeded_scan_rows={seeded}")

        address_bound_cache: dict[str, int] = {}
        while True:
            rounds += 1
            round_advanced = 0
            round_remaining = 0
            round_skipped_done = 0
            round_skipped_retry = 0
            processing_rows, fast_lane_rows, hot_lane_rows = (
                _collect_processing_rows(
                    session,
                    interaction_types=selected_types,
                    only_retry=args.only_retry,
                    from_filter=from_filter,
                    to_filter=to_filter,
                    include_hot=args.include_hot,
                    fast_per_cycle=args.fast_per_cycle,
                    hot_per_cycle=args.hot_per_cycle,
                    limit=args.limit,
                )
            )
            if not processing_rows:
                break

            for row in processing_rows:
                if row.last_analyzed_block is not None and int(
                    row.last_analyzed_block
                ) >= int(target_block):
                    round_skipped_done += 1
                    continue
                round_remaining += 1
                processed += 1

                before_last_analyzed = row.last_analyzed_block

                to_lower_bound, to_needs_retry, to_source = (
                    _resolve_address_lower_bound(
                        session,
                        trace_collector.w3,
                        row.to_address,
                        address_bound_cache,
                        allium_client=allium_client,
                        etherscan_api_key=settings.etherscan_api_key,
                        persist_deployment=not args.dry_run,
                    )
                )
                if to_lower_bound > latest_block:
                    print(
                        f"[warn] suspicious creation_block address={row.to_address} "
                        f"creation={to_lower_bound} latest={latest_block} source={to_source}"
                    )
                    to_lower_bound = latest_block
                    to_needs_retry = True

                row.needs_creation_retry = to_needs_retry

                if to_needs_retry:
                    creation_failures += 1
                    round_skipped_retry += 1
                    row.checked_at = datetime.utcnow()
                    print(
                        f"[skip] unresolved creation block id={row.id} "
                        f"type={row.interaction_type} {row.from_address}->{row.to_address} "
                        f"source={to_source}"
                    )
                    if not args.dry_run:
                        session.add(row)
                        session.commit()
                        updated += 1
                    continue

                if (
                    row.last_analyzed_block is not None
                    and row.last_analyzed_block < row.from_block
                ):
                    print(
                        f"[warn] fixing inconsistent bounds id={row.id} "
                        f"from_block={row.from_block} "
                        f"last_analyzed_block={row.last_analyzed_block}"
                    )
                    row.last_analyzed_block = row.from_block - 1

                chunks_done = 0
                normalized_type = _normalize_interaction_type(
                    row.interaction_type
                )

                from_lower_bound, from_needs_retry, from_source = (
                    _resolve_address_lower_bound(
                        session,
                        trace_collector.w3,
                        row.from_address,
                        address_bound_cache,
                        allium_client=allium_client,
                        etherscan_api_key=settings.etherscan_api_key,
                        persist_deployment=not args.dry_run,
                    )
                )
                if from_needs_retry:
                    creation_failures += 1

                effective_start = max(
                    max(0, int(to_lower_bound)),
                    max(0, int(from_lower_bound)),
                    max(0, int(args.override_start))
                    if args.override_start is not None
                    else 0,
                )

                # from_block stores the first effective analyzed block for this pair.
                # Keep it stable after the first successful initialization.
                if row.last_analyzed_block is None:
                    row.from_block = effective_start

                row_started = time.perf_counter()
                while chunks_done < max_chunks_per_row:
                    row_runtime_sec = time.perf_counter() - row_started
                    if row_runtime_sec > int(args.row_time_budget_seconds):
                        budget_preempted += 1
                        hot_marked += 1
                        _mark_hot_pair(
                            session,
                            row.from_address,
                            row.to_address,
                            normalized_type,
                            reason="row_budget_exceeded",
                            duration_ms=int(row_runtime_sec * 1000),
                            cooldown_seconds=args.hot_cooldown_seconds,
                        )
                        print(
                            f"[budget-preempt] id={row.id} type={normalized_type} "
                            f"{row.from_address}->{row.to_address} "
                            f"row_runtime_ms={int(row_runtime_sec * 1000)} "
                            f"budget_s={args.row_time_budget_seconds}"
                        )
                        if not args.dry_run:
                            session.commit()
                        break
                    scan_start = _resolve_scan_start(
                        row.from_block,
                        from_lower_bound,
                        row.last_analyzed_block,
                        args.override_start,
                    )
                    if scan_start < row.from_block:
                        print(
                            f"[warn] scan_start below creation id={row.id} "
                            f"scan_start={scan_start} from_block={row.from_block}"
                        )
                        scan_start = row.from_block

                    if scan_start > target_block:
                        break

                    scan_end = min(target_block, scan_start + chunk_size - 1)
                    chunk_started = time.perf_counter()

                    if normalized_type in TRANSITIVE_INTERACTION_TYPES:
                        hits = _count_transitive_interactions(
                            trace_collector.w3,
                            row.from_address,
                            row.to_address,
                            scan_start,
                            scan_end,
                            page_size,
                        )
                        chunk_complete = True
                    elif normalized_type == "sender_direct":
                        hits, chunk_complete = _count_direct_interactions(
                            trace_collector.w3,
                            row.from_address,
                            row.to_address,
                            scan_start,
                            scan_end,
                            page_size,
                            root_only=True,
                            mode_name="sender_direct",
                        )
                    else:
                        hits, chunk_complete = _count_direct_interactions(
                            trace_collector.w3,
                            row.from_address,
                            row.to_address,
                            scan_start,
                            scan_end,
                            page_size,
                            root_only=False,
                            mode_name="contract_direct",
                        )

                    if not chunk_complete:
                        print(
                            f"[warn] incomplete chunk id={row.id} type={normalized_type} "
                            f"{row.from_address}->{row.to_address} scan={scan_start}-{scan_end}; "
                            "not advancing checkpoint"
                        )
                        break

                    new_total = max(0, int(row.how_many_times)) + int(hits)
                    discovered = hits > 0
                    chunk_duration_ms = int(
                        (time.perf_counter() - chunk_started) * 1000
                    )

                    print(
                        f"[{processed}] id={row.id} type={row.interaction_type} "
                        f"{row.from_address}->{row.to_address} "
                        f"to_lb={row.from_block} to_source={to_source} "
                        f"from_lb={from_lower_bound} from_source={from_source} "
                        f"scan={scan_start}-{scan_end} hits={hits} "
                        f"new_hits={discovered} total={new_total} "
                        f"duration_ms={chunk_duration_ms}"
                    )

<<<<<<< Updated upstream
                    if chunk_duration_ms > int(args.hot_threshold_seconds) * 1000:
=======
                    if (
                        chunk_duration_ms
                        > int(args.hot_threshold_seconds) * 1000
                    ):
>>>>>>> Stashed changes
                        hot_marked += 1
                        _mark_hot_pair(
                            session,
                            row.from_address,
                            row.to_address,
                            normalized_type,
                            reason="slow_chunk",
                            duration_ms=chunk_duration_ms,
                            cooldown_seconds=args.hot_cooldown_seconds,
                        )
                        print(
                            f"[mark-hot] id={row.id} type={normalized_type} "
                            f"{row.from_address}->{row.to_address} "
                            f"duration_ms={chunk_duration_ms} "
                            f"cooldown_seconds={args.hot_cooldown_seconds}"
                        )
                        if not args.dry_run:
                            session.commit()

                    scanned_chunks += 1
                    total_hits += hits

                    row.how_many_times = new_total
<<<<<<< Updated upstream
                    row.first_time_interact = _is_first_time_interact(new_total)
=======
                    row.first_time_interact = _is_first_time_interact(
                        new_total
                    )
>>>>>>> Stashed changes
                    row.last_analyzed_block = scan_end
                    row.checked_at = datetime.utcnow()

                    if not args.dry_run:
                        session.add(row)
                        session.commit()
                        updated += 1

                    chunks_done += 1

                if row.last_analyzed_block is not None and (
                    before_last_analyzed is None
                    or int(row.last_analyzed_block) > int(before_last_analyzed)
                ):
                    round_advanced += 1

            print(
                f"[round-summary] round={rounds} target={target_block} "
                f"rows={len(processing_rows)} remaining={round_remaining} "
                f"advanced={round_advanced} "
                f"skipped={round_skipped_done + round_skipped_retry} "
                f"(done={round_skipped_done}, retry={round_skipped_retry})"
            )

            if not args.round_robin_until_target:
                break
            if round_remaining == 0:
                print(
                    f"[round-robin] completed all rows at target={target_block} "
                    f"after rounds={rounds}"
                )
                break
            if round_advanced == 0:
                print(
                    f"[round-robin] stopping: no progress in round={rounds} "
                    f"target={target_block} remaining_rows={round_remaining}"
                )
                break

        if args.dry_run:
            session.rollback()

    print(
        "completed "
        f"processed={processed} updated={updated} scanned_chunks={scanned_chunks} "
        f"total_hits={total_hits} creation_lookup_failures={creation_failures} "
        f"hot_marked={hot_marked} "
        f"budget_preempted={budget_preempted} "
        f"fast_lane_rows={fast_lane_rows} hot_lane_rows={hot_lane_rows} "
        f"rounds={rounds}"
    )


if __name__ == "__main__":
    main()
