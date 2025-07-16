from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
import numpy as np

class LiquidationSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class MarketStressLevel(str, Enum):
    CALM = "calm"
    ELEVATED = "elevated"
    HIGH = "high"
    EXTREME = "extreme"

class LiquidationType(str, Enum):
    LONG_LIQUIDATION = "long_liquidation"
    SHORT_LIQUIDATION = "short_liquidation"
    CASCADE_EVENT = "cascade_event"
    FLASH_CRASH = "flash_crash"

class LiquidationEvent(BaseModel):
    event_id: str = Field(..., description="Unique identifier for liquidation event")
    symbol: str = Field(..., description="Trading pair symbol")
    exchange: str = Field(..., description="Exchange identifier")
    timestamp: datetime = Field(..., description="Event timestamp")
    
    # Event classification
    liquidation_type: LiquidationType = Field(..., description="Type of liquidation detected")
    severity: LiquidationSeverity = Field(..., description="Severity level of liquidation")
    confidence_score: float = Field(..., ge=0, le=1, description="Detection confidence")
    
    # Price and volume metrics
    trigger_price: float = Field(..., gt=0, description="Price at liquidation trigger")
    price_impact: float = Field(..., description="Price impact percentage")
    volume_spike_ratio: float = Field(..., ge=1, description="Volume spike vs normal")
    liquidated_amount_usd: Optional[float] = Field(None, description="Estimated liquidated amount")
    
    # Market microstructure
    bid_ask_spread_pct: float = Field(..., ge=0, description="Bid-ask spread percentage")
    order_book_imbalance: float = Field(..., ge=-1, le=1, description="Order book skew")
    market_depth_impact: float = Field(..., ge=0, description="Impact on market depth")
    
    # Technical indicators at event
    rsi: Optional[float] = Field(None, ge=0, le=100)
    volume_weighted_price: Optional[float] = Field(None, gt=0)
    volatility_spike: float = Field(..., ge=1, description="Volatility vs normal")
    
    # Contextual data
    funding_rate: Optional[float] = Field(None, description="Funding rate at event time")
    open_interest_change: Optional[float] = Field(None, description="OI change percentage")
    
    # Event characteristics
    duration_seconds: int = Field(..., ge=0, description="Event duration")
    recovery_time_seconds: Optional[int] = Field(None, description="Time to price recovery")
    
    # Additional insights
    suspected_triggers: List[str] = Field(default_factory=list)
    market_conditions: Dict[str, Union[str, float]] = Field(default_factory=dict)

class MarketStressIndicator(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    overall_stress_level: MarketStressLevel = Field(..., description="Overall market stress")
    stress_score: float = Field(..., ge=0, le=100, description="Quantified stress level")
    
    # Component stress indicators
    volatility_stress: float = Field(..., ge=0, le=100)
    funding_rate_stress: float = Field(..., ge=0, le=100)
    liquidity_stress: float = Field(..., ge=0, le=100)
    correlation_stress: float = Field(..., ge=0, le=100)
    leverage_stress: float = Field(..., ge=0, le=100)
    
    # Market-wide metrics
    avg_funding_rate: float = Field(..., description="Average funding rate across markets")
    total_open_interest_change: float = Field(..., description="24h OI change percentage")
    liquidation_volume_24h: float = Field(..., ge=0, description="24h liquidation volume USD")
    
    # Cross-asset indicators
    btc_dominance: float = Field(..., ge=0, le=100)
    correlation_breakdown: bool = Field(..., description="Whether normal correlations broke")
    fear_greed_index: Optional[int] = Field(None, ge=0, le=100)
    
    # Risk factors
    active_risk_factors: List[str] = Field(default_factory=list)
    warning_signals: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)

