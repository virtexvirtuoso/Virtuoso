"""
Statistical OI-Price Divergence Module

Implements production-quality quantitative analysis for price-OI divergence detection
with adaptive statistical methods, confidence scoring, and partial data utilization.

Key features:
- Adaptive method selection based on sample size (Kendall/Spearman/Pearson)
- Comprehensive confidence scoring (sample, recency, completeness, significance)
- Bootstrap confidence intervals for small samples
- Partial data utilization (works with as few as 3 data points)
- Shadow mode logging for A/B comparison

See: docs/07-technical/investigations/OI_DIVERGENCE_COMPREHENSIVE_STATISTICAL_FRAMEWORK.md
"""

import math
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
import numpy as np

# Scipy is optional - graceful degradation without it
try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Defaults (overridden by config.yaml)
# =============================================================================

DEFAULT_CONFIG = {
    'min_samples': 3,              # Minimum samples for any analysis
    'zscore_threshold': 2.0,       # Z-score threshold for divergence detection
    'divergence_threshold': -0.3,  # Correlation threshold for divergence
    'bootstrap_iterations': 1000,  # Bootstrap resamples for small samples
    'recency_half_life': 30.0,     # Minutes for recency decay
    'significance_level': 0.10,    # P-value threshold for significance
    'shadow_mode_enabled': False,  # Enable shadow mode logging
}


# =============================================================================
# Confidence Scoring Functions
# =============================================================================

def sample_confidence(n: int) -> float:
    """
    Calculate confidence based on sample size.

    Statistical rationale:
    - n < 3: Cannot compute any meaningful correlation
    - n = 3-5: Kendall's Tau possible but wide confidence intervals
    - n = 6-15: Spearman viable, moderate power
    - n = 16-30: Good statistical power
    - n > 30: Approaches asymptotic reliability

    Args:
        n: Number of data points

    Returns:
        Confidence score between 0.15 and 0.95
    """
    if n < 3:
        return 0.15  # Direction-only, very low confidence
    elif n < 6:
        return 0.25 + 0.03 * (n - 3)  # 0.25 -> 0.34
    elif n < 16:
        return 0.40 + 0.03 * (n - 6)  # 0.40 -> 0.67
    elif n < 31:
        return 0.70 + 0.01 * (n - 16)  # 0.70 -> 0.84
    else:
        return min(0.85 + 0.003 * (n - 31), 0.95)  # Asymptote at 0.95


def recency_confidence(oldest_data_age_minutes: float, half_life: float = 30.0) -> float:
    """
    Calculate confidence based on data freshness.

    Uses exponential decay - older data is less reliable for current market state.

    Args:
        oldest_data_age_minutes: Age of oldest data point in minutes
        half_life: Minutes for confidence to drop by half (default 30)

    Returns:
        Confidence score between 0.3 and 1.0
    """
    if oldest_data_age_minutes <= 0:
        return 1.0
    decay = math.exp(-oldest_data_age_minutes * math.log(2) / half_life)
    return max(0.3, decay)  # Floor at 0.3 (old data still has some value)


def completeness_confidence(expected_points: int, actual_points: int) -> float:
    """
    Calculate confidence based on data completeness.

    Gaps in the time series reduce reliability.
    Uses square root to be forgiving of minor gaps.

    Args:
        expected_points: Number of points expected
        actual_points: Number of points actually available

    Returns:
        Confidence score between 0.0 and 1.0
    """
    if expected_points <= 0:
        return 0.5  # Unknown expectation
    ratio = actual_points / expected_points
    return min(1.0, ratio ** 0.5)


def significance_confidence(p_value: Optional[float]) -> float:
    """
    Calculate confidence based on statistical significance.

    Maps p-value to confidence score.

    Args:
        p_value: P-value from correlation test (None if not available)

    Returns:
        Confidence score between 0.3 and 0.95
    """
    if p_value is None:
        return 0.5  # Unknown significance
    elif p_value > 0.10:
        return 0.30  # Not significant
    elif p_value > 0.05:
        return 0.60  # Marginally significant (p < 0.10)
    elif p_value > 0.01:
        return 0.85  # Significant (p < 0.05)
    else:
        return 0.95  # Highly significant (p < 0.01)


