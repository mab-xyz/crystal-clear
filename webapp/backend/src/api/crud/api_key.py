import hashlib
import secrets
from datetime import datetime
from typing import Optional, Tuple

from sqlmodel import Session, select

from src.api.models.api_key import (
    ApiKey,
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
)


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _to_response(model: ApiKey) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=model.id,  # type: ignore[arg-type]
        name=model.name,
        prefix=model.prefix,
        created_at=model.created_at,
        revoked_at=model.revoked_at,
        last_used_at=model.last_used_at,
    )


def create_api_key(
    session: Session, data: ApiKeyCreate
) -> ApiKeyCreatedResponse:
    # Generate a URL-safe key
    key = secrets.token_urlsafe(48)
    prefix = key[:8]
    key_hash = _hash_key(key)

    model = ApiKey(name=data.name, prefix=prefix, key_hash=key_hash)
    session.add(model)
    session.commit()
    session.refresh(model)

    base = _to_response(model)
    return ApiKeyCreatedResponse(**base.model_dump(), key=key)


def list_api_keys(
    session: Session, include_revoked: bool = False
) -> list[ApiKeyResponse]:
    stmt = select(ApiKey)
    if not include_revoked:
        stmt = stmt.where(ApiKey.revoked_at.is_(None))
    rows = session.exec(stmt).all()
    return [_to_response(r) for r in rows]


def revoke_api_key(session: Session, key_id: int) -> Optional[ApiKeyResponse]:
    model = session.get(ApiKey, key_id)
    if not model or model.revoked_at is not None:
        return None
    model.revoked_at = datetime.utcnow()
    session.add(model)
    session.commit()
    session.refresh(model)
    return _to_response(model)


def get_valid_key_by_plaintext(session: Session, key: str) -> Optional[ApiKey]:
    key_hash = _hash_key(key)
    stmt = select(ApiKey).where(
        ApiKey.key_hash == key_hash, ApiKey.revoked_at.is_(None)
    )
    return session.exec(stmt).first()


def mark_key_used(session: Session, model: ApiKey) -> None:
    model.last_used_at = datetime.utcnow()
    session.add(model)
    session.commit()
