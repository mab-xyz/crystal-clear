from fastapi import APIRouter, Depends, Query, status, HTTPException
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session
from sqlmodel import select

from src.api.core.config import settings
from src.api.core.database import get_session
from src.api.models.interaction_scan_state import InteractionScanState
from src.api.schemas.analysis import (
    ContractDependenciesRequest,
    ContractDependenciesResponse,
    ContractRiskRequest,
    SimulationRequest,
    SimulationResponse,
    RiskAnalysisResponse,
    RawTxRiskRequest,
)
from src.api.schemas.response import ErrorResponse
from src.api.services.analysis_service import (
    analyze_contract_dependencies,
    assess_contract_risk,
)
from src.api.services.interaction_scan_seed import (
    seed_interaction_scan_state_from_tx,
)
from src.api.integrations.crystal_clear_adapter import get_risk_engine
from src.api.integrations.risk_engine import RiskEngine
from eth_account import Account
from eth_account.typed_transactions import TypedTransaction
from hexbytes import HexBytes
from typing import Optional, Any, Dict, List, Union
import rlp
from loguru import logger

router = APIRouter(
    prefix="/v1/analysis",
    tags=["analysis"],
)

ALL_INTERACTION_TYPES = [
    "sender_direct",
    "sender_transitive",
    "contract_direct",
    "contract_transitive",
]