def calculate_combined_confidence(
    n: int,
    oldest_age_min: float,
    expected_points: int,
    actual_points: int,
    p_value: Optional[float] = None,
    half_life: float = 30.0
) -> Dict[str, float]:
    """
    Calculate overall confidence and individual components.

    Uses min() for overall - the weakest link determines reliability.

    Args:
        n: Sample size
        oldest_age_min: Age of oldest data in minutes
        expected_points: Expected number of data points
        actual_points: Actual number of data points
        p_value: P-value from statistical test
        half_life: Recency decay half-life

    Returns:
        Dict with 'overall' and individual component confidences
    """
    components = {
        'sample': sample_confidence(n),
        'recency': recency_confidence(oldest_age_min, half_life),
        'completeness': completeness_confidence(expected_points, actual_points),
        'significance': significance_confidence(p_value)
    }
    components['overall'] = min(components.values())
    return components


# =============================================================================
# Adaptive Statistical Methods
# =============================================================================

def calculate_direction_only(
    price_changes: np.ndarray,
    oi_changes: np.ndarray
) -> Dict[str, Any]:
    """
    Direction-only analysis for n < 3.

    Simply compares signs of total changes.
    Very low confidence, but better than nothing.
    """
    price_direction = np.sign(np.sum(price_changes))
    oi_direction = np.sign(np.sum(oi_changes))

    # Divergence = opposite directions
    divergence_detected = price_direction != oi_direction and price_direction != 0 and oi_direction != 0

    return {
        'correlation': -1.0 if divergence_detected else 1.0,
        'method': 'direction_only',
        'p_value': None,
        'max_confidence': 0.15,
        'divergence_detected': divergence_detected,
        'price_direction': int(price_direction),
        'oi_direction': int(oi_direction)
    }


def calculate_kendall_correlation(
    price_changes: np.ndarray,
    oi_changes: np.ndarray,
    divergence_threshold: float = -0.3
) -> Dict[str, Any]:
    """
    Kendall's Tau-b for n = 3-5.

    Distribution-free rank correlation that works with small samples.
    Robust to outliers.
    """
    n = len(price_changes)

    if not SCIPY_AVAILABLE:
        # Fallback to direction-only if scipy unavailable
        return calculate_direction_only(price_changes, oi_changes)

    try:
        tau, p_value = stats.kendalltau(price_changes, oi_changes)

        # P-value unreliable for n < 5
        if n < 5:
            p_value = None

        return {
            'correlation': float(tau) if not np.isnan(tau) else 0.0,
            'method': 'kendall_tau',
            'p_value': float(p_value) if p_value is not None and not np.isnan(p_value) else None,
            'max_confidence': 0.40,
            'divergence_detected': tau < divergence_threshold if not np.isnan(tau) else False,
            'sample_size': n
        }
    except Exception as e:
        logger.warning(f"Kendall correlation failed: {e}")
        return calculate_direction_only(price_changes, oi_changes)


def calculate_spearman_with_bootstrap(
    price_changes: np.ndarray,
    oi_changes: np.ndarray,
    divergence_threshold: float = -0.3,
    bootstrap_iterations: int = 1000,
    significance_level: float = 0.10
) -> Dict[str, Any]:
    """
    Spearman correlation with bootstrap confidence intervals for n = 6-15.

    Provides robust rank correlation with uncertainty quantification.
    """
    n = len(price_changes)

    if not SCIPY_AVAILABLE:
        return calculate_direction_only(price_changes, oi_changes)

    try:
        rho, p_value = stats.spearmanr(price_changes, oi_changes)

        # Bootstrap confidence interval
        bootstrap_rhos = []
        for _ in range(bootstrap_iterations):
            idx = np.random.choice(n, n, replace=True)
            try:
                r, _ = stats.spearmanr(price_changes[idx], oi_changes[idx])
                if not np.isnan(r):
                    bootstrap_rhos.append(r)
            except Exception:
                continue

        if len(bootstrap_rhos) >= 100:
            ci_lower = float(np.percentile(bootstrap_rhos, 2.5))
            ci_upper = float(np.percentile(bootstrap_rhos, 97.5))
        else:
            ci_lower = None
            ci_upper = None

        return {
            'correlation': float(rho) if not np.isnan(rho) else 0.0,
            'method': 'spearman_bootstrap',
            'p_value': float(p_value) if not np.isnan(p_value) else None,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'max_confidence': 0.70,
            'divergence_detected': (
                rho < divergence_threshold and
                p_value < significance_level
            ) if not np.isnan(rho) and not np.isnan(p_value) else False,
            'sample_size': n,
            'bootstrap_samples': len(bootstrap_rhos)
        }
    except Exception as e:
        logger.warning(f"Spearman bootstrap failed: {e}")
        return calculate_kendall_correlation(price_changes, oi_changes, divergence_threshold)


