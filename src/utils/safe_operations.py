"""
Safe Mathematical Operations (Phase 1 - Week 1 Day 3-4)

This module provides numerically safe versions of common mathematical operations
that can fail due to edge cases like division by zero, overflow, or underflow.

Key Features:
- Division-by-zero protection
- Configurable epsilon thresholds
- Context-aware default values
- Optional warning logging
- NaN and infinity handling

Usage:
    from src.utils.safe_operations import safe_divide, safe_log, safe_percentage

    # Basic usage
    result = safe_divide(10, 0)  # Returns 0.0 instead of crashing

    # With custom default
    result = safe_divide(10, 0, default=50.0)  # Returns 50.0

    # With custom epsilon
    result = safe_divide(10, 1e-10, epsilon=1e-8)  # Treats 1e-10 as zero
"""

import numpy as np
from typing import Union, Optional
import logging

# Module logger
logger = logging.getLogger(__name__)

# Default epsilon threshold for near-zero detection
DEFAULT_EPSILON = 1e-10


def safe_divide(
    numerator: Union[float, np.ndarray],
    denominator: Union[float, np.ndarray],
    default: float = 0.0,
    epsilon: float = DEFAULT_EPSILON,
    warn: bool = False
) -> Union[float, np.ndarray]:
    """
    Safely divide two numbers with protection against division by zero.

    This function handles:
    - Exact zero denominators
    - Near-zero denominators (within epsilon threshold)
    - NaN values in inputs
    - Infinity values in inputs
    - Array operations (element-wise)

    Args:
        numerator: The dividend (top of fraction)
        denominator: The divisor (bottom of fraction)
        default: Value to return when division is unsafe (default: 0.0)
        epsilon: Threshold below which denominator is considered zero (default: 1e-10)
        warn: If True, log warning when falling back to default (default: False)

    Returns:
        Result of division, or default value if division is unsafe

    Examples:
        >>> safe_divide(10, 2)
        5.0

        >>> safe_divide(10, 0)
        0.0

        >>> safe_divide(10, 0, default=np.nan)
        nan

        >>> safe_divide(10, 1e-12)  # Near-zero denominator
        0.0

        >>> safe_divide(np.array([10, 20]), np.array([2, 0]))
        array([5., 0.])
    """
    # Handle scalar operations
    if np.isscalar(numerator) and np.isscalar(denominator):
        # Check for NaN or infinity in inputs
        if np.isnan(numerator) or np.isnan(denominator):
            if warn:
                logger.warning(f"safe_divide: NaN in inputs ({numerator}/{denominator}), returning default={default}")
            return default

        if np.isinf(numerator) or np.isinf(denominator):
            if warn:
                logger.warning(f"safe_divide: Infinity in inputs ({numerator}/{denominator}), returning default={default}")
            return default

        # Check for zero or near-zero denominator
        if abs(denominator) < epsilon:
            if warn:
                logger.warning(f"safe_divide: Near-zero denominator ({denominator}), returning default={default}")
            return default

        # Safe to divide
        return numerator / denominator

    # Handle array operations
    numerator_array = np.asarray(numerator)
    denominator_array = np.asarray(denominator)

    # Create result array initialized with default
    result = np.full_like(numerator_array, default, dtype=float)

    # Create mask for safe divisions
    safe_mask = (
        ~np.isnan(numerator_array) &
        ~np.isnan(denominator_array) &
        ~np.isinf(numerator_array) &
        ~np.isinf(denominator_array) &
        (np.abs(denominator_array) >= epsilon)
    )

    # Perform safe divisions
    if np.any(safe_mask):
        result[safe_mask] = numerator_array[safe_mask] / denominator_array[safe_mask]

    # Log warning if any unsafe divisions occurred
    if warn and not np.all(safe_mask):
        unsafe_count = np.sum(~safe_mask)
        logger.warning(f"safe_divide: {unsafe_count} unsafe division(s) detected, using default={default}")

    return result if result.shape else float(result)