def _normalize_address(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    if not normalized.startswith("0x"):
        return None
    return normalized


def _resolve_checked_interaction_types(
    requested_types: list[str] | None,
    root_contract: str | None,
) -> list[str]:
    requested = requested_types or ALL_INTERACTION_TYPES
    unique: list[str] = []
    seen: set[str] = set()
    for interaction_type in requested:
        if interaction_type not in seen:
            unique.append(interaction_type)
            seen.add(interaction_type)

    # Contract-based checks are not applicable when there is no root contract.
    if not _normalize_address(root_contract):
        unique = [it for it in unique if not it.startswith("contract_")]
    return unique


def _evaluate_interaction_scan_risk(
    *,
    session: Session,
    sender_address: str,
    root_contract: str | None,
    touched_addresses: list[str],
    checked_interaction_types: list[str],
) -> tuple[dict[str, dict[str, bool]], dict[str, dict[str, str]], list[str]]:
    sender_norm = _normalize_address(sender_address)
    root_norm = _normalize_address(root_contract)
    normalized_targets: list[str] = []
    seen_targets: set[str] = set()
    for item in touched_addresses:
        addr = _normalize_address(item)
        if not addr or addr in seen_targets:
            continue
        normalized_targets.append(addr)
        seen_targets.add(addr)

    if not sender_norm or not normalized_targets or not checked_interaction_types:
        return {}, {}, []

    from_candidates = {sender_norm}
    if root_norm:
        from_candidates.add(root_norm)

    rows = session.exec(
        select(InteractionScanState).where(
            InteractionScanState.from_address.in_(list(from_candidates)),
            InteractionScanState.to_address.in_(normalized_targets),
            InteractionScanState.interaction_type.in_(checked_interaction_types),
        )
    ).all()
    row_index = {
        (row.from_address, row.to_address, row.interaction_type): row
        for row in rows
    }

    first_time_map: dict[str, dict[str, bool]] = {}
    state_map: dict[str, dict[str, str]] = {}
    dangerous_types: list[str] = []

    for target in normalized_targets:
        first_time_map[target] = {}
        state_map[target] = {}

        for interaction_type in checked_interaction_types:
            from_addr = sender_norm
            if interaction_type.startswith("contract_"):
                from_addr = root_norm
            if not from_addr:
                continue

            row = row_index.get((from_addr, target, interaction_type))
            if row is None:
                first_time_val = True
                state_val = "MISSING"
            else:
                first_time_val = bool(row.first_time_interact)
                state_val = "FOUND"

            first_time_map[target][interaction_type] = first_time_val
            state_map[target][interaction_type] = state_val
            if first_time_val and interaction_type not in dangerous_types:
                dangerous_types.append(interaction_type)

    return first_time_map, state_map, dangerous_types


def _build_interaction_status(
    checked_interaction_types: list[str],
    dangerous_interaction_types: list[str],
) -> dict[str, str]:
    checked = set(checked_interaction_types)
    dangerous = set(dangerous_interaction_types)
    status_map: dict[str, str] = {}
    for interaction_type in ALL_INTERACTION_TYPES:
        if interaction_type not in checked:
            status_map[interaction_type] = "not_checked"
        elif interaction_type in dangerous:
            status_map[interaction_type] = "dangerous"
        else:
            status_map[interaction_type] = "ok"
    return status_map


@router.get(
    "/{address}/dependencies",
    response_model=ContractDependenciesResponse,
    responses={
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
        422: {
            "description": "Input validation error",
            "model": ErrorResponse,
        },
    },
    status_code=status.HTTP_200_OK,
    summary="Get contract dependencies",
    description="Analyze and return the dependency network for a given contract address.",
    include_in_schema=False,
)
@cache(expire=settings.cache_ttl)
async def get_contract_dependencies(
    address: str,
    from_block: str = Query(None, description="Start block"),
    to_block: str = Query(None, description="End block"),
    session: Session = Depends(get_session),
):
    """
    Get the dependency network for a contract.

    - **address**: Ethereum contract address
    - **from_block**: Optional start block for analysis
    - **to_block**: Optional end block for analysis
    """
    request = ContractDependenciesRequest(
        address=address, from_block=from_block, to_block=to_block
    )

    callGraph = analyze_contract_dependencies(
        session=session,
        address=request.address,
        from_block=request.from_block,
        to_block=request.to_block,
    )

    return ContractDependenciesResponse(**callGraph.model_dump())


@router.get(
    "/{address}/risk",
    response_model=RiskAnalysisResponse,
    responses={
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
        422: {
            "description": "Input validation error",
            "model": ErrorResponse,
        },
    },
    status_code=status.HTTP_200_OK,
    summary="Get contract risk assessment",
    description="Calculate and return the risk assessment for a given contract address.",
    include_in_schema=False,
)
@cache(expire=settings.cache_ttl)
async def get_contract_risk(
    address: str,
    from_block: str = Query(None, description="Start block"),
    to_block: str = Query(None, description="End block"),
    session: Session = Depends(get_session),
    risk_engine: RiskEngine = Depends(get_risk_engine),
):
    request = ContractRiskRequest(
        address=address, from_block=from_block, to_block=to_block
    )

    risk_data = await assess_contract_risk(
        session,
        request.address,
        request.from_block,
        request.to_block,
        risk_engine=risk_engine,
    )

    return risk_data


@router.post(
    "/tx-risk",
    response_model=SimulationResponse,
    responses={
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
        422: {
            "description": "Input validation error",
            "model": ErrorResponse,
        },
    },
    status_code=status.HTTP_200_OK,
    summary="Transaction risk: simulate and check",
    description=(
        "Simulate a transaction via Erigon trace_call, list all touched contracts (including DELEGATECALL), "
        "and report whether it's the first interaction by the sender and the verification status."
    ),
    include_in_schema=False,
)
async def simulate_transaction(
    body: SimulationRequest,
    risk_engine: RiskEngine = Depends(get_risk_engine),
    session: Session = Depends(get_session),
) -> SimulationResponse:
    call_object = {"from": body.from_addr}
    if body.to_addr:
        call_object["to"] = body.to_addr
    if body.data:
        call_object["data"] = body.data
    if body.value:
        call_object["value"] = body.value
    if body.gas:
        call_object["gas"] = body.gas
    if body.gasPrice:
        call_object["gasPrice"] = body.gasPrice
    if body.maxFeePerGas:
        call_object["maxFeePerGas"] = body.maxFeePerGas
    if body.maxPriorityFeePerGas:
        call_object["maxPriorityFeePerGas"] = body.maxPriorityFeePerGas
    if body.tx_type:
        call_object["type"] = body.tx_type

    # Treat empty strings as None for block bounds
    fb = (
        body.from_block
        if (body.from_block and body.from_block.strip() != "")
        else None
    )
    tb = (
        body.to_block
        if (body.to_block and body.to_block.strip() != "")
        else None
    )

    results = risk_engine.simulate_and_check(
        call_object,
        block_tag=body.block_tag or "latest",
        from_block=fb,
        to_block=tb,
        latest_offset=body.latest_offset,
    )

    touched_addresses = list(results.keys())
    checked_interaction_types = _resolve_checked_interaction_types(
        body.interaction_types,
        call_object.get("to"),
    )

    try:
        seeded_rows = seed_interaction_scan_state_from_tx(
            session=session,
            sender_address=body.from_addr,
            root_contract=call_object.get("to"),
            touched_addresses=touched_addresses,
        )
        logger.info(
            "tx-risk seeded interaction_scan_state rows: {}",
            seeded_rows,
        )
    except Exception as exc:
        logger.warning(
            "tx-risk failed to seed interaction_scan_state: {}",
            exc,
        )

    interaction_first_time, interaction_state, dangerous_types = (
        _evaluate_interaction_scan_risk(
            session=session,
            sender_address=body.from_addr,
            root_contract=call_object.get("to"),
            touched_addresses=touched_addresses,
            checked_interaction_types=checked_interaction_types,
        )
    )

    items = [
        {
            "address": addr,
            "first_time": any(
                interaction_first_time.get(
                    _normalize_address(addr) or "",
                    {},
                ).values()
            ),
            "verification": info.get("verification"),
            "depth": info.get("depth"),
            "types": info.get("types"),
            "interaction_first_time": interaction_first_time.get(
                _normalize_address(addr) or "",
                {},
            ),
            "interaction_state": interaction_state.get(
                _normalize_address(addr) or "",
                {},
            ),
        }
        for addr, info in results.items()
    ]

    status = "DANGEROUS" if dangerous_types else "OK"
    danger_reason = "FIRST_TIME_INTERACTION" if dangerous_types else None
    interaction_status = _build_interaction_status(
        checked_interaction_types,
        dangerous_types,
    )

    return SimulationResponse(
        status=status,
        interaction_status=interaction_status,
        details=items,
        dangerous_interaction_types=dangerous_types,
        danger_reason=danger_reason,
    )


def _validate_tx_hash(tx_hash: str) -> str:
    s = (tx_hash or "").strip().lower()
    if (
        s.startswith("0x")
        and len(s) == 66
        and all(c in "0123456789abcdef" for c in s[2:])
    ):
        return s
    raise HTTPException(status_code=422, detail="Invalid tx_hash format")


@router.get(
    "/tx-risk/{tx_hash}",
    response_model=SimulationResponse,
    responses={
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
        422: {
            "description": "Input validation error",
            "model": ErrorResponse,
        },
    },
    status_code=status.HTTP_200_OK,
    summary="Transaction risk by tx hash",
    description=(
        "Analyze a confirmed transaction by hash, list all touched contracts (including DELEGATECALL), "
        "and report whether it's the first interaction by the sender and the verification status."
    ),
    include_in_schema=False,
)
async def get_tx_risk(
    tx_hash: str,
    from_block: str | None = Query(
        None, description="Lower bound block for first-time checks"
    ),
    to_block: str | None = Query(
        None, description="Upper bound block for first-time checks"
    ),
    latest_offset: int | None = Query(
        100, description="Limit first-time checks to N latest blocks"
    ),
    risk_engine: RiskEngine = Depends(get_risk_engine),
) -> SimulationResponse:
    # Basic tx hash validation and sanitize empty bounds
    tx_hash = _validate_tx_hash(tx_hash)
    fb = from_block if (from_block and from_block.strip() != "") else None
    tb = to_block if (to_block and to_block.strip() != "") else None
    lo = latest_offset

    results = risk_engine.simulate_from_tx(
        tx_hash,
        from_block=fb,
        to_block=tb,
        latest_offset=lo,
    )
    items = [
        {
            "address": addr,
            "first_time": info.get("first_time", False),
            "verification": info.get("verification"),
            "depth": info.get("depth"),
            "types": info.get("types"),
        }
        for addr, info in results.items()
    ]

    status = "OK"
    for it in items:
        if it.get("first_time", False):
            status = "DANGEROUS"
        else:
            v = it.get("verification") or {}
            ver = (
                str(v.get("verification", "")).lower()
                if isinstance(v, dict)
                else ""
            )
            if ver not in {"verified", "fully-verified"}:
                status = "DANGEROUS"

    return SimulationResponse(status=status, details=items)


@router.post(
    "/tx-risk-raw",
    response_model=SimulationResponse,
    responses={
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
        422: {
            "description": "Input validation error",
            "model": ErrorResponse,
        },
    },
    status_code=status.HTTP_200_OK,
    summary="Transaction risk: from raw signed tx",
    description=(
        "Decode a raw signed transaction, simulate via trace_call, list all touched contracts, "
        "and assess risk similarly to other endpoints."
    ),
)
async def get_tx_risk_from_raw(
    body: RawTxRiskRequest,
    risk_engine: RiskEngine = Depends(get_risk_engine),
    session: Session = Depends(get_session),
) -> SimulationResponse:
    s = (body.raw_tx or "").strip()
    if not (s.startswith("0x") and len(s) % 2 == 0):
        raise HTTPException(
            status_code=422, detail="Invalid raw_tx hex format"
        )

    try:
        txn_bytes = HexBytes(s)
        decoded: dict = {}
        tx_type_val: Union[int, str]
        elems: Optional[list] = None
        is_signed = False

        # --- 1. Try Typed Transaction (Public API) ---
        try:
            ttx = TypedTransaction.from_bytes(txn_bytes)
            decoded = ttx.as_dict()
            tx_type_val = decoded.get("type", int(txn_bytes[0]))
            is_signed = True
        except Exception:
            # --- 2. Fallback: Manual RLP Decoding (Handles Signed AND Unsigned) ---
            first = txn_bytes[0]

            if first in (1, 2):
                # Type 1 (EIP-2930) or Type 2 (EIP-1559)
                payload = bytes(txn_bytes)[1:]
                try:
                    elems = rlp.decode(payload)
                except Exception as err:
                    # Ruff B904
                    raise ValueError(
                        f"RLP decode failed for Type {first} payload."
                    ) from err

                # Check for Type 1 (EIP-2930)
                if first == 1:
                    # Unsigned=8 elements, Signed=12 elements
                    if len(elems) in (8, 12):
                        decoded = {
                            "to": elems[4],
                            "data": elems[6],
                            "value": int.from_bytes(elems[5], "big")
                            if elems[5]
                            else 0,
                            "gas": int.from_bytes(elems[3], "big")
                            if elems[3]
                            else 0,
                            "gasPrice": int.from_bytes(elems[2], "big")
                            if elems[2]
                            else 0,
                            "type": 1,
                        }
                        tx_type_val = 1
                        if len(elems) == 12:
                            is_signed = True
                    else:
                        tx_type_val = 1
                        is_signed = False
                # Check for Type 2 (EIP-1559)
                else:
                    # Unsigned=9 elements, Signed=12 elements
                    if len(elems) in (9, 12):
                        decoded = {
                            "to": elems[5],
                            "data": elems[7],
                            "value": int.from_bytes(elems[6], "big")
                            if elems[6]
                            else 0,
                            "gas": int.from_bytes(elems[4], "big")
                            if elems[4]
                            else 0,
                            "maxPriorityFeePerGas": int.from_bytes(
                                elems[2], "big"
                            )
                            if elems[2]
                            else 0,
                            "maxFeePerGas": int.from_bytes(elems[3], "big")
                            if elems[3]
                            else 0,
                            "type": 2,
                        }
                        tx_type_val = 2
                        if len(elems) == 12:
                            is_signed = True
                    else:
                        tx_type_val = 2
                        is_signed = False
            else:
                # Legacy (Type 0)
                try:
                    elems = rlp.decode(txn_bytes)
                except Exception as err:
                    raise ValueError(
                        "RLP decode failed for Legacy transaction."
                    ) from err

                # Legacy: Unsigned=6 elements, Signed=9 elements
                if len(elems) in (6, 9):
                    decoded = {
                        "to": elems[3],
                        "data": elems[5],
                        "value": int.from_bytes(elems[4], "big")
                        if elems[4]
                        else 0,
                        "gas": int.from_bytes(elems[2], "big")
                        if elems[2]
                        else 0,
                        "gasPrice": int.from_bytes(elems[1], "big")
                        if elems[1]
                        else 0,
                        "type": 0,
                    }
                    tx_type_val = 0
                    if len(elems) == 9:
                        is_signed = True
                else:
                    tx_type_val = 0
                    is_signed = False

        # --- 3. Sender Recovery ---
        sender: str
        if is_signed:
            # Recover sender from signature (works for all signed types)
            sender = Account.recover_transaction(txn_bytes)
        else:
            # Requires explicit sender address for unsigned transactions
            if not body.sender_address or not body.sender_address.startswith(
                "0x"
            ):
                raise HTTPException(
                    status_code=422,
                    detail=f"Transaction Error: This transaction appears to be unsigned, Type {tx_type_val} transaction has unexpected RLP length: {len(elems)}(expect 12 for Type1 and Type2, expect 9 for Type0). 'sender_address' must be provided in the request body for simulation.",
                )
            # Use the provided sender address
            sender = body.sender_address
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Decode failed: Invalid transaction format or content. Details:{e}",
        ) from e

    # --- 4. Build Call Object and Simulate ---
    call_object = {"from": sender}
    # Mapping decoded fields to call_object format:
    to_field = decoded.get("to")
    if to_field is not None and to_field != b"":
        call_object["to"] = (
            to_field
            if isinstance(to_field, str)
            else "0x" + HexBytes(to_field).hex()
        )
    data_field = decoded.get("data")
    if data_field is not None:
        call_object["data"] = (
            data_field
            if isinstance(data_field, str)
            else "0x" + HexBytes(data_field).hex()
        )
    value_field = decoded.get("value")
    if value_field is not None:
        call_object["value"] = hex(int(value_field))
    gas_field = decoded.get("gas")
    if gas_field is not None:
        call_object["gas"] = hex(int(gas_field))
    gas_price_field = decoded.get("gasPrice")
    if gas_price_field is not None:
        call_object["gasPrice"] = hex(int(gas_price_field))
    mp_field = decoded.get("maxPriorityFeePerGas")
    if mp_field is not None:
        call_object["maxPriorityFeePerGas"] = hex(int(mp_field))
    mf_field = decoded.get("maxFeePerGas")
    if mf_field is not None:
        call_object["maxFeePerGas"] = hex(int(mf_field))
    call_object["type"] = (
        hex(int(tx_type_val)) if isinstance(tx_type_val, int) else tx_type_val
    )

    fb = (
        body.from_block.strip()
        if (body.from_block and body.from_block.strip() != "")
        else None
    )
    tb = (
        body.to_block.strip()
        if (body.to_block and body.to_block.strip() != "")
        else None
    )

    # Simulation step
    results = risk_engine.simulate_and_check(
        call_object,
        block_tag=body.block_tag or "latest",
        from_block=fb,
        to_block=tb,
        latest_offset=body.latest_offset,
    )
    touched_addresses = list(results.keys())
    checked_interaction_types = _resolve_checked_interaction_types(
        [body.interaction_type] if body.interaction_type else None,
        call_object.get("to"),
    )

    items = [
        {
            "address": addr,
            "verification": info.get("verification"),
            "depth": info.get("depth"),
            "types": info.get("types"),
        }
        for addr, info in results.items()
    ]

    # Seed scan-state rows from this request so backfill can process observed pairs.
    try:
        seeded_rows = seed_interaction_scan_state_from_tx(
            session=session,
            sender_address=sender,
            root_contract=call_object.get("to"),
            touched_addresses=touched_addresses,
        )
        logger.info(
            "tx-risk-raw seeded interaction_scan_state rows: {}",
            seeded_rows,
        )
    except Exception as exc:
        logger.warning(
            "tx-risk-raw failed to seed interaction_scan_state: {}",
            exc,
        )

    interaction_first_time, interaction_state, dangerous_types = (
        _evaluate_interaction_scan_risk(
            session=session,
            sender_address=sender,
            root_contract=call_object.get("to"),
            touched_addresses=touched_addresses,
            checked_interaction_types=checked_interaction_types,
        )
    )
    for item in items:
        normalized = _normalize_address(item["address"]) or ""
        first_time_by_type = interaction_first_time.get(normalized, {})
        item["interaction_first_time"] = first_time_by_type
        item["interaction_state"] = interaction_state.get(normalized, {})
        item["first_time"] = any(first_time_by_type.values())

    status_val = "DANGEROUS" if dangerous_types else "OK"
    danger_reason = "FIRST_TIME_INTERACTION" if dangerous_types else None
    interaction_status = _build_interaction_status(
        checked_interaction_types,
        dangerous_types,
    )
    resp = SimulationResponse(
        status=status_val,
        interaction_status=interaction_status,
        details=items,
        dangerous_interaction_types=dangerous_types,
        danger_reason=danger_reason,
    )
    return resp
