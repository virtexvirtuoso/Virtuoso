"""
Signals Schema
==============

Unified contract for analysis:signals cache key.

Handles trading signals with confluence scores and component breakdowns.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import logging
from .base import CacheSchema, SchemaVersion

logger = logging.getLogger(__name__)


@dataclass
class SignalComponentsSchema:
    """
    Schema for signal component scores

    Each signal is composed of multiple analysis components.
    Each component contributes to the overall confluence score.

    Components:
        technical: Technical indicators (RSI, MACD, etc.)
        volume: Volume analysis
        orderflow: Order flow analysis
        sentiment: Market sentiment
        orderbook: Orderbook depth and imbalance
        price_structure: Price structure analysis
    """
    technical: float = 50.0
    volume: float = 50.0
    orderflow: float = 50.0
    sentiment: float = 50.0
    orderbook: float = 50.0
    price_structure: float = 50.0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            'technical': self.technical,
            'volume': self.volume,
            'orderflow': self.orderflow,
            'sentiment': self.sentiment,
            'orderbook': self.orderbook,
            'price_structure': self.price_structure,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SignalComponentsSchema':
        """Create from dictionary"""
        if not isinstance(data, dict):
            return cls()

        return cls(
            technical=data.get('technical', 50.0),
            volume=data.get('volume', 50.0),
            orderflow=data.get('orderflow', 50.0),
            sentiment=data.get('sentiment', 50.0),
            orderbook=data.get('orderbook', 50.0),
            price_structure=data.get('price_structure', 50.0),
        )


@dataclass
class SignalSchema:
    """
    Schema for individual trading signal

    Represents a single trading signal for one symbol with all its
    associated data and analysis components.

    Fields:
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        confluence_score: Overall confluence score (0-100)
        price: Current price
        change_24h: 24-hour price change percentage
        volume_24h: 24-hour volume
        high_24h: 24-hour high price
        low_24h: 24-hour low price
        reliability: Signal reliability score (0-100)
        sentiment: Signal sentiment (BULLISH, BEARISH, NEUTRAL)
        components: Component scores breakdown
        has_breakdown: Whether detailed breakdown is available
    """
    symbol: str = ""
    confluence_score: float = 50.0
    price: float = 0.0
    change_24h: float = 0.0
    volume_24h: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    reliability: float = 75.0
    sentiment: str = "NEUTRAL"
    components: Optional[SignalComponentsSchema] = None
    has_breakdown: bool = False

    def __post_init__(self):
        """Initialize components if not provided"""
        if self.components is None:
            self.components = SignalComponentsSchema()
        elif isinstance(self.components, dict):
            self.components = SignalComponentsSchema.from_dict(self.components)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary with aliases for compatibility

        Provides both 'confluence_score' and 'score' for backward compatibility
        """
        data = {
            'symbol': self.symbol,
            'confluence_score': self.confluence_score,
            'score': self.confluence_score,  # Alias
            'price': self.price,
            'change_24h': self.change_24h,
            'volume_24h': self.volume_24h,
            'high_24h': self.high_24h,
            'low_24h': self.low_24h,
            'reliability': self.reliability,
            'sentiment': self.sentiment,
            'has_breakdown': self.has_breakdown,
        }

        if self.components:
            if isinstance(self.components, SignalComponentsSchema):
                data['components'] = self.components.to_dict()
            elif isinstance(self.components, dict):
                data['components'] = self.components
            else:
                data['components'] = {}

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SignalSchema':
        """Create signal from dictionary"""
        if not isinstance(data, dict):
            return cls()

        # Handle components
        components_data = data.get('components')
        if components_data:
            if isinstance(components_data, dict):
                components = SignalComponentsSchema.from_dict(components_data)
            else:
                components = SignalComponentsSchema()
        else:
            components = SignalComponentsSchema()

        return cls(
            symbol=data.get('symbol', ''),
            confluence_score=data.get('confluence_score', data.get('score', 50.0)),
            price=data.get('price', 0.0),
            change_24h=data.get('change_24h', 0.0),
            volume_24h=data.get('volume_24h', data.get('volume', 0.0)),
            high_24h=data.get('high_24h', 0.0),
            low_24h=data.get('low_24h', 0.0),
            reliability=data.get('reliability', 75.0),
            sentiment=data.get('sentiment', 'NEUTRAL'),
            components=components,
            has_breakdown=data.get('has_breakdown', False),
        )


