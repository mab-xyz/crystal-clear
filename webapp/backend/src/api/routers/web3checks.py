"""Ledger "Web3checks on device" API, OpenAPI v0.0.11.

POST /{family}/scan/tx and POST /ethereum/scan/eip-712 return a signed TLV
descriptor; GET /r/{id} serves the report behind the descriptor's tiny URL.
"""

from __future__ import annotations

import asyncio
import html
import json
import re
from typing import Any, Callable

import rlp
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.routing import APIRoute
from loguru import logger
from sqlalchemy.orm import Session

from src.api.core.config import settings
from src.api.core.database import get_session
from src.api.integrations.crystal_clear_adapter import (
    SimulationFailed,
)
from src.api.integrations.risk_engine import RiskEngine
from src.api.routers.analysis import get_tx_risk_from_raw
from src.api.schemas.analysis import RawTxRiskRequest
from src.api.schemas.ledger import (
    Eip712ScanInput,
    ProviderError,
    ScanResponse,
    TxScanInput,
)
from src.api.services import ledger_descriptor as ld
from src.api.services import ledger_hashing as lh
from src.api.services import ledger_reports
from src.api.services.ledger_engine_pool import (
    EnginePool,
    PoolBusy,
    get_ledger_pool,
)
from src.api.services.ledger_mapping import map_verdict

MAINNET = 1
SOLANA_CHAINS = {900, 901, 902}

ERR_NOT_SUPPORTED = 2
ERR_CANNOT_RUN = 3
ERR_INTERNAL = 100


class Web3ChecksRoute(APIRoute):
    """Spec wants 400 (not FastAPI's 422) for input validation errors."""

    def get_route_handler(self) -> Callable:
        original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            try:
                return await original(request)
            except RequestValidationError as exc:
                return JSONResponse(
                    status_code=400,
                    content={"code": 400, "message": str(exc.errors()[:3])},
                )

        return handler


router = APIRouter(route_class=Web3ChecksRoute)
public_router = APIRouter()

_ERRORS: dict[int | str, dict[str, Any]] = {
    400: {"description": "Input fields do not pass validation"},
    401: {"description": "API key is missing or invalid"},
    422: {"model": ProviderError, "description": "Not supported (2) or cannot be run (3)"},
    500: {"description": "Internal error"},
}


# Node errors caused by the submitted transaction itself (spec: "Simulation
# cannot be run", code 3). Anything else is treated as an infrastructure error.
_TX_REJECTED = re.compile(
    r"intrinsic gas too low|tip higher than fee cap|fee cap less than|"
    r"max fee per gas less than|insufficient funds|nonce too (low|high)|"
    r"exceeds block gas limit|gas limit reached|gas uint64 overflow",
    re.IGNORECASE,
)


class _CannotRun(Exception):
    """Simulation cannot be run for this transaction (-> 422 code 3)."""


class _StrictEngine:
    """Engine view whose simulation raises instead of returning empty."""

    def __init__(self, engine: RiskEngine) -> None:
        self._engine = engine
        self.revert_error: str | None = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._engine, name)

    def simulate_and_check_with_edges(self, call_object, **kwargs):
        strict = getattr(
            self._engine, "simulate_and_check_with_edges_strict", None
        )
        fn = strict or self._engine.simulate_and_check_with_edges
        try:
            out = fn(call_object, **kwargs)
            pop = getattr(self._engine, "pop_revert_error", None)
            self.revert_error = pop() if callable(pop) else None
            return out
        except SimulationFailed as exc:
            if _TX_REJECTED.search(str(exc)):
                raise _CannotRun(f"Simulation cannot be run: {exc}") from exc
            raise


def _precheck_account(
    engine: RiskEngine, sender: str, raw_hex: str, block: int
) -> None:
    """trace_call does not enforce nonce/balance; the spec wants code 3."""
    state = getattr(engine, "get_account_state", None)
    if not callable(state):
        return
    f = lh.evm_tx_fields(raw_hex)
    nonce, balance = state(sender, block)
    if f["nonce"] < nonce:
        raise _CannotRun("Simulation cannot be run: field nonce is incorrect")
    if balance < f["value"]:  # we use our own gas params: fees are not charged
        raise _CannotRun("Simulation cannot be run: insufficient funds")


def _err(status: int, code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"code": code, "message": message}
    )


def _bad(message: str) -> JSONResponse:
    return _err(400, 400, message)


