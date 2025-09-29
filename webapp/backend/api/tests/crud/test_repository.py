from datetime import datetime

from sqlmodel import Session, select

from api.models.repository import (
    Repository,
    RepositoryCreate,
    RepositoryUpdate,
)


def test_create_and_get_repository(session: Session):
    # Create a repository
    repo_data = RepositoryCreate(
        protocol="Uniswap", version="1.0", url="http://repo1.com"
    )
    repo = Repository(**repo_data.model_dump())
    session.add(repo)
    session.commit()
    session.refresh(repo)

    assert repo.protocol == "Uniswap"
    assert repo.version == "1.0"
    assert repo.url == "http://repo1.com"

    # Fetch the repository by ID
    fetched = session.get(Repository, repo.id)
    assert fetched is not None
    assert fetched.protocol == "Uniswap"
    assert fetched.version == "1.0"
    assert fetched.url == "http://repo1.com"


def test_update_repository(session: Session):
    # Create repository
    repo_data = RepositoryCreate(
        protocol="SushiSwap", version=None, url="http://repo2.com"
    )
    repo = Repository(**repo_data.model_dump())
    session.add(repo)
    session.commit()
    session.refresh(repo)

    # Update URL
    update_data = RepositoryUpdate(url="http://new-url.com")
    repo.url = update_data.url
    repo.last_updated = datetime.now()
    session.add(repo)
    session.commit()
    session.refresh(repo)

    assert repo.url == "http://new-url.com"
    assert repo.last_updated > repo.date_added


def test_delete_repository(session: Session):
    # Create repository
    repo_data = RepositoryCreate(
        protocol="Curve", version="2.0", url="http://repo3.com"
    )
    repo = Repository(**repo_data.model_dump())
    session.add(repo)
    session.commit()
    session.refresh(repo)

    repo_id = repo.id
    session.delete(repo)
    session.commit()

    # Ensure it's gone
    deleted = session.get(Repository, repo_id)
    assert deleted is None


def test_list_repositories(session: Session):
    # Create multiple repositories
    repos_data = [
        RepositoryCreate(
            protocol="Uniswap", version="1.0", url="http://repo1.com"
        ),
        RepositoryCreate(
            protocol="SushiSwap", version=None, url="http://repo3.com"
        ),
    ]
    for data in repos_data:
        repo = Repository(**data.model_dump())
        session.add(repo)
    session.commit()

    # Query all repositories
    stmt = select(Repository)
    all_repos = session.exec(stmt).all()
    assert len(all_repos) == 2

    # Filter by protocol
    stmt = select(Repository).where(Repository.protocol == "Uniswap")
    uniswap_repos = session.exec(stmt).all()
    assert len(uniswap_repos) == 1
    assert uniswap_repos[0].protocol == "Uniswap"

    # Filter by version
    stmt = select(Repository).where(Repository.version == "1.0")
    version_1_repos = session.exec(stmt).all()
    assert len(version_1_repos) == 1
    assert version_1_repos[0].version == "1.0"
