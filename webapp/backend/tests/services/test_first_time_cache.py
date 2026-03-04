from datetime import datetime, timedelta

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, SQLModel, create_engine

from src.api.models.first_interaction import FirstInteraction
from src.api.services import first_time_cache as ftc


def _setup_engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine, tables=[FirstInteraction.__table__])
    return engine


def test_get_many_filters_expired_and_normalizes(monkeypatch):
    engine = _setup_engine()
    monkeypatch.setattr(ftc, "engine", engine)

    now = datetime.utcnow()
    with Session(engine) as session:
        session.add(
            FirstInteraction(
                from_address="0xaaa",
                to_address="0xbbb",
                from_block=1,
                to_block=2,
                latest_offset=10,
                is_first_time=True,
                checked_at=now,
                expires_at=now + timedelta(hours=1),
            )
        )
        session.add(
            FirstInteraction(
                from_address="0xccc",
                to_address="0xddd",
                from_block=1,
                to_block=2,
                latest_offset=10,
                is_first_time=False,
                checked_at=now,
                expires_at=now - timedelta(hours=1),
            )
        )
        session.commit()

    cache = ftc.FirstInteractionCache(ttl_seconds=3600)
    result = cache.get_many(
        [
            ("0xAAA", "0xBBB", 1, 2, 10),
            ("0xCCC", "0xDDD", 1, 2, 10),
            ("bad", "0xbbb", 1, 2, 10),
        ]
    )

    assert result == {("0xaaa", "0xbbb", 1, 2, 10): True}


def test_set_and_get_upsert(monkeypatch):
    engine = _setup_engine()
    monkeypatch.setattr(ftc, "engine", engine)
    monkeypatch.setattr(ftc, "insert", sqlite_insert)

    cache = ftc.FirstInteractionCache(ttl_seconds=60)

    cache.set("0xAAA", "0xBBB", 1, 2, 10, True)
    assert cache.get("0xaaa", "0xbbb", 1, 2, 10) is True

    cache.set("0xaaa", "0xbbb", 1, 2, 10, False)
    assert cache.get("0xaaa", "0xbbb", 1, 2, 10) is False


def test_set_skips_invalid_address(monkeypatch):
    engine = _setup_engine()
    monkeypatch.setattr(ftc, "engine", engine)
    monkeypatch.setattr(ftc, "insert", sqlite_insert)

    cache = ftc.FirstInteractionCache(ttl_seconds=60)
    cache.set("invalid", "0xbbb", 1, 2, 10, True)

    with Session(engine) as session:
        rows = session.query(FirstInteraction).all()
    assert rows == []
