"""
Liquidation Zones API Endpoint

Provides aggregated liquidation data across multiple exchanges, clustered into price zones.
Used for displaying liquidation clusters on trading charts and detecting cascade risks.
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class LiquidationZone(BaseModel):
    """Represents a clustered liquidation zone at a specific price level."""
    price: float = Field(..., description="Price level of liquidation cluster")
    total_size_usd: float = Field(..., description="Total USD value of liquidations in zone")
    count: int = Field(..., description="Number of individual liquidations in zone")
    exchanges: List[str] = Field(..., description="Exchanges contributing to this zone")
    side: str = Field(..., description="Liquidation side (long/short)")
    confidence: str = Field(..., description="Confidence level (high/medium/low)")


class LiquidationZonesResponse(BaseModel):
    """Response model for liquidation zones endpoint."""
    symbol: str
    zones: List[LiquidationZone]
    cascade_detected: bool
    cascade_price: Optional[float] = None
    cascade_size: Optional[float] = None
    total_exchanges: int
    lookback_hours: int
    timestamp: str


def cluster_liquidations_by_price(liquidations: List[Any], clustering_pct: float = 2.0) -> List[Dict[str, Any]]:
    """
    Cluster liquidations into price zones.

    Args:
        liquidations: List of LiquidationEvent objects
        clustering_pct: Price range percentage for clustering (default 2%)

    Returns:
        List of zone dictionaries with aggregated data
    """
    if not liquidations:
        return []

    zones = []

    for liq in liquidations:
        # Find existing zone within clustering percentage
        matched_zone = None
        for zone in zones:
            price_diff_pct = abs(zone['price'] - liq.trigger_price) / zone['price'] * 100
            if price_diff_pct <= clustering_pct:
                matched_zone = zone
                break

        if matched_zone:
            # Add to existing zone
            matched_zone['total_size_usd'] += liq.liquidated_amount_usd
            matched_zone['count'] += 1
            matched_zone['exchanges'].add(liq.exchange)

            # Determine side (long or short liquidation)
            if 'LONG' in liq.liquidation_type.value.upper():
                matched_zone['long_count'] += 1
            else:
                matched_zone['short_count'] += 1
        else:
            # Create new zone
            is_long_liq = 'LONG' in liq.liquidation_type.value.upper()
            zones.append({
                'price': liq.trigger_price,
                'total_size_usd': liq.liquidated_amount_usd,
                'count': 1,
                'exchanges': {liq.exchange},
                'long_count': 1 if is_long_liq else 0,
                'short_count': 0 if is_long_liq else 1
            })

    # Determine dominant side and confidence for each zone
    for zone in zones:
        zone['exchanges'] = list(zone['exchanges'])

        # Determine side
        if zone['long_count'] > zone['short_count']:
            zone['side'] = 'long'
        else:
            zone['side'] = 'short'

        # Determine confidence based on number of exchanges
        num_exchanges = len(zone['exchanges'])
        if num_exchanges >= 3:
            zone['confidence'] = 'high'
        elif num_exchanges == 2:
            zone['confidence'] = 'medium'
        else:
            zone['confidence'] = 'low'

        # Clean up temporary fields
        del zone['long_count']
        del zone['short_count']

    # Sort by total size (largest first)
    zones.sort(key=lambda z: z['total_size_usd'], reverse=True)

    return zones


@router.get("/api/liquidations/zones", response_model=LiquidationZonesResponse)
async def get_liquidation_zones(
    symbol: str = Query("BTCUSDT", description="Trading symbol to analyze"),
    clustering_pct: float = Query(2.0, ge=0.1, le=10.0, description="Price clustering percentage (0.1-10%)"),
    lookback_hours: int = Query(1, ge=1, le=24, description="Hours of liquidation history to analyze"),
    min_zone_size: float = Query(10000, ge=0, description="Minimum USD size to include zone (default $10K)"),
    cascade_threshold: float = Query(200000, ge=0, description="USD threshold for cascade detection (default $200K)"),
):
    """
    Get aggregated liquidation zones across all configured exchanges.

    Returns price levels where significant liquidations are clustered,
    useful for:
    - Identifying support/resistance levels
    - Detecting cascade risks
    - Visualizing liquidation heatmaps on charts

    **Clustering Logic:**
    Liquidations within `clustering_pct` of each other are grouped into zones.
    For example, with 2% clustering:
    - $93,500 and $94,000 would be separate zones
    - $93,500 and $93,600 would be grouped into one zone

    **Confidence Levels:**
    - **high**: Zone confirmed by 3+ exchanges
    - **medium**: Zone confirmed by 2 exchanges
    - **low**: Zone from 1 exchange only

    **Cascade Detection:**
    Alerts when any zone exceeds the cascade threshold (default $200K).
    """

    try:
        # Get liquidation collector from app state (injected at startup)
        from src.core.di.container import get_liquidation_collector
        collector = get_liquidation_collector()

        if not collector:
            raise HTTPException(
                status_code=503,
                detail="Liquidation collector not available"
            )

        # Get liquidations from all exchanges
        all_liquidations = []
        exchanges_queried = []

        # Query each exchange
        for exchange_name in ['bybit', 'binance', 'okx']:
            try:
                liqs = collector.get_recent_liquidations(
                    symbol=symbol,
                    exchange=exchange_name,
                    minutes=lookback_hours * 60
                )
                if liqs:
                    all_liquidations.extend(liqs)
                    exchanges_queried.append(exchange_name)
                    logger.debug(f"Found {len(liqs)} liquidations from {exchange_name}")
            except Exception as e:
                logger.warning(f"Error fetching liquidations from {exchange_name}: {e}")
                continue

        logger.info(f"Total liquidations collected: {len(all_liquidations)} from {len(exchanges_queried)} exchanges")

        # Cluster into zones
        zone_dicts = cluster_liquidations_by_price(all_liquidations, clustering_pct)

        # Filter by minimum size
        zone_dicts = [z for z in zone_dicts if z['total_size_usd'] >= min_zone_size]

        # Convert to response models
        zones = [
            LiquidationZone(
                price=z['price'],
                total_size_usd=z['total_size_usd'],
                count=z['count'],
                exchanges=z['exchanges'],
                side=z['side'],
                confidence=z['confidence']
            )
            for z in zone_dicts
        ]

        # Detect cascades
        cascade_detected = any(z.total_size_usd >= cascade_threshold for z in zones)
        cascade_zone = max(zones, key=lambda z: z.total_size_usd) if cascade_detected and zones else None

        return LiquidationZonesResponse(
            symbol=symbol,
            zones=zones,
            cascade_detected=cascade_detected,
            cascade_price=cascade_zone.price if cascade_zone else None,
            cascade_size=cascade_zone.total_size_usd if cascade_zone else None,
            total_exchanges=len(exchanges_queried),
            lookback_hours=lookback_hours,
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating liquidation zones: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate liquidation zones: {str(e)}"
        )


@router.get("/api/liquidations/summary")
async def get_liquidation_summary(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    hours: int = Query(24, ge=1, le=168, description="Hours of history (max 1 week)")
):
    """
    Get summary statistics of liquidations over a time period.

    Returns:
    - Total liquidation volume (USD)
    - Long vs short liquidation ratio
    - Largest single liquidation
    - Liquidations per exchange breakdown
    """

    try:
        from src.core.di.container import get_liquidation_collector
        collector = get_liquidation_collector()

        if not collector:
            raise HTTPException(status_code=503, detail="Liquidation collector not available")

        # Get all liquidations
        all_liqs = collector.get_recent_liquidations(symbol, minutes=hours * 60)

        if not all_liqs:
            return {
                "symbol": symbol,
                "period_hours": hours,
                "total_volume_usd": 0,
                "total_count": 0,
                "long_liquidations": 0,
                "short_liquidations": 0,
                "largest_liquidation_usd": 0,
                "exchanges": {}
            }

        # Calculate statistics
        total_volume = sum(liq.liquidated_amount_usd for liq in all_liqs)
        long_count = sum(1 for liq in all_liqs if 'LONG' in liq.liquidation_type.value.upper())
        short_count = len(all_liqs) - long_count
        largest = max(all_liqs, key=lambda l: l.liquidated_amount_usd)

        # Per-exchange breakdown
        exchange_stats = defaultdict(lambda: {'count': 0, 'volume_usd': 0})
        for liq in all_liqs:
            exchange_stats[liq.exchange]['count'] += 1
            exchange_stats[liq.exchange]['volume_usd'] += liq.liquidated_amount_usd

        return {
            "symbol": symbol,
            "period_hours": hours,
            "total_volume_usd": total_volume,
            "total_count": len(all_liqs),
            "long_liquidations": long_count,
            "short_liquidations": short_count,
            "largest_liquidation_usd": largest.liquidated_amount_usd,
            "largest_liquidation_price": largest.trigger_price,
            "exchanges": dict(exchange_stats),
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating liquidation summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
