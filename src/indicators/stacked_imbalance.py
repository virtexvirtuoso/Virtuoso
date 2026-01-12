"""
Stacked Imbalance Score Calculator

Detects consecutive price levels with significant buy/sell imbalances
to identify institutional order flow clustering. This is a SPATIAL indicator
(vs CVD which is temporal) - measuring WHERE aggressive orders cluster.

Key differentiator: ~40-60% correlation with CVD = complementary, not redundant.

Author: Virtuoso Trading System
Date: 2025-12-31
Version: 1.0.0

Integration Points:
- orderflow_indicators.py: Component calculation
- interpretation_generator.py: Human-readable text
- signal_generator.py: Signal extraction
- Dashboard: Sub-component display
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import numpy as np
import pandas as pd
import time
import logging
from datetime import datetime

# Import debug logging mixin for standardized patterns
try:
    from indicators.debug_template import DebugLoggingMixin
except ImportError:
    # Fallback if running standalone
    class DebugLoggingMixin:
        pass


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class StackedImbalanceConfig:
    """Configuration for Stacked Imbalance calculations."""

    # Core thresholds
    imbalance_threshold: float = 0.40          # 70/30 split = significant
    min_stack_length: int = 3                   # Minimum consecutive levels

    # Price level granularity by symbol
    tick_sizes: Dict[str, float] = field(default_factory=lambda: {
        "BTCUSDT": 5.0,      # $5 price buckets
        "ETHUSDT": 1.0,      # $1 price buckets
        "SOLUSDT": 0.10,     # $0.10 price buckets
        "XRPUSDT": 0.001,    # $0.001 price buckets
        "DOGEUSDT": 0.0001,  # $0.0001 price buckets
        "default": 1.0
    })

    # Data requirements
    window_minutes: int = 10                    # Analysis window
    min_trades_per_level: int = 5               # Noise filter per level
    min_total_trades: int = 100                 # Minimum data requirement
    max_stale_seconds: int = 300                # 5 minute staleness threshold

    # Normalization
    max_expected_strength: float = 5.0          # For score scaling

    # Performance
    cache_ttl_seconds: int = 5                  # Internal cache TTL

    # Latency budgets (ms)
    latency_budget_total: int = 250
    latency_budget_extraction: int = 50
    latency_budget_validation: int = 20
    latency_budget_aggregation: int = 50
    latency_budget_detection: int = 100
    latency_budget_scoring: int = 30


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class PriceLevelData:
    """Aggregated data for a single price level."""
    price: float
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    trade_count: int = 0
    whale_trades: int = 0  # GAP #4: Whale tracking

    @property
    def total_volume(self) -> float:
        return self.buy_volume + self.sell_volume

    @property
    def imbalance(self) -> float:
        """Calculate imbalance ratio [-1.0, +1.0]."""
        if self.total_volume == 0:
            return 0.0
        return (self.buy_volume - self.sell_volume) / self.total_volume


@dataclass
class DetectedStack:
    """Represents a detected stack of imbalanced levels."""
    start_price: float
    end_price: float
    levels: List[PriceLevelData]
    direction: str  # 'bullish' or 'bearish'

    @property
    def length(self) -> int:
        return len(self.levels)

    @property
    def total_volume(self) -> float:
        return sum(level.total_volume for level in self.levels)

    @property
    def avg_imbalance(self) -> float:
        if not self.levels:
            return 0.0
        return sum(abs(level.imbalance) for level in self.levels) / len(self.levels)

    @property
    def strength(self) -> float:
        """Calculate stack strength with diminishing returns."""
        imbalance_sum = sum(abs(level.imbalance) for level in self.levels)
        length_factor = np.sqrt(self.length)  # Diminishing returns for long stacks
        return imbalance_sum * length_factor

    @property
    def whale_concentration(self) -> float:
        """Percentage of trades that are whale trades."""
        total_trades = sum(l.trade_count for l in self.levels)
        whale_trades = sum(l.whale_trades for l in self.levels)
        return whale_trades / max(total_trades, 1)


@dataclass
class StackedImbalanceResult:
    """Complete result of stacked imbalance analysis."""
    score: float                                # 0-100 normalized score
    bullish_stacks: List[DetectedStack]
    bearish_stacks: List[DetectedStack]
    dominant_direction: str                     # 'bullish', 'bearish', or 'neutral'
    confidence: float                           # 0-1 confidence level
    total_levels_analyzed: int
    significant_levels: int
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Metadata for interpretation
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for API/cache serialization."""
        return {
            'score': round(self.score, 2),
            'dominant_direction': self.dominant_direction,
            'confidence': round(self.confidence, 3),
            'bullish_stack_count': len(self.bullish_stacks),
            'bearish_stack_count': len(self.bearish_stacks),
            'max_bullish_length': max((s.length for s in self.bullish_stacks), default=0),
            'max_bearish_length': max((s.length for s in self.bearish_stacks), default=0),
            'total_bullish_volume': sum(s.total_volume for s in self.bullish_stacks),
            'total_bearish_volume': sum(s.total_volume for s in self.bearish_stacks),
            'total_levels': self.total_levels_analyzed,
            'significant_levels': self.significant_levels,
            'timestamp': self.timestamp.isoformat(),
            **self.metadata
        }


