"""
Pydantic models for comprehensive configuration validation.
Provides type safety and validation for all configuration sections.
"""

from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, validator, model_validator
from enum import Enum
import os


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class MarketType(str, Enum):
    SPOT = "spot"
    FUTURES = "futures" 
    LINEAR = "linear"


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


# Alpha Scanning Configuration
class AlphaTierConfig(BaseModel):
    cooldown_minutes: Optional[int] = Field(None, ge=1)
    cooldown_override: Optional[bool] = False
    max_alerts_per_hour: int = Field(..., ge=1, le=50)
    min_alpha: float = Field(..., ge=0.0, le=1.0)
    min_confidence: float = Field(..., ge=0.0, le=1.0)
    scan_interval_minutes: int = Field(..., ge=1, le=60)


class AlphaFilteringConfig(BaseModel):
    min_alert_value_score: float = Field(..., ge=0.0)
    volume_confirmation: Dict[str, Union[float, bool]] = Field(...)


class AlphaPatternWeights(BaseModel):
    alpha_breakout: float = Field(..., ge=0.0, le=1.0)
    beta_compression: float = Field(..., ge=0.0, le=1.0)
    beta_expansion: float = Field(..., ge=0.0, le=1.0)
    correlation_breakdown: float = Field(..., ge=0.0, le=1.0)
    cross_timeframe: float = Field(..., ge=0.0, le=1.0)


class AlphaThrottlingConfig(BaseModel):
    emergency_override: Dict[str, float] = Field(...)
    max_total_alerts_per_day: int = Field(..., ge=1)
    max_total_alerts_per_hour: int = Field(..., ge=1)


class AlphaValueScoringConfig(BaseModel):
    alpha_weight: float = Field(..., ge=0.0, le=1.0)
    confidence_weight: float = Field(..., ge=0.0, le=1.0)
    pattern_weight: float = Field(..., ge=0.0, le=1.0)
    risk_weight: float = Field(..., ge=0.0, le=1.0)
    volume_weight: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode='after')
    def validate_weights_sum(self):
        """Ensure all weights sum to approximately 1.0"""
        total = self.alpha_weight + self.confidence_weight + self.pattern_weight + self.risk_weight + self.volume_weight
        if not (0.95 <= total <= 1.05):
            raise ValueError(f"Alpha value scoring weights must sum to ~1.0, got {total}")
        return self


class AlphaScanningConfig(BaseModel):
    alpha_tiers: Dict[str, AlphaTierConfig] = Field(...)
    enabled: bool = Field(...)
    filtering: AlphaFilteringConfig = Field(...)
    pattern_weights: AlphaPatternWeights = Field(...)
    throttling: AlphaThrottlingConfig = Field(...)
    value_scoring: AlphaValueScoringConfig = Field(...)


# Analysis Configuration
class OrderbookParametersConfig(BaseModel):
    absorption: Dict[str, Union[float, int]] = Field(...)
    depth: Dict[str, Union[float, int]] = Field(...)
    depth_levels: int = Field(..., ge=1, le=100)
    dom_momentum: Dict[str, Union[float, int]] = Field(...)
    imbalance: Dict[str, Union[float, int]] = Field(...)
    large_orders: Dict[str, Union[float, int, bool]] = Field(...)
    liquidity: Dict[str, Union[float, bool]] = Field(...)
    min_data_points: int = Field(..., ge=1)
    mpi: Dict[str, Union[float, int]] = Field(...)
    obps: Dict[str, Union[float, int]] = Field(...)
    pressure: Dict[str, Union[float, int]] = Field(...)
    price_impact: Dict[str, Union[float, int, bool]] = Field(...)
    sigmoid_transformation: Dict[str, float] = Field(...)
    spread: Dict[str, Union[float, int, bool]] = Field(...)
    support_resistance: Dict[str, Union[float, int]] = Field(...)
    update_interval: int = Field(..., ge=1)


