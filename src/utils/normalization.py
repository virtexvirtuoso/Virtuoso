"""
Signal Normalization Utilities for Confluence Analysis

This module provides z-score normalization for trading indicators to ensure
consistent signal comparison and mathematically valid confluence calculations.

Key Features:
- Rolling z-score normalization with Welford's online algorithm
- Efficient memory usage with fixed-size buffers
- Configurable lookback windows per indicator
- Automatic outlier winsorization
- Fallback mechanisms for insufficient data

Usage:
    normalizer = RollingNormalizer(lookback=100)

    for value in data_stream:
        normalizer.update(value)
        normalized = normalizer.normalize(value)
"""

import numpy as np
from collections import deque
from typing import Optional, List, Union, Dict
from dataclasses import dataclass
from enum import Enum


class NormalizationMethod(Enum):
    """Available normalization methods."""
    ZSCORE = "zscore"
    TANH = "tanh"
    MINMAX = "minmax"
    NONE = "none"


@dataclass
class NormalizationConfig:
    """Configuration for indicator-specific normalization."""
    method: NormalizationMethod = NormalizationMethod.ZSCORE
    lookback: int = 100
    min_samples: int = 20
    winsorize_threshold: float = 3.0
    outlier_removal: bool = False

    @classmethod
    def for_accumulative_indicator(cls) -> 'NormalizationConfig':
        """Config optimized for accumulative indicators (CVD, OBV, ADL)."""
        return cls(
            method=NormalizationMethod.ZSCORE,
            lookback=200,
            min_samples=30,
            winsorize_threshold=3.0,
            outlier_removal=False
        )

    @classmethod
    def for_volatile_indicator(cls) -> 'NormalizationConfig':
        """Config optimized for volatile indicators (OI changes, volume spikes)."""
        return cls(
            method=NormalizationMethod.ZSCORE,
            lookback=50,
            min_samples=15,
            winsorize_threshold=3.0,
            outlier_removal=True
        )


class RollingNormalizer:
    """
    Maintains rolling statistics for z-score normalization.

    Uses Welford's online algorithm for numerically stable calculation
    of mean and variance without storing full history.

    Attributes:
        lookback: Number of historical values to consider
        min_samples: Minimum samples required before normalization
        winsorize_threshold: Maximum absolute z-score (clips outliers)

    Example:
        >>> normalizer = RollingNormalizer(lookback=100)
        >>> normalizer.update(42.0)
        >>> z_score = normalizer.normalize(45.0)
        >>> print(f"Z-score: {z_score:.2f}")
    """

    def __init__(
        self,
        lookback: int = 100,
        min_samples: int = 20,
        winsorize_threshold: float = 3.0
    ):
        """
        Initialize rolling normalizer.

        Args:
            lookback: Number of values in rolling window
            min_samples: Minimum samples before normalization activates
            winsorize_threshold: Clip z-scores beyond ±threshold
        """
        if lookback < min_samples:
            raise ValueError(f"lookback ({lookback}) must be >= min_samples ({min_samples})")

        self.lookback = lookback
        self.min_samples = min_samples
        self.winsorize_threshold = winsorize_threshold

        # Rolling buffer for values
        self.values: deque = deque(maxlen=lookback)

        # Welford's algorithm state
        self._count: int = 0
        self._mean: float = 0.0
        self._m2: float = 0.0  # Sum of squared differences from mean

    def update(self, value: float) -> None:
        """
        Update rolling statistics with new value.

        Uses Welford's online algorithm for numerical stability:
        https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance#Welford's_online_algorithm

        Args:
            value: New value to add to rolling window
        """
        # Handle overflow when buffer is full
        if len(self.values) == self.lookback:
            # Remove oldest value's contribution using reverse Welford
            old_value = self.values[0]
            old_delta = old_value - self._mean
            self._mean = (self._mean * self._count - old_value) / (self._count - 1) if self._count > 1 else 0
            new_delta = old_value - self._mean
            self._m2 -= old_delta * new_delta
            self._count -= 1

        # Add new value
        self.values.append(value)
        self._count += 1

        # Welford's update
        delta = value - self._mean
        self._mean += delta / self._count
        delta2 = value - self._mean
        self._m2 += delta * delta2

    def normalize(self, value: float) -> float:
        """
        Normalize value using current rolling statistics.

        Returns z-score: (value - mean) / std
        Winsorized to [-threshold, +threshold] range

        Args:
            value: Value to normalize

        Returns:
            Normalized z-score (typically -3 to +3)
            Returns 0.0 if insufficient samples or zero variance
        """
        if self._count < self.min_samples:
            return 0.0  # Insufficient data

        # Calculate standard deviation
        variance = self._m2 / (self._count - 1) if self._count > 1 else 0
        std = np.sqrt(variance)

        if std < 1e-8:  # Zero variance
            return 0.0

        # Calculate z-score
        z_score = (value - self._mean) / std

        # Winsorize to prevent extreme outliers
        return np.clip(z_score, -self.winsorize_threshold, self.winsorize_threshold)

    @property
    def mean(self) -> float:
        """Current rolling mean."""
        return self._mean

    @property
    def std(self) -> float:
        """Current rolling standard deviation."""
        if self._count < 2:
            return 0.0
        variance = self._m2 / (self._count - 1)
        return np.sqrt(variance)

    @property
    def sample_count(self) -> int:
        """Number of samples in current window."""
        return self._count

    @property
    def is_ready(self) -> bool:
        """Whether normalizer has sufficient samples."""
        return self._count >= self.min_samples

    def reset(self) -> None:
        """Reset normalizer state."""
        self.values.clear()
        self._count = 0
        self._mean = 0.0
        self._m2 = 0.0


