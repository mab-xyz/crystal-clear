import random

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Ethereum Node Configuration
    eth_node_urls: str | None = Field(default=None, alias="ETH_NODE_URLS")
    eth_rpc_timeout_seconds: int = Field(
        120, alias="ETH_RPC_TIMEOUT_SECONDS"
    )

    # Database Configuration
    database_url: str = Field(..., alias="DATABASE_URL")

    # Cache Configuration
    cache_url: str = Field(..., alias="CACHE_URL")
    cache_ttl: int = Field(60, alias="CACHE_TTL")

    # API Configuration
    api_host: str = Field(..., alias="API_HOST")
    api_port: int = Field(..., alias="API_PORT")

    # API Key Auth Configuration
    api_key_auth_enabled: bool = Field(False, alias="API_KEY_AUTH_ENABLED")
    api_key_header: str = Field("X-API-Key", alias="API_KEY_HEADER")
    root_api_key: str | None = Field(default=None, alias="ROOT_API_KEY")

    root_api_key_hash: str | None = Field(
        default=None, alias="ROOT_API_KEY_HASH"
    )

    # Request Timeout
    request_timeout: int = Field(60 * 5, alias="REQUEST_TIMEOUT")

    # Maximum block range for analysis
    MAX_BLOCK_RANGE: int = Field(500, alias="MAX_BLOCK_RANGE")

    # Logging Configuration
    log_level: str = Field("ERROR", alias="LOG_LEVEL")

    # Allium API Key
    allium_api_key: str = Field(..., alias="ALLIUM_API_KEY")

    # Github Token
    github_token: str = Field(..., alias="GITHUB_TOKEN")

    # Etherscan API Key
    etherscan_api_key: str = Field(..., alias="ETHERSCAN_API_KEY")

    # Verification cache
    verification_cache_ttl_seconds: int = Field(
        60 * 60 * 24 * 90, alias="VERIFICATION_CACHE_TTL_SECONDS"
    )

    # First-time interaction cache
    first_time_cache_ttl_seconds: int = Field(
        60 * 60 * 24 * 180, alias="FIRST_TIME_CACHE_TTL_SECONDS"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown env vars instead of raising errors
    )


# Instantiate settings
settings = Settings()


def get_eth_node_url() -> str | None:
    if not settings.eth_node_urls:
        return None
    urls = settings.eth_node_urls.split("|")
    if len(urls) == 1:
        return urls[0]
    from src.api.core.rpc_health import tracker  # avoid circular import at module load
    weights = [tracker.health_ratio(url) for url in urls]
    return random.choices(urls, weights=weights, k=1)[0]
