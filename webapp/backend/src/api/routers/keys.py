from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import Session

from src.api.core.database import get_session
from src.api.core.key_usage import UsageStore
from src.api.core.rate_limit import get_usage, presented_key
from src.api.core.security import require_admin_api_key
from src.api.crud.api_key import create_api_key, list_api_keys, revoke_api_key
from src.api.models.api_key import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyListResponse,
    ApiKeyResponse,
    KeyUsageListResponse,
    KeyUsageResponse,
)

router = APIRouter(prefix="/keys", tags=["keys"]) 


@router.post(
    "/",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an API key",
)
async def create_key(
    payload: ApiKeyCreate,
    _: Any = Depends(require_admin_api_key),
    session: Session = Depends(get_session),
) -> ApiKeyCreatedResponse:
    return create_api_key(session, payload)


@router.get(
    "/",
    response_model=ApiKeyListResponse,
    status_code=status.HTTP_200_OK,
    summary="List API keys",
)
async def list_keys(
    include_revoked: bool = Query(False),
    _: Any = Depends(require_admin_api_key),
    session: Session = Depends(get_session),
) -> ApiKeyListResponse:
    items = list_api_keys(session, include_revoked=include_revoked)
    return ApiKeyListResponse(total=len(items), items=items)


def _usage_row(prefix: str, raw: dict | None, meta=None) -> KeyUsageResponse:
    raw = raw or {}
    return KeyUsageResponse(
        prefix=prefix,
        id=getattr(meta, "id", None),
        name=getattr(meta, "name", None),
        total=raw.get("total", 0),
        scan=raw.get("scan", 0),
        ok_2xx=raw.get("2xx", 0),
        client_error_4xx=raw.get("4xx", 0),
        server_error_5xx=raw.get("5xx", 0),
        by_day=raw.get("by_day", {}),
    )


@router.get(
    "/usage",
    response_model=KeyUsageListResponse,
    summary="Request counts per API key (admin)",
    description="Counts per key over the last N UTC days, from per-day Redis hashes (cheap regardless of traffic).",
)
async def keys_usage(
    days: int = Query(7, ge=1, le=90),
    _: Any = Depends(require_admin_api_key),
    session: Session = Depends(get_session),
    usage: UsageStore = Depends(get_usage),
) -> KeyUsageListResponse:
    raw = await usage.read(days)
    meta = {k.prefix: k for k in list_api_keys(session, include_revoked=True)}
    rows = [_usage_row(p, raw.get(p), meta.get(p)) for p in set(raw) | set(meta)]
    rows.sort(key=lambda r: (-r.total, r.name or r.prefix))
    return KeyUsageListResponse(days=days, keys=rows)


@router.get(
    "/usage/me",
    response_model=KeyUsageResponse,
    summary="Request counts for the calling API key",
)
async def my_usage(
    request: Request,
    days: int = Query(7, ge=1, le=90),
    session: Session = Depends(get_session),
    usage: UsageStore = Depends(get_usage),
) -> KeyUsageResponse:
    key = presented_key(request)
    if not key:
        raise HTTPException(status_code=401, detail="API key required")
    prefix = key[:8]
    raw = await usage.read(days, prefix=prefix)
    meta = {k.prefix: k for k in list_api_keys(session, include_revoked=True)}
    return _usage_row(prefix, raw.get(prefix), meta.get(prefix))


@router.delete(
    "/{key_id}",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke API key",
)
async def revoke_key(
    key_id: int,
    _: Any = Depends(require_admin_api_key),
    session: Session = Depends(get_session),
) -> ApiKeyResponse:
    res = revoke_api_key(session, key_id)
    if not res:
        raise HTTPException(status_code=404, detail="Key not found or already revoked")
    return res
