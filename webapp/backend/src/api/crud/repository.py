from datetime import datetime
from typing import List, Optional
from sqlmodel import Session, select
from src.api.models.repository import *
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from api.models.repository import (
    Repository,
    RepositoryCreate,
    RepositoryUpdate,
)


def create_repository(
    session: Session, repository: RepositoryCreate
) -> Repository:
    """Create new repository entry"""
    db_repository = Repository(**repository.model_dump())
    session.add(db_repository)
    try:
        session.commit()
        session.refresh(db_repository)
        return db_repository
    except IntegrityError as e:
        session.rollback()
        raise ValueError("Repository with these details already exists") from e


def get_repository(
    session: Session, protocol: str, version: str | None = None
) -> Optional[Repository]:
    """Get repository by protocol and optional version"""
    stmt = select(Repository).where(Repository.protocol == protocol)

    if version is not None:
        stmt = stmt.where(Repository.version == version)
    else:
        stmt = stmt.where(Repository.version.is_(None))

    return session.exec(stmt).first()


def get_repositories(
    session: Session,
    skip: int = 0,
    limit: int = 100,
    protocol: Optional[str] = None,
    version: Optional[str] = None,
) -> List[Repository]:
    """Get repositories with optional filters"""
    query = select(Repository)

    if protocol:
        query = query.where(Repository.protocol == protocol)
    if version is not None:
        query = query.where(Repository.version == version)

    query = query.offset(skip).limit(limit)
    return session.exec(query).all()


def update_repository(
    session: Session,
    repository_update: RepositoryUpdate,
    protocol: str,
    version: str | None = None,
) -> Optional[Repository]:
    """Update repository URL"""
    db_repository = get_repository(session, protocol, version)
    if not db_repository:
        return None

    db_repository.url = repository_update.url
    db_repository.last_updated = datetime.now()

    try:
        session.add(db_repository)
        session.commit()
        session.refresh(db_repository)
        return db_repository
    except IntegrityError as e:
        session.rollback()
        raise ValueError(
            "URL update failed due to uniqueness constraint"
        ) from e


def delete_repository(
    session: Session, protocol: str, version: str | None = None
) -> bool:
    """Delete repository entry"""
    db_repository = get_repository(session, protocol, version)
    if not db_repository:
        return False
    session.delete(db_repository)
    session.commit()
    return True