def calculate_full_correlation_suite(
    price_changes: np.ndarray,
    oi_changes: np.ndarray,
    divergence_threshold: float = -0.3,
    significance_level: float = 0.10
) -> Dict[str, Any]:
    """
    Full correlation suite for n >= 16.

    Includes both Spearman (robust) and Pearson (parametric) for comparison.
    Uses Spearman as primary measure.
    """
    n = len(price_changes)

    if not SCIPY_AVAILABLE:
        return calculate_direction_only(price_changes, oi_changes)

    try:
        # Primary: Spearman
        rho, p_spearman = stats.spearmanr(price_changes, oi_changes)

        # Secondary: Pearson
        r, p_pearson = stats.pearsonr(price_changes, oi_changes)

        # Check if methods agree
        methods_agree = np.sign(rho) == np.sign(r) if not np.isnan(rho) and not np.isnan(r) else True

        # Max confidence based on sample size
        if n >= 31:
            max_confidence = min(0.85 + 0.003 * (n - 31), 0.95)
        else:
            max_confidence = 0.85

        return {
            'correlation': float(rho) if not np.isnan(rho) else 0.0,
            'correlation_pearson': float(r) if not np.isnan(r) else 0.0,
            'method': 'spearman_pearson',
            'p_value': float(p_spearman) if not np.isnan(p_spearman) else None,
            'p_value_pearson': float(p_pearson) if not np.isnan(p_pearson) else None,
            'methods_agree': methods_agree,
            'max_confidence': max_confidence,
            'divergence_detected': (
                rho < divergence_threshold and
                p_spearman < significance_level
            ) if not np.isnan(rho) and not np.isnan(p_spearman) else False,
            'sample_size': n
        }
    except Exception as e:
        logger.warning(f"Full correlation suite failed: {e}")
        return calculate_spearman_with_bootstrap(price_changes, oi_changes, divergence_threshold)


# =============================================================================
# Rolling Z-Score Calculation
# =============================================================================

def calculate_rolling_zscore(
    values: np.ndarray,
    window: int = 20
) -> Tuple[float, float, float]:
    """
    Calculate rolling z-score of the latest value.

    Args:
        values: Array of values
        window: Rolling window size

    Returns:
        Tuple of (z_score, rolling_mean, rolling_std)
    """
    if len(values) < 2:
        return 0.0, 0.0, 0.0

    # Use available data up to window size
    window_data = values[-min(window, len(values)):]

    mean = float(np.mean(window_data))
    std = float(np.std(window_data))

    if std < 1e-10:  # Avoid division by zero
        return 0.0, mean, std

    latest = values[-1]
    z_score = (latest - mean) / std

    return float(z_score), mean, std


# =============================================================================
# Main Statistical OI Divergence Calculator
# =============================================================================

