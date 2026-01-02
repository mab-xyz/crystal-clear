<<<<<<< HEAD
from crystal_clear import CrystalClear
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
=======
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
>>>>>>> production


class Settings(BaseSettings):
    # Ethereum Node Configuration
<<<<<<< HEAD
    eth_node_url: str | None = Field(default=None, alias="ETH_NODE_URL")

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
    request_timeout: int = Field(60 * 2, alias="REQUEST_TIMEOUT")

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
    log_level=settings.log_level,
)
=======
    eth_node_url: str

    # Database Configuration
    database_url: str

    # Cache Configuration
    cache_url: str
    cache_ttl: int = 60

    # API Configuration
    api_host: str
    api_port: int

    # Request Timeout
    request_timeout: int = 60 * 2  # seconds

    # Maximum block range for analysis
    MAX_BLOCK_RANGE: int = 7000

    # Default block range for analysis
    DEFAULT_BLOCK_RANGE: int = 10

    # Logging Configuration
    log_level: str = "DEBUG"

    # Allium API Key
    allium_api_key: str

    # Github Token
    github_token: str

    # Etherscan API Key
    etherscan_api_key: str

    model_config = ConfigDict(
        case_sensitive=False,
        # NO env_file loaded — read only from actual environment variables
        fields={
            "eth_node_url": "ETH_NODE_URL",
            "database_url": "DATABASE_URL",
            "cache_url": "CACHE_URL",
            "api_host": "API_HOST",
            "api_port": "API_PORT",
            "log_level": "LOG_LEVEL",
            "allium_api_key": "ALLIUM_API_KEY",
            "github_token": "GITHUB_TOKEN",
            "etherscan_api_key": "ETHERSCAN_API_KEY",
        }
    )


settings = Settings()
>>>>>>> production
