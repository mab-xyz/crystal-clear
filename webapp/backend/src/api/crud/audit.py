from sqlmodel import Session, select
from src.api.models.audit import Audit, AuditCreate, AuditUpdate
from typing import List
from datetime import datetime
from typing import List

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.api.models.audit import Audit, AuditCreate, AuditUpdate


def create_audit(session: Session, audit_data: AuditCreate) -> Audit:
    """Create new audit entry"""
    audit = Audit(**audit_data.model_dump())
    session.add(audit)
    try:
        session.commit()
        session.refresh(audit)
        return audit
    except IntegrityError as e:
        session.rollback()
        raise ValueError("Audit with these details already exists") from e


def get_audit(
    session: Session,
    protocol: str,
    company: str,
    version: str | None = None,
) -> Audit | None:
    """Get audit by protocol, company and optional version"""
    stmt = select(Audit).where(
        Audit.protocol == protocol, Audit.company == company
    )
    if version is not None:
        stmt = stmt.where(Audit.version == version)
    else:
        stmt = stmt.where(Audit.version.is_(None))

    return session.exec(stmt).first()


def delete_audit(
    session: Session,
    protocol: str,
    company: str,
    version: str | None = None,
) -> bool:
    """Delete audit entry"""
    audit = get_audit(session, protocol, company, version)
    if not audit:
        return False
    session.delete(audit)
    session.commit()
    return True


def get_audits(
    session: Session,
    protocol: str | None = None,
    version: str | None = None,
    company: str | None = None,
) -> List[Audit]:
    """Get audits with optional filters"""
    stmt = select(Audit)

    if protocol:
        stmt = stmt.where(Audit.protocol == protocol)
    if company:
        stmt = stmt.where(Audit.company == company)
    if version is not None:
        stmt = stmt.where(Audit.version == version)

    return session.exec(stmt).all()


def update_audit(
    session: Session,
    audit_data: AuditUpdate,
    protocol: str,
    company: str,
    version: str | None = None,
) -> Audit | None:
    """Update audit URL"""
    audit = get_audit(session, protocol, company, version)
    if not audit:
        return None

    audit.url = audit_data.url
    audit.last_updated = datetime.now()

    try:
        session.add(audit)
        session.commit()
        session.refresh(audit)
        return audit
    except IntegrityError as e:
        session.rollback()
        raise ValueError(
            "URL update failed due to uniqueness constraint"
        ) from e
