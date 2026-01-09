# Virtuoso MCP Server - Configuration
# Environment-based settings using pydantic-settings

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """MCP Server configuration from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="VIRTUOSO_MCP_",
        env_file=".env",
        extra="ignore",
    )

    # VPS API URLs (set via environment: VIRTUOSO_MCP_VIRTUOSO_API_URL)
    virtuoso_api_url: str = "http://localhost:8002"
    virtuoso_derivatives_url: str = "http://localhost:8888"

    # Optional API key for protected endpoints
    virtuoso_api_key: Optional[str] = None

    # HTTP client settings
    request_timeout: float = 10.0
    max_retries: int = 3
    retry_delay: float = 1.0

    # Feature flags
    mock_mode: bool = False  # Return mock data instead of calling VPS


# Singleton instance
settings = Settings()
