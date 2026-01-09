# src/core/analysis/liquidation_decay.py
"""
Liquidation Time Decay Module

Implements exponential time decay for liquidation scoring to improve
signal quality by weighting recent events more heavily than older ones.

Key Features:
- Configurable half-life (default: 3.5 hours)
- Outlier handling via sqrt transform
- Cascade detection for clustered events
- Minimum event threshold for statistical validity

Usage:
    from src.core.analysis.liquidation_decay import (
        LiquidationDecayConfig,
        calculate_liquidation_score_with_decay
    )

    config = LiquidationDecayConfig(half_life_hours=3.5)
    result = calculate_liquidation_score_with_decay(liquidations, config)
"""

import math
import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class DecayFunction(Enum):
    """Supported decay function types."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    POWER_LAW = "power_law"


@dataclass
class LiquidationDecayConfig:
    """Configuration for liquidation time decay scoring.

    Attributes:
        enabled: Master switch for decay functionality
        half_life_hours: Time for weight to decay to 50%
        min_effective_weight: Minimum weight threshold (events below this are excluded)
        min_events: Minimum events required for valid score
        use_sqrt_transform: Apply sqrt transform to reduce outlier impact
        cascade_detection: Enable special handling for clustered liquidations
        cascade_window_minutes: Window size for cascade detection
        cascade_min_events: Minimum events to trigger cascade handling
        decay_function: Type of decay function to use
        power_law_alpha: Exponent for power law decay (if used)
    """
    enabled: bool = True
    half_life_hours: float = 3.5
    min_effective_weight: float = 0.01
    min_events: int = 5
    use_sqrt_transform: bool = True
    cascade_detection: bool = True
    cascade_window_minutes: float = 5.0
    cascade_min_events: int = 10
    decay_function: DecayFunction = DecayFunction.EXPONENTIAL
    power_law_alpha: float = 0.5

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.half_life_hours <= 0:
            raise ValueError("half_life_hours must be positive")
        if not 0 < self.min_effective_weight < 1:
            raise ValueError("min_effective_weight must be between 0 and 1")
        if self.min_events < 1:
            raise ValueError("min_events must be at least 1")

    @property
    def decay_constant(self) -> float:
        """Calculate decay constant (lambda) from half-life."""
        return math.log(2) / self.half_life_hours

    @property
    def max_age_hours(self) -> float:
        """Calculate maximum age before weight drops below threshold."""
        # Solve: e^(-λt) = min_weight => t = -ln(min_weight) / λ
        return -math.log(self.min_effective_weight) / self.decay_constant


@dataclass
class DecayedLiquidationResult:
    """Result of decay-weighted liquidation calculation.

    Attributes:
        long_liquidations: Decay-weighted sum of long liquidations
        short_liquidations: Decay-weighted sum of short liquidations
        total_liquidations: Decay-weighted total
        net_imbalance: (short - long) / total, range [-1, 1]
        raw_score: Transformed score before normalization
        event_count: Number of events included (after filtering)
        effective_events: Sum of weights (effective number of events)
        oldest_event_age_hours: Age of oldest included event
        cascade_detected: Whether a cascade was detected
        cascade_weight_boost: Multiplier applied due to cascade
        warnings: Any warnings generated during calculation
    """
    long_liquidations: float
    short_liquidations: float
    total_liquidations: float
    net_imbalance: float
    raw_score: float
    event_count: int
    effective_events: float
    oldest_event_age_hours: float
    cascade_detected: bool = False
    cascade_weight_boost: float = 1.0
    warnings: List[str] = field(default_factory=list)


def calculate_decay_weight(
    event_age_hours: float,
    config: LiquidationDecayConfig
) -> float:
    """Calculate the decay weight for a single event.

    Args:
        event_age_hours: Age of the event in hours (0 = now)
        config: Decay configuration

    Returns:
        Weight between 0 and 1, or 0 if below minimum threshold

    Examples:
        >>> config = LiquidationDecayConfig(half_life_hours=3.5)
        >>> calculate_decay_weight(0, config)
        1.0
        >>> calculate_decay_weight(3.5, config)
        0.5
        >>> calculate_decay_weight(7.0, config)
        0.25
    """
    if event_age_hours < 0:
        logger.warning(f"Negative event age: {event_age_hours}h, treating as 0")
        event_age_hours = 0

    if config.decay_function == DecayFunction.EXPONENTIAL:
        weight = math.exp(-config.decay_constant * event_age_hours)
    elif config.decay_function == DecayFunction.LINEAR:
        max_age = config.max_age_hours
        weight = max(0, 1 - event_age_hours / max_age)
    elif config.decay_function == DecayFunction.POWER_LAW:
        weight = (1 + event_age_hours) ** (-config.power_law_alpha)
    else:
        raise ValueError(f"Unknown decay function: {config.decay_function}")

    # Apply minimum threshold
    if weight < config.min_effective_weight:
        return 0.0

    return weight


def detect_cascade(
    liquidations: List[Dict[str, Any]],
    config: LiquidationDecayConfig,
    current_time_ms: int
) -> Tuple[bool, float, List[Dict[str, Any]]]:
    """Detect if liquidations form a cascade pattern.

    A cascade is detected when many liquidations occur in a short window,
    indicating a potential chain reaction of forced liquidations.

    Args:
        liquidations: List of liquidation events with timestamps
        config: Decay configuration
        current_time_ms: Current time in milliseconds

    Returns:
        Tuple of (cascade_detected, weight_boost, cascade_events)
    """
    if not config.cascade_detection:
        return False, 1.0, []

    cascade_window_ms = config.cascade_window_minutes * 60 * 1000
    recent_cutoff = current_time_ms - cascade_window_ms

    # Find events within cascade window (filter out non-dict items)
    cascade_events = [
        liq for liq in liquidations
        if isinstance(liq, dict) and liq.get('timestamp', 0) >= recent_cutoff
    ]

    if len(cascade_events) >= config.cascade_min_events:
        # Calculate cascade intensity
        # More events in shorter time = higher intensity
        if len(cascade_events) > 0:
            time_span_ms = max(
                liq.get('timestamp', 0) for liq in cascade_events
            ) - min(
                liq.get('timestamp', 0) for liq in cascade_events
            )

            # Intensity: events per minute
            time_span_minutes = max(time_span_ms / 60000, 0.1)  # Avoid division by zero
            intensity = len(cascade_events) / time_span_minutes

            # Boost factor: 1.0 to 2.0 based on intensity
            # 10 events/min = 1.0x, 50 events/min = 1.5x, 100+ events/min = 2.0x
            weight_boost = min(2.0, 1.0 + (intensity - 10) / 180)
            weight_boost = max(1.0, weight_boost)

            logger.info(
                f"Cascade detected: {len(cascade_events)} events in "
                f"{time_span_minutes:.1f}min (intensity: {intensity:.1f}/min, "
                f"boost: {weight_boost:.2f}x)"
            )

            return True, weight_boost, cascade_events

    return False, 1.0, []


def calculate_liquidation_score_with_decay(
    liquidations: List[Dict[str, Any]],
    config: Optional[LiquidationDecayConfig] = None,
    current_time_ms: Optional[int] = None
) -> DecayedLiquidationResult:
    """Calculate decay-weighted liquidation score.

    This function replaces the equal-weighted aggregation in confluence.py
    with exponential time decay to improve signal quality.

    Args:
        liquidations: List of liquidation events, each containing:
            - 'side': 'buy' (short liq) or 'sell' (long liq)
            - 'qty' or 'amount' or 'size': liquidation size
            - 'timestamp': event timestamp in milliseconds
        config: Decay configuration (uses defaults if None)
        current_time_ms: Current time in ms (uses system time if None)

    Returns:
        DecayedLiquidationResult with weighted scores and metadata

    Example:
        >>> liquidations = [
        ...     {'side': 'buy', 'qty': 1000, 'timestamp': now - 1*hour},
        ...     {'side': 'sell', 'qty': 500, 'timestamp': now - 4*hour},
        ... ]
        >>> result = calculate_liquidation_score_with_decay(liquidations)
        >>> print(f"Net imbalance: {result.net_imbalance:.2f}")
    """
    if config is None:
        config = LiquidationDecayConfig()

    if current_time_ms is None:
        current_time_ms = int(time.time() * 1000)

    warnings = []

    # If decay is disabled, use legacy equal-weighting
    if not config.enabled:
        long_liq = 0.0
        short_liq = 0.0
        for liq in liquidations:
            if isinstance(liq, dict):
                side = liq.get('side', '').lower()
                qty = float(liq.get('qty', liq.get('amount', liq.get('size', 0.0))))
                if side == 'buy':
                    short_liq += qty
                elif side == 'sell':
                    long_liq += qty
        total_liq = long_liq + short_liq
        return DecayedLiquidationResult(
            long_liquidations=long_liq,
            short_liquidations=short_liq,
            total_liquidations=total_liq,
            net_imbalance=0.0 if total_liq == 0 else (short_liq - long_liq) / total_liq,
            raw_score=0.0,
            event_count=len([l for l in liquidations if isinstance(l, dict)]),
            effective_events=float(len([l for l in liquidations if isinstance(l, dict)])),
            oldest_event_age_hours=0.0,
            cascade_detected=False,
            cascade_weight_boost=1.0,
            warnings=["Decay disabled - using legacy equal weighting"]
        )

    # Handle empty or insufficient data
    if not liquidations:
        return DecayedLiquidationResult(
            long_liquidations=0.0,
            short_liquidations=0.0,
            total_liquidations=0.0,
            net_imbalance=0.0,
            raw_score=0.0,
            event_count=0,
            effective_events=0.0,
            oldest_event_age_hours=0.0,
            warnings=["No liquidation events provided"]
        )

    # Detect cascades first
    cascade_detected, cascade_boost, cascade_events = detect_cascade(
        liquidations, config, current_time_ms
    )

    long_weighted = 0.0
    short_weighted = 0.0
    total_weight = 0.0
    included_count = 0
    oldest_age_hours = 0.0

    for liq in liquidations:
        if not isinstance(liq, dict):
            continue

        # Extract timestamp
        timestamp = liq.get('timestamp', 0)
        if timestamp <= 0:
            warnings.append(f"Invalid timestamp in liquidation: {liq}")
            continue

        # Calculate age in hours
        age_ms = current_time_ms - timestamp
        age_hours = age_ms / (1000 * 60 * 60)

        # Skip future events (clock skew)
        if age_hours < -0.01:  # Allow 36 seconds of clock skew
            warnings.append(f"Future liquidation detected (age: {age_hours:.2f}h)")
            continue

        age_hours = max(0, age_hours)  # Clamp small negative values to 0

        # Calculate decay weight
        weight = calculate_decay_weight(age_hours, config)

        if weight <= 0:
            continue  # Below minimum threshold

        # Apply cascade boost to recent events
        if cascade_detected and timestamp >= (current_time_ms - config.cascade_window_minutes * 60 * 1000):
            weight *= cascade_boost

        # Extract size (handle different field names)
        qty = float(liq.get('qty', liq.get('amount', liq.get('size', 0.0))))

        if qty <= 0:
            continue

        # Apply sqrt transform for outlier reduction
        if config.use_sqrt_transform:
            qty = math.sqrt(qty)

        # Categorize by side
        side = liq.get('side', '').lower()
        if side == 'buy':
            # Buy liquidation = short position liquidated (bullish)
            short_weighted += qty * weight
        elif side == 'sell':
            # Sell liquidation = long position liquidated (bearish)
            long_weighted += qty * weight
        else:
            warnings.append(f"Unknown liquidation side: {side}")
            continue

        total_weight += weight
        included_count += 1
        oldest_age_hours = max(oldest_age_hours, age_hours)

    # Calculate totals
    total_weighted = long_weighted + short_weighted

    # Check minimum event threshold
    if included_count < config.min_events:
        warnings.append(
            f"Insufficient events: {included_count} < {config.min_events} minimum"
        )
        # Return neutral score but with data
        return DecayedLiquidationResult(
            long_liquidations=long_weighted,
            short_liquidations=short_weighted,
            total_liquidations=total_weighted,
            net_imbalance=0.0,
            raw_score=0.0,
            event_count=included_count,
            effective_events=total_weight,
            oldest_event_age_hours=oldest_age_hours,
            cascade_detected=cascade_detected,
            cascade_weight_boost=cascade_boost,
            warnings=warnings
        )

    # Calculate net imbalance: positive = more shorts liquidated (bullish)
    # negative = more longs liquidated (bearish)
    if total_weighted > 0:
        net_imbalance = (short_weighted - long_weighted) / total_weighted
    else:
        net_imbalance = 0.0

    # Calculate raw score using tanh for bounded output
    # Scale factor chosen so that moderate imbalance maps to ~0.6-0.7
    raw_score = math.tanh(net_imbalance * 1.5)

    return DecayedLiquidationResult(
        long_liquidations=long_weighted,
        short_liquidations=short_weighted,
        total_liquidations=total_weighted,
        net_imbalance=net_imbalance,
        raw_score=raw_score,
        event_count=included_count,
        effective_events=total_weight,
        oldest_event_age_hours=oldest_age_hours,
        cascade_detected=cascade_detected,
        cascade_weight_boost=cascade_boost,
        warnings=warnings
    )


def convert_score_to_confluence_scale(
    decay_result: DecayedLiquidationResult,
    neutral_point: float = 50.0,
    scale_factor: float = 25.0
) -> float:
    """Convert decay result to 0-100 confluence scale.

    Maps raw_score from [-1, 1] to [0, 100] with configurable
    neutral point and sensitivity.

    Args:
        decay_result: Result from calculate_liquidation_score_with_decay
        neutral_point: Score representing neutral (default 50)
        scale_factor: How much raw_score affects final score

    Returns:
        Score between 0 and 100

    Example:
        >>> result = DecayedLiquidationResult(raw_score=0.5, ...)
        >>> score = convert_score_to_confluence_scale(result)
        >>> print(f"Confluence score: {score:.1f}")  # ~62.5
    """
    # raw_score is in [-1, 1] range (from tanh)
    # Map to [0, 100] with neutral at 50
    score = neutral_point + (decay_result.raw_score * scale_factor)

    # Clamp to valid range
    return max(0.0, min(100.0, score))


def get_decayed_liquidation_score(
    liquidations: List[Dict[str, Any]],
    config: Optional[LiquidationDecayConfig] = None
) -> Dict[str, Any]:
    """High-level function returning liquidation data in confluence.py format.

    This function can directly replace the aggregation logic in
    confluence.py:3859-3876.

    Args:
        liquidations: List of liquidation events
        config: Optional decay configuration

    Returns:
        Dict matching existing sentiment_data['liquidations'] format:
        {
            'long': float,
            'short': float,
            'total': float,
            'timestamp': int,
            'decay_info': {...}  # Additional metadata
        }
    """
    result = calculate_liquidation_score_with_decay(liquidations, config)

    # If sqrt transform was used, square the results to get back to original scale
    # for compatibility with existing code that expects raw USD values
    if config is None or config.use_sqrt_transform:
        long_liq = result.long_liquidations ** 2
        short_liq = result.short_liquidations ** 2
        total_liq = long_liq + short_liq
    else:
        long_liq = result.long_liquidations
        short_liq = result.short_liquidations
        total_liq = result.total_liquidations

    return {
        'long': long_liq,
        'short': short_liq,
        'total': total_liq,
        'timestamp': int(time.time() * 1000),
        'decay_info': {
            'net_imbalance': result.net_imbalance,
            'raw_score': result.raw_score,
            'event_count': result.event_count,
            'effective_events': result.effective_events,
            'cascade_detected': result.cascade_detected,
            'warnings': result.warnings
        }
    }


def load_decay_config(app_config: dict) -> LiquidationDecayConfig:
    """Load decay configuration from application config.

    Args:
        app_config: Application configuration dictionary

    Returns:
        LiquidationDecayConfig instance
    """
    decay_section = app_config.get('liquidation_decay', {})
    cascade_section = decay_section.get('cascade_detection', {})
    advanced_section = decay_section.get('advanced', {})

    return LiquidationDecayConfig(
        enabled=decay_section.get('enabled', True),
        half_life_hours=decay_section.get('half_life_hours', 3.5),
        min_events=decay_section.get('min_events', 5),
        use_sqrt_transform=decay_section.get('use_sqrt_transform', True),
        min_effective_weight=decay_section.get('min_effective_weight', 0.01),
        cascade_detection=cascade_section.get('enabled', True),
        cascade_window_minutes=cascade_section.get('window_minutes', 5.0),
        cascade_min_events=cascade_section.get('min_events', 10),
        decay_function=DecayFunction(advanced_section.get('decay_function', 'exponential')),
        power_law_alpha=advanced_section.get('power_law_alpha', 0.5),
    )
