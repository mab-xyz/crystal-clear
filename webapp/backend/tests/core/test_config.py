import pytest
from pydantic import ValidationError

from src.api.core.config import Settings


def _required_settings(**overrides):
    values = {
        "ETH_NODE_URLS": "http://localhost:8545",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
        "CACHE_URL": "redis://localhost:6379",
        "ALLIUM_API_KEY": "allium-key",
        "ETHERSCAN_API_KEY": "etherscan-key",
    }
    values.update(overrides)
    return values


def test_settings_requires_eth_node_urls():
    values = _required_settings()
    values.pop("ETH_NODE_URLS")

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None, **values)

    assert "ETH_NODE_URLS" in str(exc.value)


def test_settings_treats_empty_eth_node_urls_as_missing():
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None, **_required_settings(ETH_NODE_URLS=""))

    assert "ETH_NODE_URLS" in str(exc.value)


def test_settings_requires_cache_url():
    values = _required_settings()
    values.pop("CACHE_URL")

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None, **values)

    assert "CACHE_URL" in str(exc.value)
