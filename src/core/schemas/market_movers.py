"""
Market Movers Schema
====================

Unified contract for market:movers cache key.

Tracks top gainers, losers, and volume leaders.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
import logging
from .base import CacheSchema, SchemaVersion

logger = logging.getLogger(__name__)


@dataclass
class MarketMoversSchema(CacheSchema):
    """
    Market movers data schema

    Tracks the best and worst performing symbols, plus volume leaders.

    Fields:
        gainers: Top gaining symbols with positive price change
        losers: Top losing symbols with negative price change
        volume_leaders: Symbols with highest trading volume

    Aliases (for backward compatibility):
        top_gainers: Alias for gainers
        top_losers: Alias for losers
    """

    # Class constants
    CACHE_KEY = "market:movers"
    VERSION = SchemaVersion.V1

    # Primary data
    gainers: List[Dict[str, Any]] = field(default_factory=list)
    losers: List[Dict[str, Any]] = field(default_factory=list)
    volume_leaders: List[Dict[str, Any]] = field(default_factory=list)

    # Aliases for backward compatibility
    top_gainers: List[Dict[str, Any]] = field(default_factory=list)
    top_losers: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """Set up aliases"""
        # Sync aliases with primary fields
        if not self.top_gainers and self.gainers:
            self.top_gainers = self.gainers
        if not self.top_losers and self.losers:
            self.top_losers = self.losers

        # Sync primary fields from aliases if needed
        if not self.gainers and self.top_gainers:
            self.gainers = self.top_gainers
        if not self.losers and self.top_losers:
            self.losers = self.top_losers

    def validate(self) -> bool:
        """Validate market movers data"""
        if not super().validate():
            return False

        # Validate each gainer has required fields
        for i, gainer in enumerate(self.gainers):
            if not isinstance(gainer, dict):
                logger.error(f"Gainer {i} is not a dict")
                return False
            if 'symbol' not in gainer:
                logger.error(f"Gainer {i} missing 'symbol' field")
                return False

        # Validate each loser has required fields
        for i, loser in enumerate(self.losers):
            if not isinstance(loser, dict):
                logger.error(f"Loser {i} is not a dict")
                return False
            if 'symbol' not in loser:
                logger.error(f"Loser {i} missing 'symbol' field")
                return False

        return True

    def get_top_gainers(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top N gainers"""
        return self.gainers[:limit]

    def get_top_losers(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top N losers"""
        return self.losers[:limit]