class OrderflowConfig(BaseModel):
    cvd: Dict[str, float] = Field(...)
    divergence: Dict[str, Union[float, int, bool]] = Field(...)
    imbalance: Dict[str, Union[float, int, bool]] = Field(...)
    liquidity: Dict[str, Union[float, int]] = Field(...)
    smart_money_flow: Dict[str, Union[float, int, bool]] = Field(...)
    min_trades: int = Field(..., ge=1)
    open_interest: Dict[str, float] = Field(...)
    trade_flow: Dict[str, Union[float, int]] = Field(...)
    trades_imbalance: Dict[str, Union[float, int]] = Field(...)
    trades_pressure: Dict[str, Union[float, int]] = Field(...)
    volume_threshold: float = Field(..., ge=0.0)


class AnalysisIndicatorsConfig(BaseModel):
    orderbook: Dict[str, OrderbookParametersConfig] = Field(...)
    orderflow: OrderflowConfig = Field(...)
    price_structure: Dict[str, Any] = Field(...)
    sentiment: Dict[str, Any] = Field(...)
    technical: Dict[str, Any] = Field(...)
    volume: Dict[str, Any] = Field(...)


class AnalysisConfig(BaseModel):
    confluence_reference: str = Field(...)
    indicators: AnalysisIndicatorsConfig = Field(...)


# Bitcoin Beta Analysis Configuration
class BitcoinBetaAlertsConfig(BaseModel):
    cooldown_minutes: int = Field(..., ge=1)
    enabled: bool = Field(...)
    min_confidence: float = Field(..., ge=0.0, le=1.0)


class BitcoinBetaThresholdsConfig(BaseModel):
    alpha_threshold: float = Field(..., ge=0.0)
    beta_divergence: float = Field(..., ge=0.0)
    confidence_threshold: float = Field(..., ge=0.0, le=1.0)
    correlation_breakdown: float = Field(..., ge=0.0)
    reversion_beta: float = Field(..., ge=0.0)
    rolling_beta_change: float = Field(..., ge=0.0)
    sector_correlation: float = Field(..., ge=0.0, le=1.0)
    timeframe_consensus: float = Field(..., ge=0.0, le=1.0)


class BitcoinBetaAlphaDetectionConfig(BaseModel):
    alerts: BitcoinBetaAlertsConfig = Field(...)
    enabled: bool = Field(...)
    thresholds: BitcoinBetaThresholdsConfig = Field(...)


class BitcoinBetaReportsConfig(BaseModel):
    enabled: bool = Field(...)
    output_dir: str = Field(...)
    schedule_enabled: bool = Field(...)
    schedule_times: List[str] = Field(...)


class BitcoinBetaTimeframeConfig(BaseModel):
    analysis_period_hours: Optional[int] = Field(None, ge=1)
    analysis_period_days: Optional[int] = Field(None, ge=1)
    description: str = Field(...)
    interval: str = Field(...)
    periods: int = Field(..., ge=1)


class BitcoinBetaAnalysisConfig(BaseModel):
    alpha_detection: BitcoinBetaAlphaDetectionConfig = Field(...)
    reports: BitcoinBetaReportsConfig = Field(...)
    timeframes: Dict[str, BitcoinBetaTimeframeConfig] = Field(...)


# Confluence Configuration
class ConfluenceThresholdsConfig(BaseModel):
    buy: float = Field(..., ge=0.0, le=100.0)
    neutral_buffer: float = Field(..., ge=0.0)
    sell: float = Field(..., ge=0.0, le=100.0)

    @validator('buy')
    def buy_must_be_greater_than_sell(cls, v, values):
        if 'sell' in values and v <= values['sell']:
            raise ValueError('Buy threshold must be greater than sell threshold')
        return v


class ConfluenceComponentWeights(BaseModel):
    orderbook: float = Field(..., ge=0.0, le=1.0)
    orderflow: float = Field(..., ge=0.0, le=1.0)
    price_structure: float = Field(..., ge=0.0, le=1.0)
    sentiment: float = Field(..., ge=0.0, le=1.0)
    technical: float = Field(..., ge=0.0, le=1.0)
    volume: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode='after')
    def weights_must_sum_to_one(self):
        total = sum([self.orderbook, self.orderflow, self.price_structure, 
                    self.sentiment, self.technical, self.volume])
        if not (0.95 <= total <= 1.05):
            raise ValueError(f'Component weights must sum to ~1.0, got {total}')
        return self


