from typing import Optional
import hashlib

from fastapi import Depends, HTTPException, status
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery
from sqlmodel import Session

from src.api.core.config import settings
from src.api.core.database import get_session
from src.api.crud.api_key import get_valid_key_by_plaintext, mark_key_used


def _api_key_header() -> APIKeyHeader:
    return APIKeyHeader(name=settings.api_key_header, auto_error=False)


api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def require_api_key(
    header_key: Optional[str] = Depends(_api_key_header()),
    query_key: Optional[str] = Depends(api_key_query),
    session: Session = Depends(get_session),
):
    if not settings.api_key_auth_enabled:
        return None

    key = header_key or query_key
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )

    # Root key bypass (supports plaintext or SHA-256 hash configured)
    if _is_root_key_value(key):
        return {"admin": True}

    model = get_valid_key_by_plaintext(session, key)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or revoked API key",
        )
    mark_key_used(session, model)
    return {"admin": False, "key_id": model.id}


async def require_admin_api_key(
    header_key: Optional[str] = Depends(_api_key_header()),
    query_key: Optional[str] = Depends(api_key_query),
):
    key = header_key or query_key
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin API key required",
        )
    if not _is_root_key_value(key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key",
        )
    return {"admin": True}


async def require_admin_if_enabled(
    header_key: Optional[str] = Depends(_api_key_header()),
    query_key: Optional[str] = Depends(api_key_query),
):
    # When API key auth is disabled, do not enforce admin.
    if not settings.api_key_auth_enabled:
        return {"admin": True}
    key = header_key or query_key
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin API key required",
        )
    if not _is_root_key_value(key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key",
        )
    return {"admin": True}


def _is_root_key_value(provided: str | None) -> bool:
    if not provided:
        return False
    # Plaintext match
    if settings.root_api_key and provided == settings.root_api_key:
        return True
    # Hash match (SHA-256 hex)
    if settings.root_api_key_hash:
        try:
            digest = hashlib.sha256(provided.encode("utf-8")).hexdigest()
            # compare case-insensitively
            return digest.lower() == settings.root_api_key_hash.strip().lower()
        except Exception:
            return False
    return False