class OIDivergenceStatsCalculator:
    """
    Statistical OI-Price Divergence Calculator with adaptive methods and confidence scoring.

    This replaces the naive divergence calculation with a production-quality
    quantitative framework that:
    - Adapts methods based on sample size
    - Provides confidence scores for all outputs
    - Uses partial data effectively
    - Supports shadow mode for A/B comparison
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize calculator with configuration.

        Args:
            config: Configuration dict (uses defaults if not provided)
        """
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.logger = logging.getLogger(__name__)

        # Cache for recent calculations
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 60  # Cache TTL in seconds

    def calculate(
        self,
        price_changes: List[float],
        oi_changes: List[float],
        timestamps: Optional[List[float]] = None,
        expected_points: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate statistical price-OI divergence.

        Args:
            price_changes: List of price changes
            oi_changes: List of OI changes (must match length)
            timestamps: Optional list of timestamps (for recency calculation)
            expected_points: Expected number of data points (for completeness)

        Returns:
            Dict with divergence analysis including:
            - type: 'bullish', 'bearish', or 'neutral'
            - strength: 0-100 score
            - correlation: Raw correlation value
            - confidence: Overall confidence score
            - confidence_components: Individual confidence factors
            - method: Statistical method used
            - sample_size: Number of data points
            - p_value: Statistical significance (if available)
        """
        start_time = time.time()

        # Validate inputs
        if not price_changes or not oi_changes:
            return self._neutral_result("Empty input data")

        if len(price_changes) != len(oi_changes):
            return self._neutral_result(f"Length mismatch: prices={len(price_changes)}, oi={len(oi_changes)}")

        n = len(price_changes)
        min_samples = self.config['min_samples']

        if n < min_samples:
            return self._neutral_result(f"Insufficient samples: {n} < {min_samples}")

        # Convert to numpy arrays
        price_arr = np.array(price_changes, dtype=float)
        oi_arr = np.array(oi_changes, dtype=float)

        # Remove any NaN/Inf values
        valid_mask = np.isfinite(price_arr) & np.isfinite(oi_arr)
        if not np.any(valid_mask):
            return self._neutral_result("No valid data points after filtering")

        price_arr = price_arr[valid_mask]
        oi_arr = oi_arr[valid_mask]
        n = len(price_arr)

        if n < min_samples:
            return self._neutral_result(f"Insufficient valid samples: {n} < {min_samples}")

        # Select and apply appropriate method
        divergence_threshold = self.config['divergence_threshold']
        bootstrap_iterations = self.config['bootstrap_iterations']
        significance_level = self.config['significance_level']

        if n < 3:
            stats_result = calculate_direction_only(price_arr, oi_arr)
        elif n < 6:
            stats_result = calculate_kendall_correlation(price_arr, oi_arr, divergence_threshold)
        elif n < 16:
            stats_result = calculate_spearman_with_bootstrap(
                price_arr, oi_arr, divergence_threshold, bootstrap_iterations, significance_level
            )
        else:
            stats_result = calculate_full_correlation_suite(
                price_arr, oi_arr, divergence_threshold, significance_level
            )

        # Calculate data freshness
        oldest_age_min = 0.0
        if timestamps and len(timestamps) > 0:
            try:
                now = datetime.now(timezone.utc).timestamp() * 1000
                oldest_ts = min(timestamps)
                oldest_age_min = (now - oldest_ts) / 60000  # Convert to minutes
            except Exception:
                oldest_age_min = 30.0  # Default to half-life if can't calculate

        # Calculate confidence
        confidence_result = calculate_combined_confidence(
            n=n,
            oldest_age_min=oldest_age_min,
            expected_points=expected_points or n,
            actual_points=n,
            p_value=stats_result.get('p_value'),
            half_life=self.config['recency_half_life']
        )

        # Cap confidence at method's max
        max_conf = stats_result.get('max_confidence', 0.95)
        overall_confidence = min(confidence_result['overall'], max_conf)

        # Determine divergence type and strength
        correlation = stats_result.get('correlation', 0.0)
        divergence_detected = stats_result.get('divergence_detected', False)

        # Calculate strength from correlation
        # Map correlation from [-1, 1] to strength [0, 100]
        # Negative correlation = divergence strength
        if divergence_detected and correlation < 0:
            raw_strength = abs(correlation) * 100
        else:
            raw_strength = 0.0

        # Apply confidence scaling
        effective_strength = raw_strength * overall_confidence

        # Determine type based on price direction and divergence
        price_trend = np.sum(price_arr)
        oi_trend = np.sum(oi_arr)

        if divergence_detected:
            if price_trend > 0 and oi_trend < 0:
                divergence_type = 'bearish'
            elif price_trend < 0 and oi_trend > 0:
                divergence_type = 'bullish'
            else:
                divergence_type = 'neutral'
        else:
            divergence_type = 'neutral'

        # Calculate z-score for OI changes
        z_score, z_mean, z_std = calculate_rolling_zscore(oi_arr)

        result = {
            'type': divergence_type,
            'strength': float(min(effective_strength, 100.0)),
            'raw_strength': float(raw_strength),
            'correlation': float(correlation),
            'confidence': float(overall_confidence),
            'confidence_components': confidence_result,
            'method': stats_result.get('method', 'unknown'),
            'sample_size': n,
            'p_value': stats_result.get('p_value'),
            'divergence_detected': divergence_detected,
            'price_trend': float(price_trend),
            'oi_trend': float(oi_trend),
            'z_score': float(z_score),
            'z_mean': float(z_mean),
            'z_std': float(z_std),
            'calculation_time_ms': (time.time() - start_time) * 1000
        }

        # Add confidence interval if available
        if 'ci_lower' in stats_result:
            result['ci_lower'] = stats_result['ci_lower']
            result['ci_upper'] = stats_result['ci_upper']

        # Add Pearson comparison if available
        if 'correlation_pearson' in stats_result:
            result['correlation_pearson'] = stats_result['correlation_pearson']
            result['methods_agree'] = stats_result['methods_agree']

        self.logger.debug(
            f"OI divergence stats: type={divergence_type}, strength={effective_strength:.1f}, "
            f"corr={correlation:.3f}, conf={overall_confidence:.2f}, method={result['method']}, n={n}"
        )

        return result

    def _neutral_result(self, reason: str) -> Dict[str, Any]:
        """Return a neutral result with reason."""
        self.logger.debug(f"OI divergence neutral: {reason}")
        return {
            'type': 'neutral',
            'strength': 0.0,
            'raw_strength': 0.0,
            'correlation': 0.0,
            'confidence': 0.0,
            'confidence_components': {
                'sample': 0.0,
                'recency': 0.0,
                'completeness': 0.0,
                'significance': 0.0,
                'overall': 0.0
            },
            'method': 'none',
            'sample_size': 0,
            'p_value': None,
            'divergence_detected': False,
            'reason': reason
        }


# =============================================================================
# Shadow Mode Storage Integration
# =============================================================================

def init_shadow_oi_divergence_table():
    """
    Initialize shadow_oi_divergence table for A/B comparison.

    Creates table if it doesn't exist.
    """
    try:
        from src.database.shadow_storage import get_db_path
        import sqlite3
        import os

        db_path = get_db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shadow_oi_divergence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                legacy_type TEXT,
                legacy_strength REAL,
                new_type TEXT,
                new_strength REAL,
                new_correlation REAL,
                new_confidence REAL,
                new_method TEXT,
                sample_count INTEGER,
                difference REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_shadow_oi_div_timestamp
            ON shadow_oi_divergence(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_shadow_oi_div_symbol
            ON shadow_oi_divergence(symbol)
        ''')

        conn.commit()
        conn.close()

        logger.info("Shadow OI divergence table initialized")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize shadow_oi_divergence table: {e}")
        return False


def log_shadow_comparison(
    symbol: str,
    legacy_result: Dict[str, Any],
    new_result: Dict[str, Any]
):
    """
    Log shadow mode comparison between legacy and new divergence calculation.

    Args:
        symbol: Trading symbol
        legacy_result: Result from legacy calculation
        new_result: Result from new statistical calculation
    """
    try:
        from src.database.shadow_storage import get_db_path
        import sqlite3

        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        legacy_strength = legacy_result.get('strength', 0.0)
        new_strength = new_result.get('strength', 0.0)
        difference = abs(new_strength - legacy_strength)

        cursor.execute('''
            INSERT INTO shadow_oi_divergence (
                timestamp, symbol, legacy_type, legacy_strength,
                new_type, new_strength, new_correlation, new_confidence,
                new_method, sample_count, difference
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            int(datetime.now(timezone.utc).timestamp() * 1000),
            symbol,
            legacy_result.get('type', 'neutral'),
            legacy_strength,
            new_result.get('type', 'neutral'),
            new_strength,
            new_result.get('correlation', 0.0),
            new_result.get('confidence', 0.0),
            new_result.get('method', 'unknown'),
            new_result.get('sample_size', 0),
            difference
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        logger.debug(f"Shadow logging failed (non-critical): {e}")


# =============================================================================
# Module-level Calculator Instance
# =============================================================================

# Singleton calculator instance
_calculator: Optional[OIDivergenceStatsCalculator] = None


def get_calculator(config: Optional[Dict[str, Any]] = None) -> OIDivergenceStatsCalculator:
    """Get or create the singleton calculator instance."""
    global _calculator
    if _calculator is None:
        _calculator = OIDivergenceStatsCalculator(config)
    return _calculator


def calculate_statistical_divergence(
    price_changes: List[float],
    oi_changes: List[float],
    timestamps: Optional[List[float]] = None,
    expected_points: Optional[int] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function for calculating statistical divergence.

    Uses singleton calculator instance.
    """
    calculator = get_calculator(config)
    return calculator.calculate(price_changes, oi_changes, timestamps, expected_points)