class BatchNormalizer:
    """
    Normalize arrays of values using batch z-score calculation.

    Useful for backtesting or processing historical data where
    you have the full dataset upfront.
    """

    @staticmethod
    def normalize(
        values: np.ndarray,
        lookback: int = 100,
        min_samples: int = 20,
        winsorize_threshold: float = 3.0
    ) -> np.ndarray:
        """
        Normalize array using rolling z-score.

        Args:
            values: Array of values to normalize
            lookback: Rolling window size
            min_samples: Minimum samples for normalization
            winsorize_threshold: Clip z-scores beyond ±threshold

        Returns:
            Array of normalized z-scores
        """
        if len(values) < min_samples:
            return np.zeros_like(values)

        # Calculate rolling mean and std
        rolling_mean = np.full_like(values, np.nan, dtype=float)
        rolling_std = np.full_like(values, np.nan, dtype=float)

        for i in range(len(values)):
            start_idx = max(0, i - lookback + 1)
            window = values[start_idx:i+1]

            if len(window) >= min_samples:
                rolling_mean[i] = np.mean(window)
                rolling_std[i] = np.std(window, ddof=1)

        # Calculate z-scores
        z_scores = np.zeros_like(values, dtype=float)
        valid_mask = (~np.isnan(rolling_mean)) & (rolling_std > 1e-8)

        z_scores[valid_mask] = (
            (values[valid_mask] - rolling_mean[valid_mask]) / rolling_std[valid_mask]
        )

        # Winsorize
        z_scores = np.clip(z_scores, -winsorize_threshold, winsorize_threshold)

        return z_scores


