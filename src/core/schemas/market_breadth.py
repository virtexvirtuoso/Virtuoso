"""
Market Breadth Schema
=====================

Unified contract for market:breadth cache key.

Tracks how many symbols are moving up vs down.
"""

from dataclasses import dataclass
import logging
from .base import CacheSchema, SchemaVersion

logger = logging.getLogger(__name__)


@dataclass
class MarketBreadthSchema(CacheSchema):
    """
    Market breadth data schema

    Tracks the number of symbols moving in each direction to gauge
    overall market sentiment and participation.

    Fields:
        up_count: Number of symbols with positive price change
        down_count: Number of symbols with negative price change
        flat_count: Number of symbols with no change
        breadth_percentage: Percentage of symbols moving up (0-100)
        market_sentiment: Overall sentiment based on breadth
    """

    # Class constants
    CACHE_KEY = "market:breadth"
    VERSION = SchemaVersion.V1

    # Symbol counts by direction
    up_count: int = 0
    down_count: int = 0
    flat_count: int = 0

    # Calculated metrics
    breadth_percentage: float = 50.0  # 0-100
    market_sentiment: str = "neutral"  # bullish, bearish, neutral

    def __post_init__(self):
        """Calculate breadth percentage and sentiment from counts"""
        total = self.up_count + self.down_count

        if total > 0:
            # Calculate breadth percentage
            self.breadth_percentage = (self.up_count / total) * 100

            # Determine sentiment
            if self.breadth_percentage >= 60:
                self.market_sentiment = "bullish"
            elif self.breadth_percentage <= 40:
                self.market_sentiment = "bearish"
            else:
                self.market_sentiment = "neutral"

    def validate(self) -> bool:
        """Validate market breadth data"""
        if not super().validate():
            return False

        # Ensure counts are non-negative
        if self.up_count < 0 or self.down_count < 0 or self.flat_count < 0:
            logger.error("Market breadth counts cannot be negative")
            return False

        # Ensure breadth percentage in valid range
        if not 0 <= self.breadth_percentage <= 100:
            logger.warning(
                f"breadth_percentage out of range [0-100]: {self.breadth_percentage}"
            )
            return False

        return True

    def get_total_symbols(self) -> int:
        """Get total number of symbols tracked"""
        return self.up_count + self.down_count + self.flat_count
