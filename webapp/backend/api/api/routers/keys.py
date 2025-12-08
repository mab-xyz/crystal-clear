from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from api.core.database import get_session
from api.core.security import require_admin_api_key
from api.crud.api_key import create_api_key, list_api_keys, revoke_api_key
from api.models.api_key import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyListResponse,
    ApiKeyResponse,
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