def safe_percentage(
    part: Union[float, np.ndarray],
    whole: Union[float, np.ndarray],
    default: float = 0.0,
    epsilon: float = DEFAULT_EPSILON,
    warn: bool = False
) -> Union[float, np.ndarray]:
    """
    Safely calculate percentage: (part / whole) * 100

    This is a convenience wrapper around safe_divide for percentage calculations.

    Args:
        part: The numerator value
        whole: The denominator (total) value
        default: Value to return when calculation is unsafe (default: 0.0)
            Note: This should be the final percentage value (e.g., 50.0 for 50%)
        epsilon: Threshold below which whole is considered zero (default: 1e-10)
        warn: If True, log warning when falling back to default (default: False)

    Returns:
        Percentage value (0-100 scale), or default if calculation is unsafe

    Examples:
        >>> safe_percentage(25, 100)
        25.0

        >>> safe_percentage(1, 0)
        0.0

        >>> safe_percentage(1, 0, default=50.0)
        50.0

        >>> safe_percentage(50, 200)
        25.0
    """
    # Pass default/100 to safe_divide, then multiply result by 100
    # This ensures the default parameter represents the final percentage
    return safe_divide(part, whole, default=default/100, epsilon=epsilon, warn=warn) * 100


def safe_log(
    value: Union[float, np.ndarray],
    base: Optional[float] = None,
    default: float = 0.0,
    epsilon: float = DEFAULT_EPSILON,
    warn: bool = False
) -> Union[float, np.ndarray]:
    """
    Safely calculate logarithm with protection against log(0) and log(negative).

    Args:
        value: The value to take logarithm of
        base: Logarithm base (None = natural log, 10 = log10, 2 = log2, etc.)
        default: Value to return when log is unsafe (default: 0.0)
        epsilon: Threshold below which value is considered zero (default: 1e-10)
        warn: If True, log warning when falling back to default (default: False)

    Returns:
        Logarithm of value, or default if calculation is unsafe

    Examples:
        >>> safe_log(10)  # Natural log
        2.302585...

        >>> safe_log(0)
        0.0

        >>> safe_log(100, base=10)
        2.0

        >>> safe_log(-5)
        0.0
    """
    # Handle scalar operations
    if np.isscalar(value):
        # Check for NaN or infinity
        if np.isnan(value) or np.isinf(value):
            if warn:
                logger.warning(f"safe_log: Invalid input ({value}), returning default={default}")
            return default

        # Check for zero or near-zero
        if abs(value) < epsilon:
            if warn:
                logger.warning(f"safe_log: Near-zero value ({value}), returning default={default}")
            return default

        # Check for negative values
        if value < 0:
            if warn:
                logger.warning(f"safe_log: Negative value ({value}), returning default={default}")
            return default

        # Safe to take log
        if base is None:
            return np.log(value)
        elif base == 10:
            return np.log10(value)
        elif base == 2:
            return np.log2(value)
        else:
            return np.log(value) / np.log(base)

    # Handle array operations
    value_array = np.asarray(value)
    result = np.full_like(value_array, default, dtype=float)

    # Create mask for safe log calculations
    safe_mask = (
        ~np.isnan(value_array) &
        ~np.isinf(value_array) &
        (value_array >= epsilon)
    )

    # Perform safe log calculations
    if np.any(safe_mask):
        if base is None:
            result[safe_mask] = np.log(value_array[safe_mask])
        elif base == 10:
            result[safe_mask] = np.log10(value_array[safe_mask])
        elif base == 2:
            result[safe_mask] = np.log2(value_array[safe_mask])
        else:
            result[safe_mask] = np.log(value_array[safe_mask]) / np.log(base)

    # Log warning if any unsafe operations occurred
    if warn and not np.all(safe_mask):
        unsafe_count = np.sum(~safe_mask)
        logger.warning(f"safe_log: {unsafe_count} unsafe log(s) detected, using default={default}")

    return result if result.shape else float(result)