class LiquidationRisk(BaseModel):
    symbol: str = Field(..., description="Trading pair symbol")
    exchange: str = Field(..., description="Exchange identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Risk assessment
    liquidation_probability: float = Field(..., ge=0, le=1, description="Probability of liquidation")
    risk_level: LiquidationSeverity = Field(..., description="Risk severity level")
    time_horizon_minutes: int = Field(..., ge=1, description="Risk assessment timeframe")
    
    # Contributing factors
    leverage_ratio: Optional[float] = Field(None, ge=1, description="Current leverage ratio")
    funding_rate_pressure: float = Field(..., ge=0, le=100, description="Funding rate stress")
    liquidity_risk: float = Field(..., ge=0, le=100, description="Liquidity adequacy")
    technical_weakness: float = Field(..., ge=0, le=100, description="Technical pattern risk")
    
    # Threshold levels
    liquidation_price_est: Optional[float] = Field(None, gt=0, description="Estimated liquidation price")
    support_levels: List[float] = Field(default_factory=list)
    resistance_levels: List[float] = Field(default_factory=list)
    
    # Market context
    current_price: float = Field(..., gt=0)
    price_distance_to_risk: float = Field(..., description="Distance to risk zone (%)")
    volume_profile_support: float = Field(..., ge=0, le=100, description="Volume-based support strength")
    
    # Historical context
    similar_events_count: int = Field(..., ge=0, description="Similar events in lookback period")
    avg_recovery_time: Optional[int] = Field(None, description="Average recovery time from similar events")

class CascadeAlert(BaseModel):
    alert_id: str = Field(..., description="Unique alert identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity: LiquidationSeverity = Field(..., description="Cascade severity")
    
    # Cascade characteristics
    initiating_symbol: str = Field(..., description="Symbol that started cascade")
    affected_symbols: List[str] = Field(..., description="Symbols involved in cascade")
    cascade_probability: float = Field(..., ge=0, le=1, description="Probability of cascade event")
    
    # Impact assessment
    estimated_total_liquidations: float = Field(..., ge=0, description="Estimated total liquidation volume")
    price_impact_range: Dict[str, float] = Field(..., description="Expected price impact per symbol")
    duration_estimate_minutes: int = Field(..., ge=1, description="Estimated cascade duration")
    
    # Market conditions
    overall_leverage: float = Field(..., ge=1, description="Market-wide leverage estimate")
    liquidity_adequacy: float = Field(..., ge=0, le=100, description="Market liquidity score")
    correlation_strength: float = Field(..., ge=0, le=1, description="Cross-asset correlation")
    
    # Action recommendations
    immediate_actions: List[str] = Field(default_factory=list)
    risk_mitigation: List[str] = Field(default_factory=list)
    monitoring_priorities: List[str] = Field(default_factory=list)

class LiquidationMonitorRequest(BaseModel):
    symbols: List[str] = Field(..., description="Symbols to monitor")
    exchanges: Optional[List[str]] = Field(None, description="Target exchanges")
    sensitivity_level: float = Field(default=0.7, ge=0, le=1, description="Detection sensitivity")
    alert_threshold: LiquidationSeverity = Field(default=LiquidationSeverity.MEDIUM)
    webhook_url: Optional[str] = Field(None, description="Webhook for real-time alerts")

class LiquidationDetectionResponse(BaseModel):
    detected_events: List[LiquidationEvent]
    market_stress: MarketStressIndicator
    risk_assessments: List[LiquidationRisk]
    cascade_alerts: List[CascadeAlert]
    analysis_timestamp: datetime
    detection_duration_ms: int
    metadata: Dict[str, Union[str, int, float]]

class LeverageMetrics(BaseModel):
    symbol: str = Field(..., description="Trading pair symbol")
    exchange: str = Field(..., description="Exchange identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Funding and leverage data
    funding_rate: float = Field(..., description="Current funding rate")
    funding_rate_8h_avg: float = Field(..., description="8-hour average funding rate")
    funding_rate_24h_avg: float = Field(..., description="24-hour average funding rate")
    predicted_funding_rate: Optional[float] = Field(None, description="Next funding rate prediction")
    
    # Open interest metrics
    open_interest: float = Field(..., ge=0, description="Current open interest")
    open_interest_24h_change: float = Field(..., description="24h OI change percentage")
    open_interest_usd: float = Field(..., ge=0, description="OI in USD terms")
    
    # Leverage indicators
    long_short_ratio: float = Field(..., gt=0, description="Long/short ratio")
    estimated_avg_leverage: float = Field(..., ge=1, description="Estimated average leverage")
    max_leverage_available: int = Field(..., ge=1, description="Maximum leverage offered")
    
    # Liquidation estimates
    long_liquidation_threshold: Optional[float] = Field(None, description="Long position liquidation price estimate")
    short_liquidation_threshold: Optional[float] = Field(None, description="Short position liquidation price estimate")
    liquidation_cluster_density: float = Field(..., ge=0, description="Density of liquidation orders")
    
    # Risk indicators
    funding_rate_volatility: float = Field(..., ge=0, description="Funding rate volatility")
    leverage_stress_score: float = Field(..., ge=0, le=100, description="Overall leverage stress") 