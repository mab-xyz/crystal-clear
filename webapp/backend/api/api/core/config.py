from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from crystal_clear import CrystalClear


class Settings(BaseSettings):
    # Ethereum Node Configuration
    eth_node_url: str = Field(..., alias="ETH_NODE_URL")

    # Database Configuration
    database_url: str = Field(..., alias="DATABASE_URL")

    # Cache Configuration
    cache_url: str = Field(..., alias="CACHE_URL")
    cache_ttl: int = Field(60, alias="CACHE_TTL")

    # API Configuration
    api_host: str = Field(..., alias="API_HOST")
    api_port: int = Field(..., alias="API_PORT")

    # Request Timeout
    request_timeout: int = Field(60 * 2, alias="REQUEST_TIMEOUT")

    # Maximum block range for analysis
    MAX_BLOCK_RANGE: int = Field(7000, alias="MAX_BLOCK_RANGE")

    # Logging Configuration
    log_level: str = Field("ERROR", alias="LOG_LEVEL")

    # Allium API Key
    allium_api_key: str = Field(..., alias="ALLIUM_API_KEY")

    # Github Token
    github_token: str = Field(..., alias="GITHUB_TOKEN")

    # Etherscan API Key
    etherscan_api_key: str = Field(..., alias="ETHERSCAN_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown env vars instead of raising errors
    )


# Instantiate settings
settings = Settings()

# Use in CrystalClear
cc = CrystalClear(
    url=settings.eth_node_url,
    allium_api_key=settings.allium_api_key,
    etherscan_api_key=settings.etherscan_api_key,
)