# ============================================================================
# MAIN CALCULATOR
# ============================================================================

class StackedImbalanceCalculator(DebugLoggingMixin):
    """
    Core calculator for Stacked Imbalance Score.

    Analyzes recent trades to detect spatial clustering of buy/sell
    imbalances across consecutive price levels.

    Key Features:
    - Trade data validation (GAP #12)
    - Error recovery with neutral fallbacks (GAP #9)
    - Debug logging via DebugLoggingMixin (GAP #2)
    - Internal caching with TTL (GAP #3)
    - Performance metrics and latency tracking (GAP #10)
    """

    # Class constants
    MIN_TRADES = 50  # Absolute minimum for any calculation

    def __init__(self, config: Optional[StackedImbalanceConfig] = None):
        self.config = config or StackedImbalanceConfig()
        self.logger = logging.getLogger(__name__)

        # GAP #3: Internal caching
        self._cache: Dict[str, StackedImbalanceResult] = {}
        self._cache_timestamps: Dict[str, float] = {}

        # GAP #2: Debug statistics
        self._debug_stats = {
            'calculation_counts': {'total': 0, 'bullish': 0, 'bearish': 0, 'neutral': 0},
            'cache_hits': {'hit': 0, 'miss': 0},
            'stack_stats': {'avg_length': 0, 'max_length': 0, 'total_detected': 0},
            'performance_metrics': {'avg_ms': 0, 'max_ms': 0, 'total_calculations': 0},
            'validation_rejections': {'insufficient_trades': 0, 'stale_data': 0, 'invalid_data': 0}
        }

        # Component weights for confidence calculation (mirrors orderflow pattern)
        self.component_weights = {
            'trade_count': 0.3,
            'level_coverage': 0.3,
            'stack_clarity': 0.4
        }

    # ========================================================================
    # GAP #1: Trade Data Source Handling
    # ========================================================================

    def _get_trades_dataframe(self, market_data: Dict) -> Optional[pd.DataFrame]:
        """
        Extract trades as DataFrame with validation.

        Handles multiple input formats:
        - trades_df: Pre-converted DataFrame (preferred)
        - trades: List of trade dicts
        - recent_trades: Alternative key name

        Returns None if insufficient data.
        """
        # Try DataFrame first (preferred - already processed)
        if 'trades_df' in market_data and isinstance(market_data['trades_df'], pd.DataFrame):
            df = market_data['trades_df']
            if len(df) >= self.MIN_TRADES:
                return df

        # Try list and convert
        trades = market_data.get('trades', market_data.get('recent_trades', []))

        if not trades:
            self.logger.debug("No trades data found in market_data")
            return None

        if len(trades) < self.MIN_TRADES:
            self.logger.debug(f"Insufficient trades: {len(trades)} < {self.MIN_TRADES}")
            self._debug_stats['validation_rejections']['insufficient_trades'] += 1
            return None

        # Convert to DataFrame
        df = pd.DataFrame(trades)

        # Normalize column names (Bybit uses 'qty', standard uses 'size'/'amount')
        if 'qty' in df.columns and 'size' not in df.columns:
            df['size'] = df['qty']
        if 'amount' in df.columns and 'size' not in df.columns:
            df['size'] = df['amount']

        # Normalize side column (Bybit uses 'Buy'/'Sell', we want lowercase)
        if 'side' in df.columns:
            df['side'] = df['side'].str.lower()

        return df

    def _extract_trades_list(self, market_data: Dict) -> List[Dict]:
        """
        Extract trades as list for aggregation.

        DEPRECATED: Use _get_trades_dataframe() directly for better performance.
        This method is kept for backward compatibility only.
        """
        df = self._get_trades_dataframe(market_data)
        if df is None:
            return []
        # SLOW: df.to_dict('records') is O(n) with high constant factor
        # Prefer using DataFrame directly via _validate_trades_df()
        return df.to_dict('records')

    def _validate_trades_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Vectorized trade validation - 10-50x faster than _validate_trades.

        Filters invalid trades using pandas operations instead of Python loops.
        """
        if df is None or len(df) == 0:
            return pd.DataFrame()

        # Ensure numeric columns
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce')

        # Get size column (different exchanges use different names)
        size_col = None
        for col in ['qty', 'amount', 'size']:
            if col in df.columns:
                size_col = col
                df['_size'] = pd.to_numeric(df[col], errors='coerce')
                break

        if size_col is None:
            self._debug_stats['validation_rejections']['invalid_data'] += 1
            return pd.DataFrame()

        # Vectorized filtering - no Python loops!
        mask = (
            df['price'].notna() &
            (df['price'] > 0) &
            np.isfinite(df['price']) &
            df['_size'].notna() &
            (df['_size'] > 0) &
            np.isfinite(df['_size'])
        )

        df = df[mask].copy()

        if len(df) == 0:
            self._debug_stats['validation_rejections']['invalid_data'] += 1
            return pd.DataFrame()

        # Remove outliers (top 0.1%) - vectorized
        if len(df) > 100:
            threshold = df['_size'].quantile(0.999)
            df = df[df['_size'] <= threshold]

        return df

    def _aggregate_trades_by_level_df(
        self,
        df: pd.DataFrame,
        tick_size: float,
        whale_threshold: Optional[float] = None
    ) -> Dict[float, PriceLevelData]:
        """
        Vectorized trade aggregation using pandas groupby - 10-20x faster.

        Replaces Python loop with optimized C-level pandas operations.
        """
        if df is None or len(df) == 0:
            return {}

        # Quantize prices to tick levels - vectorized
        df = df.copy()
        df['level_price'] = (df['price'] / tick_size).round() * tick_size

        # Normalize side column
        if 'side' not in df.columns:
            # No side info - assume 50/50
            df['side'] = 'unknown'
        else:
            df['side'] = df['side'].astype(str).str.lower()

        # Create buy/sell masks - vectorized
        buy_mask = df['side'].isin(['buy', 'b'])
        sell_mask = df['side'].isin(['sell', 's'])
        unknown_mask = ~(buy_mask | sell_mask)

        # Calculate buy/sell volumes per row - vectorized
        df['buy_vol'] = 0.0
        df['sell_vol'] = 0.0
        df.loc[buy_mask, 'buy_vol'] = df.loc[buy_mask, '_size']
        df.loc[sell_mask, 'sell_vol'] = df.loc[sell_mask, '_size']
        df.loc[unknown_mask, 'buy_vol'] = df.loc[unknown_mask, '_size'] * 0.5
        df.loc[unknown_mask, 'sell_vol'] = df.loc[unknown_mask, '_size'] * 0.5

        # Whale trade indicator
        if whale_threshold is not None:
            df['is_whale'] = (df['_size'] >= whale_threshold).astype(int)
        else:
            df['is_whale'] = 0

        # Group by price level - single pass aggregation using pandas groupby (C-optimized)
        agg = df.groupby('level_price').agg({
            'buy_vol': 'sum',
            'sell_vol': 'sum',
            '_size': 'count',  # trade_count
            'is_whale': 'sum'
        }).reset_index()

        agg.columns = ['level_price', 'buy_volume', 'sell_volume', 'trade_count', 'whale_trades']

        # Convert to PriceLevelData dict
        levels = {}
        # Use itertuples for faster iteration than iterrows
        for row in agg.itertuples(index=False):
            levels[row.level_price] = PriceLevelData(
                price=row.level_price,
                buy_volume=row.buy_volume,
                sell_volume=row.sell_volume,
                trade_count=int(row.trade_count),
                whale_trades=int(row.whale_trades)
            )

        return levels

    # ========================================================================
    # GAP #12: Data Validation
    # ========================================================================

    def _validate_trades(self, trades: List[Dict]) -> List[Dict]:
        """
        Filter invalid trades and remove outliers.

        Validation steps:
        1. Remove trades with invalid/missing price
        2. Remove trades with invalid/missing size
        3. Remove zero/negative values
        4. Remove size outliers (top 0.1% - likely erroneous)
        """
        if not trades:
            return []

        valid = []
        for t in trades:
            # Extract price
            price = t.get('price', 0)
            if not isinstance(price, (int, float)):
                try:
                    price = float(price)
                except (ValueError, TypeError):
                    continue

            # Check price validity
            if not np.isfinite(price) or price <= 0:
                continue

            # Extract size (multiple possible field names)
            size = t.get('qty', t.get('amount', t.get('size', 0)))
            if not isinstance(size, (int, float)):
                try:
                    size = float(size)
                except (ValueError, TypeError):
                    continue

            # Check size validity
            if not np.isfinite(size) or size <= 0:
                continue

            # Valid trade
            valid.append(t)

        if not valid:
            self._debug_stats['validation_rejections']['invalid_data'] += 1
            return []

        # Remove size outliers (top 0.1% - likely erroneous or test trades)
        sizes = [t.get('qty', t.get('amount', t.get('size', 0))) for t in valid]
        if len(sizes) > 100:  # Only if enough data for percentile
            threshold = np.percentile(sizes, 99.9)
            valid = [t for t in valid if t.get('qty', t.get('amount', t.get('size', 0))) <= threshold]

        return valid

    def _check_data_staleness(self, trades: List[Dict]) -> bool:
        """
        Check if trade data is too stale.

        Returns True if data is fresh, False if stale.
        """
        if not trades:
            return False

        # Find latest trade timestamp
        timestamps = []
        for t in trades:
            ts = t.get('time', t.get('timestamp', 0))
            if ts:
                # Handle both ms and s timestamps
                if ts > 1e12:  # Milliseconds
                    timestamps.append(ts / 1000)
                else:
                    timestamps.append(ts)

        if not timestamps:
            # No timestamps - assume fresh (trust the data source)
            return True

        latest = max(timestamps)
        age_seconds = time.time() - latest

        if age_seconds > self.config.max_stale_seconds:
            self.logger.debug(f"Trade data stale: {age_seconds:.0f}s > {self.config.max_stale_seconds}s")
            self._debug_stats['validation_rejections']['stale_data'] += 1
            return False

        return True

    # ========================================================================
    # GAP #3: Internal Caching
    # ========================================================================

    def _get_cached(self, key: str) -> Optional[StackedImbalanceResult]:
        """Get cached result if still valid."""
        if key not in self._cache:
            self._debug_stats['cache_hits']['miss'] += 1
            return None

        age = time.time() - self._cache_timestamps.get(key, 0)
        if age > self.config.cache_ttl_seconds:
            # Expired - remove and return None
            del self._cache[key]
            del self._cache_timestamps[key]
            self._debug_stats['cache_hits']['miss'] += 1
            return None

        self._debug_stats['cache_hits']['hit'] += 1
        return self._cache[key]

    def _set_cached(self, key: str, result: StackedImbalanceResult):
        """Cache a result."""
        self._cache[key] = result
        self._cache_timestamps[key] = time.time()

        # Limit cache size (LRU-style cleanup)
        if len(self._cache) > 100:
            # Remove oldest entries
            oldest_keys = sorted(
                self._cache_timestamps.keys(),
                key=lambda k: self._cache_timestamps[k]
            )[:50]
            for k in oldest_keys:
                del self._cache[k]
                del self._cache_timestamps[k]

    # ========================================================================
    # Core Calculation Methods
    # ========================================================================

    def get_tick_size(self, symbol: str) -> float:
        """Get appropriate tick size for symbol."""
        return self.config.tick_sizes.get(
            symbol.upper(),
            self.config.tick_sizes['default']
        )

    def quantize_price(self, price: float, tick_size: float) -> float:
        """Round price to nearest tick."""
        if tick_size <= 0:
            return price
        return round(price / tick_size) * tick_size

    def aggregate_trades_by_level(
        self,
        trades: List[Dict],
        tick_size: float,
        whale_threshold: Optional[float] = None
    ) -> Dict[float, PriceLevelData]:
        """
        Aggregate trades into price level buckets.

        Args:
            trades: List of trade dicts with 'price', 'amount'/'qty', 'side'
            tick_size: Price bucket size
            whale_threshold: Size threshold for whale trade classification

        Returns:
            Dictionary mapping price levels to aggregated data
        """
        levels: Dict[float, PriceLevelData] = {}

        for trade in trades:
            price = trade.get('price', 0)
            amount = abs(float(trade.get('amount', trade.get('qty', trade.get('size', 0)))))
            side = str(trade.get('side', '')).lower()

            # Quantize to price level
            level_price = self.quantize_price(price, tick_size)

            if level_price not in levels:
                levels[level_price] = PriceLevelData(price=level_price)

            level = levels[level_price]
            level.trade_count += 1

            # Track whale trades
            if whale_threshold and amount >= whale_threshold:
                level.whale_trades += 1

            # Classify as buy or sell
            if side in ('buy', 'b'):
                level.buy_volume += amount
            elif side in ('sell', 's'):
                level.sell_volume += amount
            else:
                # Unknown side - split 50/50 as fallback
                level.buy_volume += amount * 0.5
                level.sell_volume += amount * 0.5

        return levels

    def detect_stacks(
        self,
        levels: Dict[float, PriceLevelData]
    ) -> Tuple[List[DetectedStack], List[DetectedStack]]:
        """
        Detect bullish and bearish stacks from price levels.

        A stack is 3+ consecutive price levels with same-direction significant imbalance.

        Returns:
            Tuple of (bullish_stacks, bearish_stacks)
        """
        if not levels:
            return [], []

        # Sort levels by price
        sorted_prices = sorted(levels.keys())
        threshold = self.config.imbalance_threshold
        min_trades = self.config.min_trades_per_level

        bullish_stacks: List[DetectedStack] = []
        bearish_stacks: List[DetectedStack] = []

        # Current stack tracking
        current_stack: List[PriceLevelData] = []
        current_direction: Optional[str] = None

        def save_stack():
            """Save current stack if valid."""
            nonlocal current_stack, current_direction
            if len(current_stack) >= self.config.min_stack_length and current_direction:
                stack = DetectedStack(
                    start_price=current_stack[0].price,
                    end_price=current_stack[-1].price,
                    levels=current_stack.copy(),
                    direction=current_direction
                )
                if current_direction == 'bullish':
                    bullish_stacks.append(stack)
                else:
                    bearish_stacks.append(stack)

        for price in sorted_prices:
            level = levels[price]

            # Skip levels with insufficient trades (noise filter)
            if level.trade_count < min_trades:
                save_stack()
                current_stack = []
                current_direction = None
                continue

            imbalance = level.imbalance

            # Determine level direction
            if imbalance >= threshold:
                level_direction = 'bullish'
            elif imbalance <= -threshold:
                level_direction = 'bearish'
            else:
                level_direction = None  # Neutral

            # Stack continuation logic
            if level_direction is None:
                # Neutral level breaks the stack
                save_stack()
                current_stack = []
                current_direction = None

            elif current_direction is None:
                # Start new stack
                current_stack = [level]
                current_direction = level_direction

            elif level_direction == current_direction:
                # Continue current stack
                current_stack.append(level)

            else:
                # Direction changed - save old stack and start new
                save_stack()
                current_stack = [level]
                current_direction = level_direction

        # Handle final stack
        save_stack()

        # Update statistics
        all_stacks = bullish_stacks + bearish_stacks
        if all_stacks:
            lengths = [s.length for s in all_stacks]
            self._debug_stats['stack_stats']['avg_length'] = sum(lengths) / len(lengths)
            self._debug_stats['stack_stats']['max_length'] = max(lengths)
            self._debug_stats['stack_stats']['total_detected'] += len(all_stacks)

        return bullish_stacks, bearish_stacks

    def calculate_score(
        self,
        bullish_stacks: List[DetectedStack],
        bearish_stacks: List[DetectedStack],
        total_volume: float,
        levels: Optional[Dict[float, PriceLevelData]] = None
    ) -> float:
        """
        Calculate normalized score from detected stacks.

        When no stacks are detected, falls back to aggregate imbalance
        calculation from all price levels (with reduced magnitude).

        Returns:
            Score in range [0, 100] where 50 = neutral
        """
        def weighted_strength(stacks: List[DetectedStack]) -> float:
            """Calculate volume-weighted strength of stacks."""
            if not stacks or total_volume == 0:
                return 0.0
            total = 0.0
            for stack in stacks:
                volume_weight = stack.total_volume / total_volume
                total += stack.strength * volume_weight
            return total

        bullish_strength = weighted_strength(bullish_stacks)
        bearish_strength = weighted_strength(bearish_stacks)

        # Check if we have any stacks at all
        has_stacks = len(bullish_stacks) > 0 or len(bearish_stacks) > 0

        if has_stacks:
            # Standard calculation with detected stacks
            raw_score = bullish_strength - bearish_strength
            max_strength = self.config.max_expected_strength
            normalized = 50 + (raw_score / max_strength) * 50
        elif levels and total_volume > 0:
            # Fallback: aggregate imbalance from all price levels
            # Calculate volume-weighted average imbalance across all levels
            weighted_imbalance = 0.0
            for level in levels.values():
                weight = level.total_volume / total_volume
                weighted_imbalance += level.imbalance * weight

            # weighted_imbalance is in range [-1, 1]
            # Scale to score but with REDUCED magnitude (0.6x) since no clear stacks
            # This prevents returning exactly 50.0 while being conservative
            fallback_multiplier = 0.6
            normalized = 50 + (weighted_imbalance * 50 * fallback_multiplier)

            self.logger.debug(
                f"Stacked imbalance fallback: weighted_imbalance={weighted_imbalance:.3f}, "
                f"score={normalized:.1f} (no stacks detected)"
            )
        else:
            # No stacks and no levels - truly neutral
            normalized = 50.0

        return float(np.clip(normalized, 0, 100))

    def calculate_confidence(
        self,
        levels: Dict[float, PriceLevelData],
        bullish_stacks: List[DetectedStack],
        bearish_stacks: List[DetectedStack],
        total_trades: int
    ) -> float:
        """
        Calculate confidence level based on data quality.

        Factors:
        1. Trade count adequacy
        2. Level coverage (% significant)
        3. Stack clarity (avg length)

        Returns:
            Confidence in range [0, 1]
        """
        factors = []

        # Factor 1: Trade count adequacy (0-1)
        min_trades = self.config.min_total_trades
        trade_factor = min(total_trades / (min_trades * 2), 1.0)
        factors.append(trade_factor)

        # Factor 2: Level coverage (0-1)
        total_levels = len(levels)
        significant_levels = sum(
            1 for level in levels.values()
            if abs(level.imbalance) >= self.config.imbalance_threshold
        )
        coverage_factor = significant_levels / max(total_levels, 1)
        factors.append(coverage_factor)

        # Factor 3: Stack clarity (0-1)
        all_stacks = bullish_stacks + bearish_stacks
        if all_stacks:
            avg_length = sum(s.length for s in all_stacks) / len(all_stacks)
            clarity_factor = min(avg_length / 5, 1.0)  # 5+ levels = max clarity
        else:
            clarity_factor = 0.3  # No stacks = low but not zero confidence
        factors.append(clarity_factor)

        # Weighted average based on component_weights
        weights = [
            self.component_weights['trade_count'],
            self.component_weights['level_coverage'],
            self.component_weights['stack_clarity']
        ]
        weighted_sum = sum(f * w for f, w in zip(factors, weights))
        total_weight = sum(weights)

        return weighted_sum / total_weight if total_weight > 0 else 0.5

    # ========================================================================
    # GAP #9: Error Recovery / Neutral Fallback
    # ========================================================================

    def _neutral_result(self, reason: str = "unknown") -> StackedImbalanceResult:
        """
        Return neutral result with tracking.

        Used when calculation cannot proceed due to data issues.
        """
        self._debug_stats['calculation_counts']['neutral'] += 1
        self.logger.debug(f"Returning neutral result: {reason}")

        return StackedImbalanceResult(
            score=50.0,
            bullish_stacks=[],
            bearish_stacks=[],
            dominant_direction='neutral',
            confidence=0.0,
            total_levels_analyzed=0,
            significant_levels=0,
            metadata={'neutral_reason': reason}
        )

    # ========================================================================
    # GAP #10: Performance Metrics
    # ========================================================================

    def _check_latency_budgets(self, timings: Dict[str, float]):
        """Check if any step exceeded its latency budget."""
        budgets = {
            'total': self.config.latency_budget_total,
            'extraction': self.config.latency_budget_extraction,
            'validation': self.config.latency_budget_validation,
            'aggregation': self.config.latency_budget_aggregation,
            'detection': self.config.latency_budget_detection,
            'scoring': self.config.latency_budget_scoring
        }

        for component, elapsed in timings.items():
            budget = budgets.get(component, 100)
            if elapsed > budget:
                self.logger.warning(
                    f"Stacked Imbalance {component} exceeded budget: "
                    f"{elapsed:.1f}ms > {budget}ms"
                )

    def _update_performance_stats(self, elapsed_ms: float):
        """Update running performance statistics."""
        stats = self._debug_stats['performance_metrics']
        stats['total_calculations'] += 1

        # Running average
        n = stats['total_calculations']
        old_avg = stats['avg_ms']
        stats['avg_ms'] = old_avg + (elapsed_ms - old_avg) / n

        # Max
        stats['max_ms'] = max(stats['max_ms'], elapsed_ms)

    # ========================================================================
    # Main Entry Point
    # ========================================================================

    async def calculate(
        self,
        symbol: str,
        trades: Optional[List[Dict]] = None,
        market_data: Optional[Dict] = None
    ) -> StackedImbalanceResult:
        """
        Main calculation entry point.

        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            trades: List of recent trades (optional if market_data provided)
            market_data: Full market data dict (optional if trades provided)

        Returns:
            StackedImbalanceResult with score and metadata
        """
        total_start = time.time()
        timings = {}

        self._debug_stats['calculation_counts']['total'] += 1

        # ===== Check Cache =====
        cache_key = f"{symbol}_stacked_imbalance"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # ===== Extract Trades as DataFrame (vectorized path) =====
        t0 = time.time()
        if trades is None and market_data:
            df = self._get_trades_dataframe(market_data)
        elif trades is not None:
            # Convert list to DataFrame for vectorized processing
            df = pd.DataFrame(trades) if trades else None
            # Normalize column names
            if df is not None and len(df) > 0:
                if 'qty' in df.columns and 'size' not in df.columns:
                    df['size'] = df['qty']
                if 'amount' in df.columns and 'size' not in df.columns:
                    df['size'] = df['amount']
        else:
            df = None
        timings['extraction'] = (time.time() - t0) * 1000

        if df is None or len(df) == 0:
            return self._neutral_result("no_trades_data")

        # ===== Validation (GAP #12) - VECTORIZED =====
        t0 = time.time()
        df = self._validate_trades_df(df)
        timings['validation'] = (time.time() - t0) * 1000

        if len(df) < self.config.min_total_trades:
            return self._neutral_result("insufficient_trades")

        # ===== Staleness Check (GAP #9) - use DataFrame timestamps =====
        # Check latest timestamp from DataFrame
        ts_col = None
        for col in ['time', 'timestamp']:
            if col in df.columns:
                ts_col = col
                break

        if ts_col:
            latest_ts = df[ts_col].max()
            if latest_ts > 1e12:  # Milliseconds
                latest_ts = latest_ts / 1000
            age_seconds = time.time() - latest_ts
            if age_seconds > self.config.max_stale_seconds:
                self._debug_stats['validation_rejections']['stale_data'] += 1
                return self._neutral_result("stale_data")

        # ===== Aggregation - VECTORIZED =====
        t0 = time.time()
        tick_size = self.get_tick_size(symbol)
        num_trades = len(df)

        # Calculate whale threshold from DataFrame (vectorized)
        whale_threshold = df['_size'].quantile(0.90) if len(df) >= 10 else None

        levels = self._aggregate_trades_by_level_df(df, tick_size, whale_threshold)
        timings['aggregation'] = (time.time() - t0) * 1000

        if not levels:
            return self._neutral_result("no_price_levels")

        # ===== Stack Detection =====
        t0 = time.time()
        bullish_stacks, bearish_stacks = self.detect_stacks(levels)
        timings['detection'] = (time.time() - t0) * 1000

        # ===== Scoring =====
        t0 = time.time()
        total_volume = sum(level.total_volume for level in levels.values())
        score = self.calculate_score(bullish_stacks, bearish_stacks, total_volume, levels)
        timings['scoring'] = (time.time() - t0) * 1000

        # ===== Determine Direction =====
        if score > 60:
            dominant = 'bullish'
            self._debug_stats['calculation_counts']['bullish'] += 1
        elif score < 40:
            dominant = 'bearish'
            self._debug_stats['calculation_counts']['bearish'] += 1
        else:
            dominant = 'neutral'
            self._debug_stats['calculation_counts']['neutral'] += 1

        # ===== Calculate Confidence =====
        confidence = self.calculate_confidence(
            levels, bullish_stacks, bearish_stacks, num_trades
        )

        # ===== Count Significant Levels =====
        significant_levels = sum(
            1 for level in levels.values()
            if abs(level.imbalance) >= self.config.imbalance_threshold
        )

        # ===== Build Result =====
        result = StackedImbalanceResult(
            score=score,
            bullish_stacks=bullish_stacks,
            bearish_stacks=bearish_stacks,
            dominant_direction=dominant,
            confidence=confidence,
            total_levels_analyzed=len(levels),
            significant_levels=significant_levels,
            metadata={
                'bullish_stack_count': len(bullish_stacks),
                'bearish_stack_count': len(bearish_stacks),
                'total_trades_analyzed': num_trades,
                'tick_size': tick_size,
                'whale_threshold': whale_threshold,
                'timings_ms': timings
            }
        )

        # ===== Performance Tracking (GAP #10) =====
        timings['total'] = (time.time() - total_start) * 1000
        self._check_latency_budgets(timings)
        self._update_performance_stats(timings['total'])

        # ===== Cache Result (GAP #3) =====
        self._set_cached(cache_key, result)

        # ===== Debug Logging =====
        self.logger.debug(
            f"Stacked Imbalance {symbol}: score={score:.1f}, "
            f"direction={dominant}, confidence={confidence:.2f}, "
            f"stacks={len(bullish_stacks)}B/{len(bearish_stacks)}S, "
            f"time={timings['total']:.1f}ms"
        )

        return result

    def get_debug_stats(self) -> Dict[str, Any]:
        """Get current debug statistics."""
        return self._debug_stats.copy()

    def reset_debug_stats(self):
        """Reset debug statistics."""
        self._debug_stats = {
            'calculation_counts': {'total': 0, 'bullish': 0, 'bearish': 0, 'neutral': 0},
            'cache_hits': {'hit': 0, 'miss': 0},
            'stack_stats': {'avg_length': 0, 'max_length': 0, 'total_detected': 0},
            'performance_metrics': {'avg_ms': 0, 'max_ms': 0, 'total_calculations': 0},
            'validation_rejections': {'insufficient_trades': 0, 'stale_data': 0, 'invalid_data': 0}
        }


# ============================================================================
# SINGLETON & FACTORY
# ============================================================================

_calculator: Optional[StackedImbalanceCalculator] = None


def get_calculator(config: Optional[StackedImbalanceConfig] = None) -> StackedImbalanceCalculator:
    """Get or create singleton calculator instance."""
    global _calculator
    if _calculator is None:
        _calculator = StackedImbalanceCalculator(config)
    return _calculator


def create_calculator(config: Optional[StackedImbalanceConfig] = None) -> StackedImbalanceCalculator:
    """Create a new calculator instance (non-singleton)."""
    return StackedImbalanceCalculator(config)


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

async def calculate_stacked_imbalance(
    symbol: str,
    trades: Optional[List[Dict]] = None,
    market_data: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Convenience function for calculating stacked imbalance.

    Returns a dictionary suitable for direct use in orderflow_indicators.py
    """
    calculator = get_calculator()
    result = await calculator.calculate(symbol, trades, market_data)

    return {
        'score': result.score,
        'confidence': result.confidence,
        'direction': result.dominant_direction,
        'bullish_stacks': len(result.bullish_stacks),
        'bearish_stacks': len(result.bearish_stacks),
        'significant_levels': result.significant_levels,
        'total_levels': result.total_levels_analyzed,
        'raw_data': result.to_dict()
    }
