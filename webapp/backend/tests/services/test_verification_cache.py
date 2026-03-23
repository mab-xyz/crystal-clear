from datetime import datetime, timedelta

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, SQLModel, create_engine

from src.api.models.contract_verification import ContractVerification
from src.api.services import verification_cache as vc


def _setup_engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine, tables=[ContractVerification.__table__])
    return engine


def test_get_many_filters_expired_and_normalizes(monkeypatch):
    engine = _setup_engine()
    monkeypatch.setattr(vc, "engine", engine)

    now = datetime.utcnow()
    with Session(engine) as session:
        session.add(
            ContractVerification(
                contract_address="0xaaa",
                source="sourcify",
                verification_status="verified",
                details={"address": "0xaaa", "verification": "verified"},
                checked_at=now,
                expires_at=now + timedelta(hours=1),
            )
        )
        session.add(
            ContractVerification(
                contract_address="0xbbb",
                source="sourcify",
                verification_status="not-verified",
                details={"address": "0xbbb", "verification": "not-verified"},
                checked_at=now,
                expires_at=now - timedelta(hours=1),
            )
        )
        session.commit()

    cache = vc.ContractVerificationCache(ttl_seconds=3600)
    result = cache.get_many(["0xAAA", "0xBBB", "bad"])

    assert result == {"0xaaa": {"address": "0xaaa", "verification": "verified"}}


def test_set_and_get_upsert(monkeypatch):
    engine = _setup_engine()
    monkeypatch.setattr(vc, "engine", engine)
    monkeypatch.setattr(vc, "insert", sqlite_insert)

    cache = vc.ContractVerificationCache(ttl_seconds=60)

    cache.set(
        "0xAAA",
        {"address": "0xaaa", "verification": "verified", "source": "sourcify"},
    )
    first = cache.get("0xaaa")
    assert first is not None
    assert first["verification"] == "verified"

    cache.set(
        "0xaaa",
        {"address": "0xaaa", "verification": "not-verified", "source": "sourcify"},
    )
    second = cache.get("0xaaa")
    assert second is not None
    assert second["verification"] == "not-verified"


def test_get_returns_none_for_invalid_address(monkeypatch):
    engine = _setup_engine()
    monkeypatch.setattr(vc, "engine", engine)

    cache = vc.ContractVerificationCache(ttl_seconds=60)
    assert cache.get("not-an-address") is None