def _not_supported(message: str) -> JSONResponse:
    return _err(422, ERR_NOT_SUPPORTED, message)


def _signer():
    key = settings.ledger_signer_private_key_hex
    if not key:
        return None
    return ld.load_private_key(key)


def _resolve_block(risk_engine: RiskEngine, block: int | None) -> int:
    if block is not None:
        return block
    return int(risk_engine.get_latest_block_number())


async def _simulate(
    raw_hex: str, sender: str, block: int, risk_engine: RiskEngine,
    session: Session, check_account: bool = True,
):
    if check_account:
        _precheck_account(risk_engine, sender, raw_hex, block)
    strict = _StrictEngine(risk_engine)
    sim = await get_tx_risk_from_raw(
        RawTxRiskRequest(
            # spec: partner uses its own gas parameters
            raw_tx=lh.with_own_gas(raw_hex) if check_account else raw_hex,
            sender_address=sender,
            block_tag=hex(block),
        ),
        risk_engine=strict,  # type: ignore[arg-type]
        session=session,
    )
    return sim, strict.revert_error


def _finish(
    *,
    session: Session,
    sim: Any,
    revert_error: str | None = None,
    fields: dict[str, Any],
    family: str,
    kind: str,
    block: int,
    request_json: dict[str, Any],
    key,
) -> JSONResponse:
    verdict = map_verdict(sim.status, sim.danger_reason, revert_error)
    simulation = json.loads(sim.model_dump_json())
    if revert_error:
        simulation["reverted"] = revert_error
    report = ledger_reports.store_report(
        session,
        family=family,
        kind=kind,
        block=block,
        request_json=request_json,
        simulation_json=simulation,
    )
    url = ledger_reports.tiny_url(settings.ledger_report_base_url, report.id)
    if len(url) > ld.MAX_TINY_URL:
        raise ValueError(f"report URL longer than {ld.MAX_TINY_URL}: {url}")
    descriptor = ld.sign_descriptor(
        ld.DescriptorFields(
            risk=verdict.risk,
            category=verdict.category,
            provider_message=verdict.message,
            tiny_url=url,
            **fields,
        ),
        key,
    )
    return JSONResponse(
        ScanResponse(
            public_key_id=settings.ledger_public_key_id,
            descriptor="0x" + descriptor.hex(),
            block=block,
            simulation=simulation,
        ).model_dump()
    )


def _handle_failure(exc: Exception) -> JSONResponse:
    if isinstance(exc, PoolBusy):
        return JSONResponse(
            status_code=503,
            content={
                "code": ERR_INTERNAL,
                "message": "Too many simulations in progress, retry shortly",
            },
            headers={"Retry-After": "2"},
        )
    if isinstance(exc, _CannotRun):
        return _err(422, ERR_CANNOT_RUN, str(exc))
    if isinstance(exc, HTTPException):
        if exc.status_code == 422:  # decode failure in the shared core
            return _bad(str(exc.detail))
    logger.exception("web3checks internal error")
    return _err(500, ERR_INTERNAL, "Internal error during transaction simulation")


@router.post(
    "/{family}/scan/tx",
    response_model=ScanResponse,
    responses=_ERRORS,
    summary="Submit a transaction for simulation and validation",
    tags=["transaction"],
)
async def scan_tx(
    family: str,
    body: TxScanInput,
    pool: EnginePool = Depends(get_ledger_pool),
    session: Session = Depends(get_session),
):
    if family == "solana":
        try:
            lh.solana_decode(body.tx.from_, 32)
            lh.solana_decode(body.tx.raw)
        except ValueError as exc:
            return _bad(f"Invalid Solana input: {exc}")
        if body.chain is not None and body.chain not in SOLANA_CHAINS:
            return _not_supported(f"The chain {body.chain} is currently not supported")
        return _not_supported("Solana is currently not supported")
    if family != "ethereum":
        return _not_supported(f"The family {family} is currently not supported")

    if body.chain is None:
        return _bad("chain is required for ethereum")
    try:
        sender = lh.evm_address_bytes(body.tx.from_)
        tx_hash = lh.evm_tx_hash(body.tx.raw)
    except lh.UnsupportedPayload as exc:
        return _not_supported(str(exc))
    except (ValueError, rlp.exceptions.RLPException) as exc:
        return _bad(f"Invalid transaction: {exc}")
    if body.chain != MAINNET:
        return _not_supported(f"The chain {body.chain} is currently not supported")
    key = _signer()
    if key is None:
        return _err(500, ERR_INTERNAL, "Signer key not configured")

    try:
        def job(engine):
            blk = _resolve_block(engine, body.block)
            sim_, rev_ = asyncio.run(
                _simulate(body.tx.raw, body.tx.from_, blk, engine, session)
            )
            return blk, sim_, rev_

        block, sim, revert_error = await pool.run(job)
        return _finish(
            session=session, sim=sim, revert_error=revert_error,
            family="ethereum", kind="tx",
            block=block, key=key,
            request_json=body.model_dump(by_alias=True),
            fields=dict(
                address=sender, tx_hash=tx_hash, chain_id=body.chain,
                simulation_type=ld.SIMULATION_TX,
            ),
        )
    except Exception as exc:  # noqa: BLE001 - mapped to spec error codes
        return _handle_failure(exc)


