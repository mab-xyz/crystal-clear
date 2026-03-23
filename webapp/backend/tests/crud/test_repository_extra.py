from sqlalchemy.exc import IntegrityError

from src.api.crud.repository import create_repository, update_repository
from src.api.models.repository import RepositoryCreate, RepositoryUpdate


def test_create_repository_rolls_back_and_raises_on_integrity_error(session, monkeypatch):
    called = {"rollback": False}

    def _boom():
        raise IntegrityError("stmt", "params", Exception("dup"))

    def _rollback():
        called["rollback"] = True

    monkeypatch.setattr(session, "commit", _boom)
    monkeypatch.setattr(session, "rollback", _rollback)

    try:
        create_repository(
            session,
            RepositoryCreate(
                protocol="proto",
                version="1.0",
                url="https://example.com",
            ),
        )
        assert False, "expected ValueError"
    except ValueError:
        assert called["rollback"] is True


def test_update_repository_rolls_back_and_raises_on_integrity_error(session, monkeypatch):
    create_repository(
        session,
        RepositoryCreate(
            protocol="protox",
            version="1.0",
            url="https://old.example",
        ),
    )

    called = {"rollback": False}

    def _boom():
        raise IntegrityError("stmt", "params", Exception("dup"))

    def _rollback():
        called["rollback"] = True

    monkeypatch.setattr(session, "commit", _boom)
    monkeypatch.setattr(session, "rollback", _rollback)

    try:
        update_repository(
            session,
            RepositoryUpdate(url="https://new.example"),
            protocol="protox",
            version="1.0",
        )
        assert False, "expected ValueError"
    except ValueError:
        assert called["rollback"] is True