class MultiIndicatorNormalizer:
    """
    Manages normalization for multiple indicators with different configs.

    Example:
        >>> normalizer = MultiIndicatorNormalizer()
        >>> normalizer.register_indicator('cvd', NormalizationConfig.for_accumulative_indicator())
        >>> normalizer.update('cvd', 1234.56)
        >>> z_score = normalizer.normalize('cvd', 1250.00)
    """

    def __init__(self):
        """Initialize multi-indicator normalizer."""
        self.normalizers: Dict[str, RollingNormalizer] = {}
        self.configs: Dict[str, NormalizationConfig] = {}

    def register_indicator(
        self,
        name: str,
        config: Optional[NormalizationConfig] = None
    ) -> None:
        """
        Register an indicator for normalization.

        Args:
            name: Indicator name (e.g., 'cvd', 'obv', 'rsi')
            config: Normalization configuration (uses default if None)
        """
        if config is None:
            config = NormalizationConfig()

        self.configs[name] = config

        if config.method == NormalizationMethod.ZSCORE:
            self.normalizers[name] = RollingNormalizer(
                lookback=config.lookback,
                min_samples=config.min_samples,
                winsorize_threshold=config.winsorize_threshold
            )

    def update(self, indicator_name: str, value: float) -> None:
        """
        Update normalizer for specific indicator.

        Args:
            indicator_name: Name of indicator
            value: New value
        """
        if indicator_name in self.normalizers:
            self.normalizers[indicator_name].update(value)

    def normalize(self, indicator_name: str, value: float) -> float:
        """
        Normalize value for specific indicator.

        Args:
            indicator_name: Name of indicator
            value: Value to normalize

        Returns:
            Normalized value (method depends on config)
        """
        if indicator_name not in self.configs:
            raise ValueError(f"Indicator '{indicator_name}' not registered")

        config = self.configs[indicator_name]

        if config.method == NormalizationMethod.ZSCORE:
            if indicator_name in self.normalizers:
                return self.normalizers[indicator_name].normalize(value)
            return 0.0

        elif config.method == NormalizationMethod.TANH:
            # Legacy tanh normalization
            return float(np.tanh(value / 1000))

        elif config.method == NormalizationMethod.MINMAX:
            # Min-max to [-1, 1] range
            return float(np.clip(value / 100, -1, 1))

        else:  # NONE
            return value

    def is_ready(self, indicator_name: str) -> bool:
        """Check if indicator normalizer has sufficient samples."""
        if indicator_name in self.normalizers:
            return self.normalizers[indicator_name].is_ready
        return True  # Non-zscore methods are always ready

    def get_stats(self, indicator_name: str) -> Dict[str, float]:
        """Get current statistics for indicator."""
        if indicator_name in self.normalizers:
            norm = self.normalizers[indicator_name]
            return {
                'mean': norm.mean,
                'std': norm.std,
                'samples': norm.sample_count,
                'ready': norm.is_ready
            }
        return {}


def create_default_normalizers() -> MultiIndicatorNormalizer:
    """
    Create normalizer with recommended configs for common indicators.

    Returns:
        Configured MultiIndicatorNormalizer instance
    """
    normalizer = MultiIndicatorNormalizer()

    # Accumulative indicators (unbounded)
    accumulative_config = NormalizationConfig.for_accumulative_indicator()
    normalizer.register_indicator('cvd', accumulative_config)
    normalizer.register_indicator('obv', accumulative_config)
    normalizer.register_indicator('adl', accumulative_config)

    # Volatile indicators
    volatile_config = NormalizationConfig.for_volatile_indicator()
    normalizer.register_indicator('volume_delta', volatile_config)
    normalizer.register_indicator('oi_change', volatile_config)

    # Standard indicators
    standard_config = NormalizationConfig()
    normalizer.register_indicator('rsi', standard_config)
    normalizer.register_indicator('macd', standard_config)
    normalizer.register_indicator('price_change', standard_config)

    return normalizer


# Convenience functions for quick normalization

def normalize_signal(
    value: float,
    lookback_data: Union[List[float], np.ndarray],
    winsorize_threshold: float = 3.0
) -> float:
    """
    Quick z-score normalization for single value.

    Args:
        value: Value to normalize
        lookback_data: Historical data for statistics
        winsorize_threshold: Clip threshold

    Returns:
        Normalized z-score
    """
    if len(lookback_data) < 2:
        return 0.0

    mean = np.mean(lookback_data)
    std = np.std(lookback_data, ddof=1)

    if std < 1e-8:
        return 0.0

    z_score = (value - mean) / std
    return float(np.clip(z_score, -winsorize_threshold, winsorize_threshold))


def normalize_array(
    values: Union[List[float], np.ndarray],
    winsorize_threshold: float = 3.0
) -> np.ndarray:
    """
    Quick z-score normalization for array.

    Args:
        values: Array to normalize
        winsorize_threshold: Clip threshold

    Returns:
        Normalized array
    """
    arr = np.asarray(values, dtype=float)

    if len(arr) < 2:
        return np.zeros_like(arr)

    mean = np.mean(arr)
    std = np.std(arr, ddof=1)

    if std < 1e-8:
        return np.zeros_like(arr)

    z_scores = (arr - mean) / std
    return np.clip(z_scores, -winsorize_threshold, winsorize_threshold)


# Volume and whale detection utilities (used by orderflow indicators)

def calculate_volume_ratio(
    buy_volume: float,
    sell_volume: float,
    default: float = 0.5
) -> float:
    """
    Calculate buy/sell volume ratio normalized to 0-1 range.

    Args:
        buy_volume: Total buy volume
        sell_volume: Total sell volume
        default: Default value when total volume is zero

    Returns:
        Ratio between 0 (all sells) and 1 (all buys), 0.5 is neutral
    """
    total = buy_volume + sell_volume
    if total <= 0:
        return default
    return buy_volume / total