class ConfluenceSubComponentWeights(BaseModel):
    orderbook: Dict[str, float] = Field(...)
    orderflow: Dict[str, float] = Field(...)
    price_structure: Dict[str, float] = Field(...)
    sentiment: Dict[str, float] = Field(...)
    technical: Dict[str, float] = Field(...)
    volume: Dict[str, float] = Field(...)

    @validator('*', pre=True)
    def validate_sub_weights(cls, v):
        if isinstance(v, dict):
            total = sum(v.values())
            if not (0.95 <= total <= 1.05):
                raise ValueError(f'Sub-component weights must sum to ~1.0, got {total}')
        return v


class ConfluenceWeightsConfig(BaseModel):
    components: ConfluenceComponentWeights = Field(...)
    sub_components: ConfluenceSubComponentWeights = Field(...)


class ConfluenceConfig(BaseModel):
    thresholds: ConfluenceThresholdsConfig = Field(...)
    weights: ConfluenceWeightsConfig = Field(...)


# Data Processing Configuration
class DataProcessingErrorHandlingConfig(BaseModel):
    log_errors: bool = Field(...)
    max_retries: int = Field(..., ge=0, le=10)
    retry_delay: float = Field(..., ge=0.0)


class DataProcessingFeatureEngineeringConfig(BaseModel):
    market_impact: bool = Field(...)
    orderbook_features: bool = Field(...)
    technical_indicators: bool = Field(...)


class DataProcessingPerformanceConfig(BaseModel):
    cache_enabled: bool = Field(...)
    cache_size: int = Field(..., ge=1)
    parallel_processing: bool = Field(...)


class DataProcessingPipelineStageConfig(BaseModel):
    enabled: bool = Field(...)
    name: str = Field(...)
    timeout: int = Field(..., ge=1)


class DataProcessingStorageConfig(BaseModel):
    compression: str = Field(...)
    format: str = Field(...)
    partition_by: List[str] = Field(...)


class DataProcessingTimeWeightsConfig(BaseModel):
    base: float = Field(..., ge=0.0)
    htf: float = Field(..., ge=0.0)
    ltf: float = Field(..., ge=0.0)
    mtf: float = Field(..., ge=0.0)


class DataProcessingValidationConfig(BaseModel):
    check_duplicates: bool = Field(...)
    check_missing: bool = Field(...)
    check_outliers: bool = Field(...)


class DataProcessingConfig(BaseModel):
    batch_size: int = Field(..., ge=1)
    enabled: bool = Field(...)
    error_handling: DataProcessingErrorHandlingConfig = Field(...)
    feature_engineering: DataProcessingFeatureEngineeringConfig = Field(...)
    max_history: int = Field(..., ge=1)
    max_workers: int = Field(..., ge=1, le=32)
    mode: str = Field(...)
    performance: DataProcessingPerformanceConfig = Field(...)
    pipeline: List[DataProcessingPipelineStageConfig] = Field(...)
    storage: DataProcessingStorageConfig = Field(...)
    time_weights: DataProcessingTimeWeightsConfig = Field(...)
    update_interval: float = Field(..., ge=0.0)
    validation: DataProcessingValidationConfig = Field(...)
    volatility_threshold: float = Field(..., ge=0.0)
    window_size: int = Field(..., ge=1)


# Database Configuration
class InfluxDBConfig(BaseModel):
    bucket: str = Field(...)
    org: str = Field(...)
    timeout: int = Field(..., ge=1000)
    token: str = Field(...)
    url: str = Field(...)


class DatabaseConfig(BaseModel):
    influxdb: InfluxDBConfig = Field(...)
    url: str = Field(...)


# Exchange Configuration
class ExchangeAPICredentialsConfig(BaseModel):
    api_key: str = Field(...)
    api_secret: str = Field(...)


