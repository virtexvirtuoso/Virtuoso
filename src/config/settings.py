from typing import Dict, Any, Optional
from pydantic import BaseSettings, Field, validator
import os
from pathlib import Path
from functools import lru_cache

class LoggingSettings(BaseSettings):
    LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    FILE_PATH: Optional[str] = Field(default="logs/app.log", env="LOG_FILE")
    
    @validator("LEVEL")
    def validate_log_level(cls, v):
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return v.upper()

class DatabaseSettings(BaseSettings):
    URL: str = Field(default="http://localhost:8086", env="INFLUXDB_URL")
    TOKEN: str = Field(default="", env="INFLUXDB_TOKEN")
    ORG: str = Field(default="default", env="INFLUXDB_ORG")
    BUCKET: str = Field(default="market_data", env="INFLUXDB_BUCKET")
    TIMEOUT: int = Field(default=30000, env="DB_TIMEOUT")

class MetricsSettings(BaseSettings):
    ENABLED: bool = Field(default=True, env="METRICS_ENABLED")
    PROMETHEUS_PORT: int = Field(default=9090, env="PROMETHEUS_PORT")
    COLLECTION_INTERVAL: int = Field(default=60, env="METRICS_INTERVAL")  # seconds

class TradingSettings(BaseSettings):
    MAX_RETRIES: int = Field(default=3, env="MAX_RETRIES")
    RETRY_DELAY: float = Field(default=1.0, env="RETRY_DELAY")
    DEFAULT_TIMEFRAME: str = Field(default="1", env="DEFAULT_TIMEFRAME")
    CACHE_TTL: int = Field(default=300, env="CACHE_TTL")  # seconds
    
    @validator("DEFAULT_TIMEFRAME")
    def validate_timeframe(cls, v):
        if not v.isdigit():
            raise ValueError("Invalid timeframe format. Must be a number of minutes.")
        return v

class Settings(BaseSettings):
    """Global settings with environment variable support."""
    
    # Project metadata
    PROJECT_NAME: str = "Virtuoso Trading System"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Component settings
    logging: LoggingSettings = LoggingSettings()
    database: DatabaseSettings = DatabaseSettings()
    metrics: MetricsSettings = MetricsSettings()
    trading: TradingSettings = TradingSettings()
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

# Example usage:
# settings = get_settings()
# log_level = settings.logging.LEVEL
# db_url = settings.database.URL 