def get_whale_multiplier_sigmoid(
    volume: float,
    threshold: float = 1000000,
    steepness: float = 2.0,
    max_multiplier: float = 3.0
) -> float:
    """
    Calculate whale activity multiplier using sigmoid function.

    Provides smooth scaling that approaches max_multiplier for large volumes.

    Args:
        volume: Trade or order volume
        threshold: Volume at which multiplier reaches ~1.5x
        steepness: How quickly multiplier increases
        max_multiplier: Maximum multiplier value

    Returns:
        Multiplier between 1.0 and max_multiplier
    """
    if volume <= 0 or threshold <= 0:
        return 1.0

    # Sigmoid: 1 + (max-1) * (2 / (1 + exp(-steepness * (v/t - 1))) - 1)
    ratio = volume / threshold
    sigmoid = 2.0 / (1.0 + np.exp(-steepness * (ratio - 1.0))) - 1.0
    multiplier = 1.0 + (max_multiplier - 1.0) * max(0, sigmoid)

    return min(multiplier, max_multiplier)


def get_whale_multiplier_log(
    volume: float,
    base_volume: float = 100000,
    scale: float = 0.5,
    max_multiplier: float = 3.0
) -> float:
    """
    Calculate whale activity multiplier using logarithmic scaling.

    Provides diminishing returns for very large volumes.

    Args:
        volume: Trade or order volume
        base_volume: Reference volume for 1x multiplier
        scale: Log scaling factor
        max_multiplier: Maximum multiplier value

    Returns:
        Multiplier between 1.0 and max_multiplier
    """
    if volume <= 0 or base_volume <= 0:
        return 1.0

    # Log scaling: 1 + scale * log(1 + volume/base)
    multiplier = 1.0 + scale * np.log1p(volume / base_volume)

    return min(multiplier, max_multiplier)


def detect_manipulation_risk(
    price_change_pct: float,
    volume_ratio: float,
    spread_pct: float,
    oi_change_pct: float = 0.0,
    thresholds: Optional[Dict[str, float]] = None
) -> Dict[str, any]:
    """
    Detect potential market manipulation based on multiple signals.

    Args:
        price_change_pct: Recent price change percentage
        volume_ratio: Buy/sell volume ratio (0-1)
        spread_pct: Bid-ask spread percentage
        oi_change_pct: Open interest change percentage
        thresholds: Custom detection thresholds

    Returns:
        Dict with risk_score (0-1), risk_level, and detected_patterns
    """
    if thresholds is None:
        thresholds = {
            'price_spike': 2.0,      # % price move
            'volume_imbalance': 0.8,  # extreme buy/sell ratio
            'spread_spike': 0.5,      # % spread
            'oi_divergence': 5.0      # % OI change
        }

    detected_patterns = []
    risk_signals = 0
    max_signals = 4

    # Check for price spike without volume support
    if abs(price_change_pct) > thresholds['price_spike']:
        if 0.4 < volume_ratio < 0.6:  # Balanced volume = suspicious
            detected_patterns.append('price_spike_low_volume')
            risk_signals += 1

    # Check for extreme volume imbalance
    if volume_ratio > thresholds['volume_imbalance'] or volume_ratio < (1 - thresholds['volume_imbalance']):
        detected_patterns.append('extreme_volume_imbalance')
        risk_signals += 1

    # Check for spread manipulation
    if spread_pct > thresholds['spread_spike']:
        detected_patterns.append('wide_spread')
        risk_signals += 1

    # Check for OI divergence from price
    if abs(oi_change_pct) > thresholds['oi_divergence']:
        if (oi_change_pct > 0 and price_change_pct < 0) or \
           (oi_change_pct < 0 and price_change_pct > 0):
            detected_patterns.append('oi_price_divergence')
            risk_signals += 1

    risk_score = risk_signals / max_signals

    if risk_score >= 0.75:
        risk_level = 'high'
    elif risk_score >= 0.5:
        risk_level = 'medium'
    elif risk_score >= 0.25:
        risk_level = 'low'
    else:
        risk_level = 'none'

    return {
        'risk_score': risk_score,
        'risk_level': risk_level,
        'detected_patterns': detected_patterns,
        'signals_triggered': risk_signals
    }