class ExchangeDataPreferencesConfig(BaseModel):
    exclude_symbols: List[str] = Field(...)
    min_24h_volume: int = Field(..., ge=0)
    preferred_quote_currencies: List[str] = Field(...)


class ExchangeRateLimitsConfig(BaseModel):
    requests_per_minute: int = Field(..., ge=1)
    requests_per_second: int = Field(..., ge=1)
    weight_per_minute: Optional[int] = Field(None, ge=1)


class ExchangeWebSocketConfig(BaseModel):
    channels: Optional[List[str]] = Field(None)
    enabled: Optional[bool] = Field(None)
    keep_alive: bool = Field(...)
    mainnet_endpoint: Optional[str] = Field(None)
    ping_interval: int = Field(..., ge=1)
    private: Optional[str] = Field(None)
    public: str = Field(...)
    reconnect_attempts: int = Field(..., ge=1)
    testnet_endpoint: Optional[str] = Field(None)
    testnet_public: Optional[str] = Field(None)


class ExchangeConfig(BaseModel):
    api_credentials: ExchangeAPICredentialsConfig = Field(...)
    data_only: Optional[bool] = Field(None)
    data_preferences: Optional[ExchangeDataPreferencesConfig] = Field(None)
    enabled: bool = Field(...)
    market_types: Optional[List[MarketType]] = Field(None)
    primary: bool = Field(...)
    rate_limits: ExchangeRateLimitsConfig = Field(...)
    rest_endpoint: str = Field(...)
    testnet: bool = Field(...)
    testnet_endpoint: Optional[str] = Field(None)
    websocket: ExchangeWebSocketConfig = Field(...)


class ExchangesConfig(BaseModel):
    binance: Optional[ExchangeConfig] = Field(None)
    bybit: Optional[ExchangeConfig] = Field(None)


# Logging Configuration
class LoggingFormatterConfig(BaseModel):
    datefmt: str = Field(...)
    format: str = Field(...)


class LoggingHandlerConfig(BaseModel):
    class_: str = Field(..., alias='class')
    formatter: str = Field(...)
    level: LogLevel = Field(...)
    stream: Optional[str] = Field(None)
    filename: Optional[str] = Field(None)
    maxBytes: Optional[int] = Field(None, ge=1)
    backupCount: Optional[int] = Field(None, ge=0)


class LoggingLoggerConfig(BaseModel):
    handlers: List[str] = Field(...)
    level: LogLevel = Field(...)
    propagate: bool = Field(...)


class LoggingConfig(BaseModel):
    disable_existing_loggers: bool = Field(...)
    formatters: Dict[str, LoggingFormatterConfig] = Field(...)
    handlers: Dict[str, LoggingHandlerConfig] = Field(...)
    loggers: Dict[str, LoggingLoggerConfig] = Field(...)
    version: int = Field(..., ge=1)


# Portfolio Configuration  
class PortfolioPerformanceConfig(BaseModel):
    max_turnover: float = Field(..., ge=0.0)


class PortfolioRebalancingConfig(BaseModel):
    enabled: bool = Field(...)
    frequency: str = Field(...)
    threshold: float = Field(..., ge=0.0, le=1.0)


class PortfolioConfig(BaseModel):
    performance: PortfolioPerformanceConfig = Field(...)
    rebalancing: PortfolioRebalancingConfig = Field(...)
    target_allocation: Dict[str, float] = Field(...)

    @validator('target_allocation')
    def allocation_must_sum_to_one(cls, v):
        if v:
            total = sum(v.values())
            if not (0.95 <= total <= 1.05):
                raise ValueError(f'Target allocation must sum to ~1.0, got {total}')
        return v


# Risk Configuration
class RiskLimitsConfig(BaseModel):
    max_drawdown: float = Field(..., ge=0.0, le=1.0)
    max_leverage: float = Field(..., ge=1.0)
    max_position_size: float = Field(..., ge=0.0, le=1.0)


