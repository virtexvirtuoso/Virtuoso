"""
Execution Quality Pre-Trade Checks

Pre-flight checks to detect market manipulation, illiquidity, and dangerous
execution conditions before entering trades.

Key Check: Mark Price Divergence
- Compares mark price (liquidation price) vs last traded price
- Large divergence indicates wash trading, manipulation, or illiquidity
- Prevents bad fills during market dysfunction
"""

from typing import Dict, Literal, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExecutionQualityCheck:
    """Result of execution quality pre-check."""
    is_safe: bool
    divergence_pct: float
    action: Literal['NORMAL', 'WIDEN_STOPS', 'REJECT_SIGNAL']
    reason: str
    mark_price: Optional[float] = None
    last_price: Optional[float] = None


async def check_mark_price_divergence(
    exchange,
    symbol: str,
    threshold_warning: float = 0.5,
    threshold_critical: float = 1.0
) -> ExecutionQualityCheck:
    """
    Check for mark price divergence before executing trade.

    Mark price is the exchange's "fair value" used for liquidations.
    Large divergence from last traded price indicates:
    - Wash trading or manipulation (fake volume, price doesn't reflect reality)
    - Extreme illiquidity (wide bid-ask spreads)
    - Exchange issues or data problems

    Args:
        exchange: Exchange instance (must have fetch_mark_price_kline and fetch_ticker)
        symbol: Trading pair (e.g., 'BTC/USDT:USDT')
        threshold_warning: Warning threshold in % (default 0.5%)
        threshold_critical: Critical threshold in % (default 1.0%)

    Returns:
        ExecutionQualityCheck with:
        - NORMAL: < 0.5% divergence (safe to trade)
        - WIDEN_STOPS: 0.5% - 1.0% divergence (trade with caution, wider stops)
        - REJECT_SIGNAL: > 1.0% divergence (dangerous, skip trade)

    Thresholds:
        < 0.5%: NORMAL (safe to trade)
        0.5% - 1.0%: WIDEN_STOPS (caution, increase stop distance)
        > 1.0%: REJECT_SIGNAL (danger, skip this signal)

    Example:
        >>> check = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')
        >>> if check.action == 'REJECT_SIGNAL':
        >>>     logger.warning(f"Skipping trade: {check.reason}")
        >>>     return
    """
    try:
        # Fetch mark price data (most recent)
        mark_data = await exchange.fetch_mark_price_kline(symbol, interval='1', limit=1)
        mark_price = mark_data.get('current_mark_price')

        if not mark_price:
            logger.warning(f"No mark price available for {symbol}, assuming safe")
            return ExecutionQualityCheck(
                is_safe=True,
                divergence_pct=0.0,
                action='NORMAL',
                reason='Mark price data unavailable, proceeding with caution'
            )

        # Fetch last traded price
        ticker = await exchange.fetch_ticker(symbol)
        last_price = ticker.get('last')

        if not last_price:
            logger.warning(f"No last price available for {symbol}, assuming safe")
            return ExecutionQualityCheck(
                is_safe=True,
                divergence_pct=0.0,
                action='NORMAL',
                reason='Last price data unavailable, proceeding with caution',
                mark_price=mark_price
            )

        # Calculate divergence percentage
        divergence_pct = abs((mark_price - last_price) / last_price) * 100

        # Determine action based on thresholds
        if divergence_pct < threshold_warning:
            return ExecutionQualityCheck(
                is_safe=True,
                divergence_pct=divergence_pct,
                action='NORMAL',
                reason=f'Normal market conditions (divergence: {divergence_pct:.2f}%)',
                mark_price=mark_price,
                last_price=last_price
            )
        elif divergence_pct < threshold_critical:
            return ExecutionQualityCheck(
                is_safe=True,
                divergence_pct=divergence_pct,
                action='WIDEN_STOPS',
                reason=f'Moderate divergence detected ({divergence_pct:.2f}%), widen stops',
                mark_price=mark_price,
                last_price=last_price
            )
        else:
            return ExecutionQualityCheck(
                is_safe=False,
                divergence_pct=divergence_pct,
                action='REJECT_SIGNAL',
                reason=f'Critical divergence detected ({divergence_pct:.2f}%), rejecting signal',
                mark_price=mark_price,
                last_price=last_price
            )

    except Exception as e:
        logger.error(f"Error checking mark price divergence for {symbol}: {e}")
        # On error, assume safe to avoid false positives blocking all trades
        return ExecutionQualityCheck(
            is_safe=True,
            divergence_pct=0.0,
            action='NORMAL',
            reason=f'Error during check: {str(e)}, proceeding with caution'
        )


async def check_execution_quality(
    exchange,
    symbol: str,
    signal_strength: float = 0.0
) -> ExecutionQualityCheck:
    """
    Comprehensive execution quality check before trade.

    Currently checks:
    1. Mark price divergence (manipulation detection)

    Future checks could include:
    - Bid-ask spread width
    - Recent volatility spikes
    - Orderbook depth
    - Volume anomalies

    Args:
        exchange: Exchange instance
        symbol: Trading pair
        signal_strength: Signal strength (0-100) for context

    Returns:
        ExecutionQualityCheck with recommended action
    """
    # For now, only check mark price divergence
    # Future: Add more checks and aggregate results

    check = await check_mark_price_divergence(exchange, symbol)

    # Log the check result
    if check.action == 'REJECT_SIGNAL':
        logger.warning(
            f"❌ Execution quality check FAILED for {symbol}: {check.reason}"
        )
    elif check.action == 'WIDEN_STOPS':
        logger.info(
            f"⚠️  Execution quality check WARNING for {symbol}: {check.reason}"
        )
    else:
        logger.debug(
            f"✅ Execution quality check PASSED for {symbol}: {check.reason}"
        )

    return check