def safe_sqrt(
    value: Union[float, np.ndarray],
    default: float = 0.0,
    epsilon: float = DEFAULT_EPSILON,
    warn: bool = False
) -> Union[float, np.ndarray]:
    """
    Safely calculate square root with protection against sqrt(negative).

    Args:
        value: The value to take square root of
        default: Value to return when sqrt is unsafe (default: 0.0)
        epsilon: Threshold below which value is considered zero (default: 1e-10)
        warn: If True, log warning when falling back to default (default: False)

    Returns:
        Square root of value, or default if calculation is unsafe

    Examples:
        >>> safe_sqrt(16)
        4.0

        >>> safe_sqrt(-5)
        0.0

        >>> safe_sqrt(0)
        0.0
    """
    # Handle scalar operations
    if np.isscalar(value):
        # Check for NaN or infinity
        if np.isnan(value) or np.isinf(value):
            if warn:
                logger.warning(f"safe_sqrt: Invalid input ({value}), returning default={default}")
            return default

        # Check for negative values (treat near-zero negatives as zero)
        if value < -epsilon:
            if warn:
                logger.warning(f"safe_sqrt: Negative value ({value}), returning default={default}")
            return default

        # Clamp near-zero negatives to zero
        if value < 0:
            value = 0.0

        return np.sqrt(value)

    # Handle array operations
    value_array = np.asarray(value)
    result = np.full_like(value_array, default, dtype=float)

    # Create mask for safe sqrt calculations
    safe_mask = (
        ~np.isnan(value_array) &
        ~np.isinf(value_array) &
        (value_array >= -epsilon)
    )

    # Perform safe sqrt calculations (clamp near-zero negatives)
    if np.any(safe_mask):
        safe_values = np.maximum(value_array[safe_mask], 0.0)
        result[safe_mask] = np.sqrt(safe_values)

    # Log warning if any unsafe operations occurred
    if warn and not np.all(safe_mask):
        unsafe_count = np.sum(~safe_mask)
        logger.warning(f"safe_sqrt: {unsafe_count} unsafe sqrt(s) detected, using default={default}")

    return result if result.shape else float(result)


def clip_to_range(
    value: Union[float, np.ndarray],
    min_value: float,
    max_value: float,
    warn: bool = False
) -> Union[float, np.ndarray]:
    """
    Clip value to specified range, handling NaN and infinity.

    Args:
        value: Value(s) to clip
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        warn: If True, log warning when clipping occurs (default: False)

    Returns:
        Value clipped to [min_value, max_value] range

    Examples:
        >>> clip_to_range(150, 0, 100)
        100

        >>> clip_to_range(-50, 0, 100)
        0

        >>> clip_to_range(np.nan, 0, 100)
        0
    """
    # Replace NaN and infinity with bounds
    if np.isscalar(value):
        if np.isnan(value) or value == -np.inf:
            if warn:
                logger.warning(f"clip_to_range: Invalid value ({value}), using min_value={min_value}")
            return min_value
        if value == np.inf:
            if warn:
                logger.warning(f"clip_to_range: Invalid value ({value}), using max_value={max_value}")
            return max_value

        result = np.clip(value, min_value, max_value)
        if warn and result != value:
            logger.warning(f"clip_to_range: Value {value} clipped to {result}")
        return result

    # Handle array operations
    value_array = np.asarray(value)
    result = np.copy(value_array)

    # Replace NaN with min_value
    nan_mask = np.isnan(result)
    if np.any(nan_mask):
        result[nan_mask] = min_value
        if warn:
            logger.warning(f"clip_to_range: {np.sum(nan_mask)} NaN value(s) replaced with {min_value}")

    # Replace -inf with min_value, +inf with max_value
    neginf_mask = result == -np.inf
    posinf_mask = result == np.inf
    if np.any(neginf_mask):
        result[neginf_mask] = min_value
        if warn:
            logger.warning(f"clip_to_range: {np.sum(neginf_mask)} -inf value(s) replaced with {min_value}")
    if np.any(posinf_mask):
        result[posinf_mask] = max_value
        if warn:
            logger.warning(f"clip_to_range: {np.sum(posinf_mask)} +inf value(s) replaced with {max_value}")

    # Clip to range
    result = np.clip(result, min_value, max_value)

    return result if result.shape else float(result)


# Convenience function for common use case: ensure score is 0-100
def ensure_score_range(
    score: Union[float, np.ndarray],
    warn: bool = False
) -> Union[float, np.ndarray]:
    """
    Ensure score is within 0-100 range, handling NaN and infinity.

    This is a convenience wrapper around clip_to_range for indicator scores.

    Args:
        score: Score value(s) to validate
        warn: If True, log warning when clipping occurs (default: False)

    Returns:
        Score clipped to 0-100 range

    Examples:
        >>> ensure_score_range(150)
        100

        >>> ensure_score_range(-20)
        0

        >>> ensure_score_range(75.5)
        75.5
    """
    return clip_to_range(score, 0.0, 100.0, warn=warn)
