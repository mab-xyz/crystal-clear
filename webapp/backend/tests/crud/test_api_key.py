from src.api.crud.api_key import (
    _hash_key,
    create_api_key,
    get_valid_key_by_plaintext,
    list_api_keys,
    mark_key_used,
    revoke_api_key,
)
from src.api.models.api_key import ApiKey, ApiKeyCreate


def test_create_api_key_persists_hashed_key(session, monkeypatch):
    monkeypatch.setattr(
        "src.api.crud.api_key.secrets.token_urlsafe",
        lambda _n: "fixed-secret-key-1234567890",
    )

    created = create_api_key(session, ApiKeyCreate(name="ci"))

    assert created.name == "ci"
    assert created.key == "fixed-secret-key-1234567890"
    assert created.prefix == "fixed-se"

    model = session.get(ApiKey, created.id)
    assert model is not None
    assert model.key_hash == _hash_key("fixed-secret-key-1234567890")


def test_list_api_keys_hides_revoked_by_default(session, monkeypatch):
    monkeypatch.setattr(
        "src.api.crud.api_key.secrets.token_urlsafe",
        lambda _n: "secret-A-1234567890",
    )
    a = create_api_key(session, ApiKeyCreate(name="a"))

    monkeypatch.setattr(
        "src.api.crud.api_key.secrets.token_urlsafe",
        lambda _n: "secret-B-1234567890",
    )
    b = create_api_key(session, ApiKeyCreate(name="b"))

    revoke_api_key(session, b.id)

    active = list_api_keys(session)
    all_items = list_api_keys(session, include_revoked=True)

    assert len(active) == 1
    assert active[0].name == "a"
    assert len(all_items) == 2


def test_revoke_api_key_returns_none_for_missing_or_already_revoked(session, monkeypatch):
    monkeypatch.setattr(
        "src.api.crud.api_key.secrets.token_urlsafe",
        lambda _n: "secret-C-1234567890",
    )
    created = create_api_key(session, ApiKeyCreate(name="c"))

    first = revoke_api_key(session, created.id)
    second = revoke_api_key(session, created.id)
    missing = revoke_api_key(session, 999999)

    assert first is not None
    assert first.revoked_at is not None
    assert second is None
    assert missing is None


def test_get_valid_key_by_plaintext_and_mark_key_used(session, monkeypatch):
    monkeypatch.setattr(
        "src.api.crud.api_key.secrets.token_urlsafe",
        lambda _n: "secret-D-1234567890",
    )
    created = create_api_key(session, ApiKeyCreate(name="d"))

    model = get_valid_key_by_plaintext(session, created.key)
    assert model is not None
    assert model.name == "d"

    mark_key_used(session, model)

    refreshed = session.get(ApiKey, created.id)
    assert refreshed is not None
    assert refreshed.last_used_at is not None

    revoke_api_key(session, created.id)
    revoked_lookup = get_valid_key_by_plaintext(session, created.key)
    assert revoked_lookup is None
