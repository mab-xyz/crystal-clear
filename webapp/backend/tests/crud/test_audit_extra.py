from sqlalchemy.exc import IntegrityError

from src.api.crud.audit import create_audit, update_audit
from src.api.models.audit import AuditCreate, AuditUpdate


def test_create_audit_rolls_back_and_raises_on_integrity_error(session, monkeypatch):
    called = {"rollback": False}

    def _boom():
        raise IntegrityError("stmt", "params", Exception("dup"))

    def _rollback():
        called["rollback"] = True

    monkeypatch.setattr(session, "commit", _boom)
    monkeypatch.setattr(session, "rollback", _rollback)

    try:
        create_audit(
            session,
            AuditCreate(
                protocol="uniswap",
                version=None,
                company="trail",
                url="https://example.com",
            ),
        )
        assert False, "expected ValueError"
    except ValueError:
        assert called["rollback"] is True


def test_update_audit_rolls_back_and_raises_on_integrity_error(session, monkeypatch):
    create_audit(
        session,
        AuditCreate(
            protocol="curve",
            version=None,
            company="trail",
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
        update_audit(
            session,
            AuditUpdate(url="https://new.example"),
            protocol="curve",
            company="trail",
            version=None,
        )
        assert False, "expected ValueError"
    except ValueError:
        assert called["rollback"] is True