class RiskStopLossConfig(BaseModel):
    activation_percentage: float = Field(..., ge=0.0, le=1.0)
    default: float = Field(..., ge=0.0, le=1.0)
    trailing: bool = Field(...)


class RiskTakeProfitConfig(BaseModel):
    activation_percentage: float = Field(..., ge=0.0, le=1.0)
    default: float = Field(..., ge=0.0, le=1.0)
    trailing: bool = Field(...)


class RiskConfig(BaseModel):
    default_risk_percentage: float = Field(..., ge=0.0, le=100.0)
    long_stop_percentage: float = Field(..., ge=0.0, le=100.0)
    max_risk_percentage: float = Field(..., ge=0.0, le=100.0)
    min_risk_percentage: float = Field(..., ge=0.0, le=100.0)
    risk_free_rate: float = Field(..., ge=0.0, le=1.0)
    risk_limits: RiskLimitsConfig = Field(...)
    risk_reward_ratio: float = Field(..., ge=0.0)
    short_stop_percentage: float = Field(..., ge=0.0, le=100.0)
    stop_loss: RiskStopLossConfig = Field(...)
    take_profit: RiskTakeProfitConfig = Field(...)


# System Configuration
class SystemConfig(BaseModel):
    base_dir: str = Field(...)
    cache_dir: str = Field(...)
    data_dir: str = Field(...)
    enable_reporting: bool = Field(...)
    environment: Environment = Field(...)
    log_level: LogLevel = Field(...)
    reports_dir: str = Field(...)
    version: str = Field(...)


# Main Configuration Schema
class VirtuosoConfig(BaseModel):
    """Complete configuration schema for Virtuoso CCXT system."""
    
    alpha_scanning_optimized: AlphaScanningConfig = Field(...)
    analysis: AnalysisConfig = Field(...)
    bitcoin_beta_analysis: BitcoinBetaAnalysisConfig = Field(...)
    confluence: ConfluenceConfig = Field(...)
    data_processing: DataProcessingConfig = Field(...)
    database: DatabaseConfig = Field(...)
    exchanges: ExchangesConfig = Field(...)
    logging: LoggingConfig = Field(...)
    market: Dict[str, Any] = Field(...)  # TODO: Create detailed market config schema
    market_data: Dict[str, Any] = Field(...)  # TODO: Create detailed market_data config schema
    monitoring: Dict[str, Any] = Field(...)  # TODO: Create detailed monitoring config schema
    portfolio: PortfolioConfig = Field(...)
    reporting: Dict[str, Any] = Field(...)  # TODO: Create detailed reporting config schema
    risk: RiskConfig = Field(...)
    rollout: Dict[str, Any] = Field(...)  # TODO: Create detailed rollout config schema
    signal_frequency_tracking: Dict[str, Any] = Field(...)  # TODO: Create detailed signal tracking schema
    signal_tracking: Dict[str, Any] = Field(...)  # TODO: Create detailed signal tracking schema
    system: SystemConfig = Field(...)
    timeframes: Dict[str, Any] = Field(...)  # TODO: Create detailed timeframes schema
    web_server: Dict[str, Any] = Field(...)  # TODO: Create detailed web_server schema
    websocket: Dict[str, Any] = Field(...)  # TODO: Create detailed websocket schema
    feature_flags: Optional[Dict[str, Any]] = Field(None)  # Feature flags configuration

    class Config:
        extra = "allow"  # Allow additional fields for flexibility
        validate_assignment = True  # Validate on assignment
        use_enum_values = True  # Use enum values in serialization


def validate_config(config_dict: Dict[str, Any]) -> VirtuosoConfig:
    """
    Validate configuration dictionary against schema.
    
    Args:
        config_dict: Configuration dictionary to validate
        
    Returns:
        Validated configuration object
        
    Raises:
        ValidationError: If configuration is invalid
    """
    return VirtuosoConfig(**config_dict)


def get_config_schema() -> Dict[str, Any]:
    """
    Get JSON schema for configuration validation.
    
    Returns:
        JSON schema dictionary
    """
    return VirtuosoConfig.schema()