def _unsigned_call_raw(chain_id: int, to: str) -> str:
    """Unsigned type-2 empty call, used to assess a verifyingContract."""
    payload = [
        chain_id.to_bytes(8, "big").lstrip(b"\0") or b"",
        b"", b"", b"", (1_000_000).to_bytes(3, "big"),
        bytes.fromhex(to[2:]), b"", b"", [],
    ]
    return "0x02" + rlp.encode(payload).hex()


@router.post(
    "/{family}/scan/eip-712",
    response_model=ScanResponse,
    responses=_ERRORS,
    summary="Submit an EIP-712 typed message for simulation and validation",
    tags=["EIP-712"],
)
async def scan_eip712(
    family: str,
    body: Eip712ScanInput,
    pool: EnginePool = Depends(get_ledger_pool),
    session: Session = Depends(get_session),
):
    if family != "ethereum":
        return _not_supported("Only ethereum is supported for EIP-712")
    data = body.msg.data
    try:
        sender = lh.evm_address_bytes(body.msg.from_)
        domain_hash, message_hash = lh.eip712_hashes(data)
        raw_chain = data.get("domain", {}).get("chainId")
        chain_id = int(raw_chain, 0) if isinstance(raw_chain, str) else raw_chain
        chain_id = MAINNET if chain_id is None else int(chain_id)
    except Exception as exc:  # noqa: BLE001 - any parse/hash failure is bad input
        return _bad(f"Invalid EIP-712 message: {exc}")
    if chain_id != MAINNET:
        return _not_supported(f"The chain {chain_id} is currently not supported")
    key = _signer()
    if key is None:
        return _err(500, ERR_INTERNAL, "Signer key not configured")

    verifying = data.get("domain", {}).get("verifyingContract")
    try:
        def job(engine):
            blk = _resolve_block(engine, body.block)
            if (
                isinstance(verifying, str)
                and verifying.startswith("0x")
                and len(verifying) == 42
            ):
                sim_, _ = asyncio.run(
                    _simulate(
                        _unsigned_call_raw(chain_id, verifying),
                        body.msg.from_, blk, engine, session,
                        check_account=False,
                    )
                )
            else:  # nothing on-chain to assess
                from src.api.schemas.analysis import SimulationResponse

                sim_ = SimulationResponse(status="OK", details=[])
            return blk, sim_

        block, sim = await pool.run(job)
        return _finish(
            session=session, sim=sim, family="ethereum", kind="eip-712",
            block=block, key=key,
            request_json=body.model_dump(by_alias=True),
            fields=dict(
                address=sender, tx_hash=message_hash, domain_hash=domain_hash,
                simulation_type=ld.SIMULATION_EIP712,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return _handle_failure(exc)


@public_router.get("/r/{report_id}", include_in_schema=False)
def get_report(
    report_id: str, request: Request, session: Session = Depends(get_session)
):
    report = ledger_reports.get_report(session, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found or expired")
    content = {
        "family": report.family,
        "kind": report.kind,
        "block": report.block,
        "request": report.request_json,
        "simulation": report.simulation_json,
    }
    if "text/html" in request.headers.get("accept", ""):
        pretty = html.escape(json.dumps(content, indent=2))
        return HTMLResponse(
            f"<!doctype html><meta charset=utf-8><title>Report {html.escape(report_id)}"
            f"</title><pre>{pretty}</pre>"
        )
    return JSONResponse(content)