@dataclass
class SignalsSchema(CacheSchema):
    """
    Unified schema for analysis:signals cache key

    Represents the complete set of trading signals with metadata.

    Primary Data:
        signals: List of trading signals

    Statistics:
        total_signals: Total number of signals generated
        long_signals: Number of bullish/long signals
        short_signals: Number of bearish/short signals
        avg_confluence_score: Average confluence score
        avg_reliability: Average reliability score

    Quick Access:
        top_symbols: List of top symbols by confluence score
    """

    # Class constants
    CACHE_KEY = "analysis:signals"
    VERSION = SchemaVersion.V1

    # Primary data
    signals: List[Dict[str, Any]] = field(default_factory=list)

    # Statistics
    total_signals: int = 0
    long_signals: int = 0
    short_signals: int = 0
    avg_confluence_score: float = 50.0
    avg_reliability: float = 75.0

    # Quick access
    top_symbols: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Auto-calculate statistics from signals"""
        if self.signals and len(self.signals) > 0:
            self.total_signals = len(self.signals)

            # Count sentiment types
            self.long_signals = sum(
                1 for s in self.signals
                if s.get('sentiment', '').upper() in ['BULLISH', 'LONG']
            )
            self.short_signals = sum(
                1 for s in self.signals
                if s.get('sentiment', '').upper() in ['BEARISH', 'SHORT']
            )

            # Calculate averages
            if self.total_signals > 0:
                self.avg_confluence_score = sum(
                    s.get('confluence_score', s.get('score', 50))
                    for s in self.signals
                ) / self.total_signals

                self.avg_reliability = sum(
                    s.get('reliability', 75)
                    for s in self.signals
                ) / self.total_signals

            # Extract top symbols
            sorted_signals = sorted(
                self.signals,
                key=lambda s: s.get('confluence_score', s.get('score', 0)),
                reverse=True
            )
            self.top_symbols = [
                s.get('symbol', '')
                for s in sorted_signals[:10]
                if s.get('symbol')
            ]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dict with aliases for backward compatibility

        Provides both 'signals' and 'recent_signals' keys since different
        parts of the system use different names.
        """
        data = super().to_dict()
        # Add alias for backward compatibility
        data['recent_signals'] = data['signals']
        return data

    def validate(self) -> bool:
        """Validate signals data"""
        if not super().validate():
            return False

        # Validate signal structure
        for i, signal in enumerate(self.signals):
            if not isinstance(signal, dict):
                logger.error(f"Signal {i} is not a dict: {type(signal)}")
                return False

            if 'symbol' not in signal:
                logger.error(f"Signal {i} missing 'symbol' field")
                return False

            # Validate confluence score range
            score = signal.get('confluence_score', signal.get('score', 50))
            if not 0 <= score <= 100:
                logger.warning(f"Signal {i} ({signal.get('symbol')}) has invalid score: {score}")

        return True

    def get_top_signals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top N signals by confluence score

        Args:
            limit: Maximum number of signals to return

        Returns:
            List of top signals sorted by score descending
        """
        sorted_signals = sorted(
            self.signals,
            key=lambda s: s.get('confluence_score', s.get('score', 0)),
            reverse=True
        )
        return sorted_signals[:limit]

    def get_signals_by_sentiment(self, sentiment: str) -> List[Dict[str, Any]]:
        """
        Filter signals by sentiment

        Args:
            sentiment: 'BULLISH', 'BEARISH', or 'NEUTRAL'

        Returns:
            List of signals matching the sentiment
        """
        return [
            s for s in self.signals
            if s.get('sentiment', '').upper() == sentiment.upper()
        ]
