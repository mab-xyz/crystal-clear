import hashlib

import pytest
from fastapi import HTTPException

from src.api.core import security


@pytest.mark.asyncio
async def test_require_api_key_returns_none_when_auth_disabled(monkeypatch):
    monkeypatch.setattr(security.settings, "api_key_auth_enabled", False)

    result = await security.require_api_key(
        header_key=None,
        query_key=None,
        session=object(),
    )

    assert result is None


@pytest.mark.asyncio
async def test_require_api_key_requires_key_when_enabled(monkeypatch):
    monkeypatch.setattr(security.settings, "api_key_auth_enabled", True)
    monkeypatch.setattr(security.settings, "root_api_key", None)
    monkeypatch.setattr(security.settings, "root_api_key_hash", None)

    with pytest.raises(HTTPException) as exc:
        await security.require_api_key(
            header_key=None,
            query_key=None,
            session=object(),
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "API key required"


@pytest.mark.asyncio
async def test_require_api_key_allows_root_key(monkeypatch):
    monkeypatch.setattr(security.settings, "api_key_auth_enabled", True)
    monkeypatch.setattr(security.settings, "root_api_key", "root-secret")
    monkeypatch.setattr(security.settings, "root_api_key_hash", None)

    result = await security.require_api_key(
        header_key="root-secret",
        query_key=None,
        session=object(),
    )

    assert result == {"admin": True}


@pytest.mark.asyncio
async def test_require_api_key_valid_non_admin_key_marks_used(monkeypatch):
    class _Model:
        id = 7

    marked = {"called": False}

    monkeypatch.setattr(security.settings, "api_key_auth_enabled", True)
    monkeypatch.setattr(security.settings, "root_api_key", None)
    monkeypatch.setattr(security.settings, "root_api_key_hash", None)
    monkeypatch.setattr(
        security,
        "get_valid_key_by_plaintext",
        lambda _session, _key: _Model(),
    )

    def _mark_used(_session, _model):
        marked["called"] = True

    monkeypatch.setattr(security, "mark_key_used", _mark_used)

    result = await security.require_api_key(
        header_key="user-key",
        query_key=None,
        session=object(),
    )

    assert result == {"admin": False, "key_id": 7}
    assert marked["called"] is True


@pytest.mark.asyncio
async def test_require_api_key_rejects_invalid_key(monkeypatch):
    monkeypatch.setattr(security.settings, "api_key_auth_enabled", True)
    monkeypatch.setattr(security.settings, "root_api_key", None)
    monkeypatch.setattr(security.settings, "root_api_key_hash", None)
    monkeypatch.setattr(
        security,
        "get_valid_key_by_plaintext",
        lambda _session, _key: None,
    )

    with pytest.raises(HTTPException) as exc:
        await security.require_api_key(
            header_key="bad-key",
            query_key=None,
            session=object(),
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Invalid or revoked API key"


@pytest.mark.asyncio
async def test_require_admin_api_key_enforces_root(monkeypatch):
    monkeypatch.setattr(security.settings, "root_api_key", "root-secret")
    monkeypatch.setattr(security.settings, "root_api_key_hash", None)

    ok = await security.require_admin_api_key(
        header_key="root-secret",
        query_key=None,
    )
    assert ok == {"admin": True}

    with pytest.raises(HTTPException) as exc:
        await security.require_admin_api_key(header_key="not-root", query_key=None)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_if_enabled(monkeypatch):
    monkeypatch.setattr(security.settings, "api_key_auth_enabled", False)
    result = await security.require_admin_if_enabled(None, None)
    assert result == {"admin": True}

    monkeypatch.setattr(security.settings, "api_key_auth_enabled", True)
    monkeypatch.setattr(security.settings, "root_api_key", "root-secret")
    monkeypatch.setattr(security.settings, "root_api_key_hash", None)

    with pytest.raises(HTTPException) as exc:
        await security.require_admin_if_enabled(None, None)
    assert exc.value.status_code == 401

    ok = await security.require_admin_if_enabled("root-secret", None)
    assert ok == {"admin": True}


def test_is_root_key_value_with_hash(monkeypatch):
    monkeypatch.setattr(security.settings, "root_api_key", None)
    digest = hashlib.sha256("root-secret".encode("utf-8")).hexdigest()
    monkeypatch.setattr(security.settings, "root_api_key_hash", digest.upper())

    assert security._is_root_key_value("root-secret") is True
    assert security._is_root_key_value("wrong") is False
