"""
Event Types for Virtuoso Trading System

This module defines all event types used in the event-driven architecture.
Each event type is designed to carry specific data relevant to different
components of the trading system while maintaining type safety and performance.

Event Categories:
- Market Data Events: Raw market data from exchanges
- Analysis Events: Results from various analyzers
- Signal Events: Trading signals and recommendations
- Alert Events: System notifications and warnings
- System Events: Internal system state changes

Performance Considerations:
- Events use dataclasses for efficient serialization
- Lazy evaluation for computed properties
- Memory-efficient data structures
- Integration with existing cache layers
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np
from decimal import Decimal

from .event_bus import Event, EventPriority


class DataType(Enum):
    """Types of market data."""
    TICKER = "ticker"
    OHLCV = "ohlcv"
    ORDERBOOK = "orderbook"
    TRADES = "trades"
    FUNDING = "funding"
    LIQUIDATIONS = "liquidations"
    VOLUME_PROFILE = "volume_profile"


class AnalysisType(Enum):
    """Types of analysis results."""
    TECHNICAL = "technical"
    VOLUME = "volume"
    ORDERFLOW = "orderflow" 
    ORDERBOOK = "orderbook_analysis"
    PRICE_STRUCTURE = "price_structure"
    SENTIMENT = "sentiment"
    CONFLUENCE = "confluence"
    LIQUIDATION = "liquidation"
    ALPHA = "alpha"


class SignalType(Enum):
    """Types of trading signals."""
    BUY = "buy"
    SELL = "sell"
    NEUTRAL = "neutral"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# =============================================================================
# Market Data Events
# =============================================================================

@dataclass
class MarketDataUpdatedEvent(Event):
    """Event fired when new market data is received."""
    symbol: str = ""
    exchange: str = ""
    data_type: DataType = DataType.TICKER
    timeframe: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)
    processed_data: Optional[Dict[str, Any]] = None
    data_quality_score: float = 1.0
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = f"market_data.{self.data_type.value}"
        if not self.source:
            self.source = f"{self.exchange}:{self.symbol}"
        self.priority = EventPriority.HIGH  # Market data is high priority


@dataclass  
class OHLCVDataEvent(MarketDataUpdatedEvent):
    """OHLCV candle data event."""
    data_type: DataType = field(default=DataType.OHLCV, init=False)
    candles: Optional[pd.DataFrame] = None
    candle_count: int = 0
    timeframe_minutes: int = 1
    
    def get_latest_candle(self) -> Optional[Dict[str, Any]]:
        """Get the most recent candle data."""
        if self.candles is not None and not self.candles.empty:
            latest = self.candles.iloc[-1]
            return {
                'timestamp': latest.name if hasattr(latest, 'name') else latest.get('timestamp'),
                'open': float(latest.get('open', 0)),
                'high': float(latest.get('high', 0)),
                'low': float(latest.get('low', 0)),
                'close': float(latest.get('close', 0)),
                'volume': float(latest.get('volume', 0))
            }
        return self.raw_data.get('latest_candle')


@dataclass
class OrderBookDataEvent(MarketDataUpdatedEvent):
    """Order book data event."""
    data_type: DataType = field(default=DataType.ORDERBOOK, init=False)
    bids: List[List[float]] = field(default_factory=list)
    asks: List[List[float]] = field(default_factory=list)
    spread: float = 0.0
    depth: int = 0
    
    def get_best_bid_ask(self) -> Dict[str, float]:
        """Get best bid and ask prices."""
        best_bid = self.bids[0][0] if self.bids else 0.0
        best_ask = self.asks[0][0] if self.asks else 0.0
        return {
            'best_bid': best_bid,
            'best_ask': best_ask,
            'spread': best_ask - best_bid if best_ask > 0 and best_bid > 0 else 0.0
        }


@dataclass
class TradeDataEvent(MarketDataUpdatedEvent):
    """Trade data event."""
    data_type: DataType = field(default=DataType.TRADES, init=False)
    trades: List[Dict[str, Any]] = field(default_factory=list)
    volume_24h: float = 0.0
    trade_count: int = 0
    
    def get_trade_summary(self) -> Dict[str, Any]:
        """Get summary of recent trades."""
        if not self.trades:
            return {'buy_volume': 0.0, 'sell_volume': 0.0, 'trade_count': 0}
            
        buy_volume = sum(trade['amount'] for trade in self.trades if trade.get('side') == 'buy')
        sell_volume = sum(trade['amount'] for trade in self.trades if trade.get('side') == 'sell')
        
        return {
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'net_volume': buy_volume - sell_volume,
            'trade_count': len(self.trades),
            'avg_trade_size': sum(trade['amount'] for trade in self.trades) / len(self.trades)
        }


@dataclass
class LiquidationDataEvent(MarketDataUpdatedEvent):
    """Liquidation data event."""
    data_type: DataType = field(default=DataType.LIQUIDATIONS, init=False)
    liquidations: List[Dict[str, Any]] = field(default_factory=list)
    total_liquidated: float = 0.0
    long_liquidations: float = 0.0
    short_liquidations: float = 0.0
    
    def get_liquidation_pressure(self) -> str:
        """Determine liquidation pressure direction."""
        if self.long_liquidations > self.short_liquidations * 1.5:
            return "long_pressure"
        elif self.short_liquidations > self.long_liquidations * 1.5:
            return "short_pressure"
        return "balanced"


# =============================================================================
# Analysis Events
# =============================================================================

@dataclass
class AnalysisCompletedEvent(Event):
    """Event fired when analysis is completed."""
    analyzer_type: AnalysisType = AnalysisType.TECHNICAL
    symbol: str = ""
    timeframe: str = ""
    analysis_result: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    confidence: float = 0.0
    processing_time_ms: float = 0.0
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = f"analysis.{self.analyzer_type.value}"
        if not self.source:
            self.source = f"analyzer:{self.analyzer_type.value}"
        self.priority = EventPriority.NORMAL


@dataclass
class TechnicalAnalysisEvent(AnalysisCompletedEvent):
    """Technical analysis result event."""
    analyzer_type: AnalysisType = field(default=AnalysisType.TECHNICAL, init=False)
    indicators: Dict[str, float] = field(default_factory=dict)
    signals: Dict[str, str] = field(default_factory=dict)
    support_resistance: Dict[str, List[float]] = field(default_factory=dict)
    trend_direction: str = "neutral"
    
    def get_indicator_summary(self) -> Dict[str, Any]:
        """Get summary of technical indicators."""
        return {
            'rsi': self.indicators.get('rsi', 50),
            'macd_signal': self.signals.get('macd', 'neutral'),
            'ema_trend': self.signals.get('ema_crossover', 'neutral'),
            'bb_position': self.signals.get('bollinger_bands', 'neutral'),
            'overall_trend': self.trend_direction
        }


@dataclass
class VolumeAnalysisEvent(AnalysisCompletedEvent):
    """Volume analysis result event."""
    analyzer_type: AnalysisType = field(default=AnalysisType.VOLUME, init=False)
    volume_profile: Dict[str, Any] = field(default_factory=dict)
    volume_delta: float = 0.0
    obv_trend: str = "neutral"
    volume_strength: str = "normal"
    
    def get_volume_signals(self) -> Dict[str, Any]:
        """Get volume-based signals."""
        return {
            'volume_trend': self.obv_trend,
            'volume_strength': self.volume_strength,
            'delta': self.volume_delta,
            'profile_poc': self.volume_profile.get('poc', 0)  # Point of Control
        }


@dataclass
class ConfluenceAnalysisEvent(AnalysisCompletedEvent):
    """Confluence analysis result event."""
    analyzer_type: AnalysisType = field(default=AnalysisType.CONFLUENCE, init=False)
    confluence_score: float = 0.0
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    final_signal: SignalType = SignalType.NEUTRAL
    signal_strength: float = 0.0
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__post_init__()
        self.priority = EventPriority.HIGH  # Confluence results are high priority
        
    def get_signal_breakdown(self) -> Dict[str, Any]:
        """Get detailed signal breakdown."""
        return {
            'overall_score': self.confluence_score,
            'signal': self.final_signal.value,
            'strength': self.signal_strength,
            'technical_score': self.dimension_scores.get('technical', 0),
            'volume_score': self.dimension_scores.get('volume', 0),
            'orderflow_score': self.dimension_scores.get('orderflow', 0),
            'sentiment_score': self.dimension_scores.get('sentiment', 0),
            'components_count': len(self.components)
        }


# =============================================================================
# Signal Events
# =============================================================================

@dataclass
class TradingSignalEvent(Event):
    """Trading signal event."""
    signal_type: SignalType = SignalType.NEUTRAL
    symbol: str = ""
    timeframe: str = ""
    price: float = 0.0
    confidence: float = 0.0
    strength: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    signal_sources: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = f"signal.{self.signal_type.value}"
        if not self.source:
            self.source = "signal_generator"
        self.priority = EventPriority.CRITICAL  # Trading signals are critical
        
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get risk-related metrics for the signal."""
        risk_amount = 0.0
        reward_amount = 0.0
        
        if self.stop_loss and self.price > 0:
            risk_amount = abs(self.price - self.stop_loss)
            
        if self.take_profit and self.price > 0:
            reward_amount = abs(self.take_profit - self.price)
            
        return {
            'risk_amount': risk_amount,
            'reward_amount': reward_amount,
            'risk_reward_ratio': reward_amount / risk_amount if risk_amount > 0 else 0,
            'confidence_weighted_strength': self.confidence * self.strength
        }


