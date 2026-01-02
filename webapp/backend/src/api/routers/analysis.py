from fastapi import APIRouter, Depends, Query, status, HTTPException
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session

from src.api.core.config import settings
from src.api.core.database import get_session
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
from src.api.core.config import cc
from eth_account import Account
from eth_account.typed_transactions import TypedTransaction
from hexbytes import HexBytes
from typing import Optional, Any, Dict, List, Union
import rlp

router = APIRouter(
    prefix="/v1/analysis",
    tags=["analysis"],
)


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
):
    request = ContractRiskRequest(
        address=address, from_block=from_block, to_block=to_block
    )

    risk_data = await assess_contract_risk(
        session, request.address, request.from_block, request.to_block
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
async def simulate_transaction(body: SimulationRequest) -> SimulationResponse:
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

    results = cc.simulate_and_check(
        call_object,
        block_tag=body.block_tag or "latest",
        from_block=fb,
        to_block=tb,
        latest_offset=body.latest_offset,
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

    # Derive global status without short-circuiting; keep all details
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
) -> SimulationResponse:
    # Basic tx hash validation and sanitize empty bounds
    tx_hash = _validate_tx_hash(tx_hash)
    fb = from_block if (from_block and from_block.strip() != "") else None
    tb = to_block if (to_block and to_block.strip() != "") else None
    lo = latest_offset

    results = cc.simulate_from_tx(
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
async def get_tx_risk_from_raw(body: RawTxRiskRequest) -> SimulationResponse:
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
    results = cc.simulate_and_check(
        call_object,
        block_tag=body.block_tag or "latest",
        from_block=fb,
        to_block=tb,
        latest_offset=body.latest_offset,
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

    status_val = "OK"
    for it in items:
        if it.get("first_time", False):
            status_val = "DANGEROUS"
        else:
            v = it.get("verification") or {}
            ver = (
                str(v.get("verification", "")).lower()
                if isinstance(v, dict)
                else ""
            )
            if ver not in {"verified", "fully-verified"}:
                status_val = "DANGEROUS"

    return SimulationResponse(status=status_val, details=items)
