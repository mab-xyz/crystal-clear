from src.api.crud.repository import (
    create_repository,
    delete_repository,
    get_repositories,
    get_repository,
    update_repository,
)
from src.api.models.repository import RepositoryCreate, RepositoryUpdate


def test_create_and_get_repository(session):
    created = create_repository(
        session,
        RepositoryCreate(
            protocol="Uniswap",
            version="1.0",
            url="https://github.com/acme/uniswap",
        ),
    )

    assert created.protocol == "Uniswap"
    assert created.version == "1.0"

    fetched = get_repository(session, "Uniswap", "1.0")
    assert fetched is not None
    assert fetched.url == "https://github.com/acme/uniswap"


def test_get_repository_defaults_to_null_version(session):
    create_repository(
        session,
        RepositoryCreate(
            protocol="Curve",
            version=None,
            url="https://github.com/acme/curve",
        ),
    )

    fetched = get_repository(session, "Curve")
    assert fetched is not None
    assert fetched.version is None
    assert fetched.url == "https://github.com/acme/curve"


def test_get_repositories_filters_and_pagination(session):
    rows = [
        RepositoryCreate(
            protocol="UniswapV1",
            version="1.0",
            url="https://github.com/acme/u1",
        ),
        RepositoryCreate(
            protocol="UniswapV2",
            version="2.0",
            url="https://github.com/acme/u2",
        ),
        RepositoryCreate(
            protocol="SushiSwap",
            version=None,
            url="https://github.com/acme/sushi",
        ),
    ]
    for row in rows:
        create_repository(session, row)

    filtered = get_repositories(session, protocol="UniswapV1")
    assert len(filtered) == 1

    paged = get_repositories(session, skip=1, limit=1)
    assert len(paged) == 1
    assert paged[0].protocol in {"UniswapV1", "UniswapV2", "SushiSwap"}

    by_version = get_repositories(session, version="2.0")
    assert len(by_version) == 1
    assert by_version[0].url == "https://github.com/acme/u2"


def test_update_repository_and_missing(session):
    create_repository(
        session,
        RepositoryCreate(
            protocol="Aave",
            version="3.0",
            url="https://github.com/acme/aave-old",
        ),
    )

    updated = update_repository(
        session,
        RepositoryUpdate(url="https://github.com/acme/aave-new"),
        "Aave",
        "3.0",
    )
    assert updated is not None
    assert updated.url == "https://github.com/acme/aave-new"
    assert updated.last_updated > updated.date_added

    missing = update_repository(
        session,
        RepositoryUpdate(url="https://github.com/acme/none"),
        "Missing",
        "1.0",
    )
    assert missing is None


def test_delete_repository_and_missing(session):
    create_repository(
        session,
        RepositoryCreate(
            protocol="Balancer",
            version="1.0",
            url="https://github.com/acme/balancer",
        ),
    )

    deleted = delete_repository(session, "Balancer", "1.0")
    assert deleted is True
    assert get_repository(session, "Balancer", "1.0") is None

    deleted_missing = delete_repository(session, "Balancer", "1.0")
    assert deleted_missing is False