@dataclass
class SignalUpdateEvent(Event):
    """Signal update/modification event."""
    original_signal_id: str = ""
    update_type: str = ""  # 'modify', 'cancel', 'execute'
    new_data: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = f"signal.update.{self.update_type}"
        if not self.source:
            self.source = "signal_manager"
        self.priority = EventPriority.HIGH


# =============================================================================
# Alert Events  
# =============================================================================

@dataclass
class SystemAlertEvent(Event):
    """System alert event."""
    alert_type: str = ""
    severity: AlertSeverity = AlertSeverity.INFO
    title: str = ""
    message: str = ""
    component: str = ""
    error_details: Optional[Dict[str, Any]] = None
    requires_action: bool = False
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = f"alert.{self.alert_type}"
        if not self.source:
            self.source = self.component or "system"
        # Set priority based on severity
        priority_map = {
            AlertSeverity.INFO: EventPriority.LOW,
            AlertSeverity.WARNING: EventPriority.NORMAL,
            AlertSeverity.ERROR: EventPriority.HIGH,
            AlertSeverity.CRITICAL: EventPriority.CRITICAL
        }
        self.priority = priority_map.get(self.severity, EventPriority.NORMAL)


@dataclass
class PerformanceAlertEvent(SystemAlertEvent):
    """Performance-related alert event."""
    alert_type: str = field(default="performance", init=False)
    metric_name: str = ""
    current_value: float = 0.0
    threshold_value: float = 0.0
    trend: str = "stable"  # 'improving', 'degrading', 'stable'
    
    def is_threshold_breached(self) -> bool:
        """Check if performance metric breached threshold."""
        return self.current_value > self.threshold_value


@dataclass
class ExchangeAlertEvent(SystemAlertEvent):
    """Exchange-related alert event."""
    alert_type: str = field(default="exchange", init=False)
    exchange_name: str = ""
    connection_status: str = ""
    api_status: str = ""
    last_successful_call: Optional[datetime] = None
    error_rate: float = 0.0


# =============================================================================
# System Events
# =============================================================================

@dataclass  
class ComponentStatusEvent(Event):
    """Component status change event."""
    component_name: str = ""
    old_status: str = ""
    new_status: str = ""
    status_data: Dict[str, Any] = field(default_factory=dict)
    health_score: float = 1.0
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = f"system.component.{self.new_status}"
        if not self.source:
            self.source = self.component_name
        self.priority = EventPriority.NORMAL


@dataclass
class CacheEvent(Event):
    """Cache-related event."""
    cache_type: str = ""  # 'memcached', 'redis'
    operation: str = ""   # 'hit', 'miss', 'set', 'delete', 'flush'
    key: str = ""
    hit_rate: Optional[float] = None
    response_time_ms: float = 0.0
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = f"cache.{self.operation}"
        if not self.source:
            self.source = f"cache:{self.cache_type}"
        self.priority = EventPriority.LOW  # Cache events are informational


@dataclass
class DatabaseEvent(Event):
    """Database-related event."""
    database_type: str = ""
    operation: str = ""  # 'query', 'insert', 'update', 'delete'
    table: str = ""
    execution_time_ms: float = 0.0
    rows_affected: int = 0
    success: bool = True
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = f"database.{self.operation}"
        if not self.source:
            self.source = f"db:{self.database_type}"
        self.priority = EventPriority.LOW


# =============================================================================
# Event Factory Functions
# =============================================================================

def create_market_data_event(
    symbol: str,
    exchange: str,
    data_type: DataType,
    raw_data: Dict[str, Any],
    timeframe: str = "",
    **kwargs
) -> MarketDataUpdatedEvent:
    """Factory function to create market data events."""
    event_classes = {
        DataType.OHLCV: OHLCVDataEvent,
        DataType.ORDERBOOK: OrderBookDataEvent,
        DataType.TRADES: TradeDataEvent,
        DataType.LIQUIDATIONS: LiquidationDataEvent,
    }
    
    event_class = event_classes.get(data_type, MarketDataUpdatedEvent)
    
    return event_class(
        symbol=symbol,
        exchange=exchange,
        raw_data=raw_data,
        timeframe=timeframe,
        **kwargs
    )


def create_analysis_event(
    analyzer_type: AnalysisType,
    symbol: str,
    timeframe: str,
    analysis_result: Dict[str, Any],
    score: float = 0.0,
    **kwargs
) -> AnalysisCompletedEvent:
    """Factory function to create analysis events."""
    event_classes = {
        AnalysisType.TECHNICAL: TechnicalAnalysisEvent,
        AnalysisType.VOLUME: VolumeAnalysisEvent,
        AnalysisType.CONFLUENCE: ConfluenceAnalysisEvent,
    }
    
    event_class = event_classes.get(analyzer_type, AnalysisCompletedEvent)
    
    return event_class(
        symbol=symbol,
        timeframe=timeframe,
        analysis_result=analysis_result,
        score=score,
        **kwargs
    )


def create_alert_event(
    alert_type: str,
    severity: AlertSeverity,
    message: str,
    component: str = "",
    **kwargs
) -> SystemAlertEvent:
    """Factory function to create alert events."""
    event_classes = {
        'performance': PerformanceAlertEvent,
        'exchange': ExchangeAlertEvent,
    }
    
    event_class = event_classes.get(alert_type, SystemAlertEvent)
    
    return event_class(
        alert_type=alert_type,
        severity=severity,
        message=message,
        component=component,
        **kwargs
    )