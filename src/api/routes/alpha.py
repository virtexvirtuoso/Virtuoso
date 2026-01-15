"""
API routes for alpha opportunities.

SERVICE RESPONSIBILITY: virtuoso-web reads CACHED data only.
All confluence computation happens in virtuoso-trading and is written to cache.

Cache keys used:
- analysis:signals - Contains all signals with scores
- confluence:breakdown:{symbol} - Detailed confluence breakdown
- confluence:score:{symbol} - Simple score value
- alpha:opportunities - Pre-computed alpha opportunities (if available)

DO NOT instantiate ConfluenceAnalyzer or AlphaScannerEngine here.
See CLAUDE.md "Service Responsibilities" for details.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import time
from datetime import datetime, timezone
import logging
import json

import aiomcache

from ..models.alpha import AlphaScanRequest, AlphaScanResponse, AlphaOpportunity

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_cache_client():
    """Get memcached client for reading cached confluence data."""
    return aiomcache.Client('localhost', 11211, pool_size=2)


async def _read_cached_opportunities(
    limit: int = 10,
    min_score: float = 70.0,
    timeframe: Optional[str] = None,
    exchange: Optional[str] = None,
    symbols: Optional[List[str]] = None
) -> List[AlphaOpportunity]:
    """
    Read alpha opportunities from cache.

    Data flow: virtuoso-trading -> memcached -> virtuoso-web (here)

    This function reads pre-computed confluence scores from cache
    and converts them to AlphaOpportunity objects.
    """
    opportunities = []

    try:
        client = await get_cache_client()

        # First, try to get pre-computed alpha opportunities
        alpha_data = await client.get(b'alpha:opportunities')
        if alpha_data:
            cached_opps = json.loads(alpha_data.decode())
            if isinstance(cached_opps, list):
                for opp_data in cached_opps[:limit]:
                    score = opp_data.get('score', 0)
                    if score >= min_score:
                        try:
                            opportunity = AlphaOpportunity(
                                symbol=opp_data.get('symbol', 'UNKNOWN'),
                                exchange=exchange or opp_data.get('exchange', 'bybit'),
                                score=score,
                                potential_return=opp_data.get('potential_return', 0.05),
                                confidence=opp_data.get('confidence', 0.5),
                                risk_level=opp_data.get('risk_level', 'MEDIUM'),
                                timeframe=timeframe or opp_data.get('timeframe', '1h'),
                                entry_price=opp_data.get('entry_price', 0),
                                target_price=opp_data.get('target_price', 0),
                                stop_loss=opp_data.get('stop_loss', 0),
                                analysis=opp_data.get('analysis', {}),
                                signals=opp_data.get('signals', []),
                                timestamp=opp_data.get('timestamp', int(time.time() * 1000))
                            )
                            opportunities.append(opportunity)
                        except Exception as e:
                            logger.debug(f"Skipping malformed opportunity: {e}")
                            continue

                await client.close()
                if opportunities:
                    return opportunities[:limit]

        # Fallback: Read from analysis:signals cache
        signals_data = await client.get(b'analysis:signals')
        if signals_data:
            signals = json.loads(signals_data.decode())
            signal_list = signals.get('signals', [])

            for signal in signal_list:
                symbol = signal.get('symbol', '')

                # Filter by symbols if specified
                if symbols and symbol not in symbols:
                    continue

                score = signal.get('score', signal.get('confluence_score', 0))
                if score < min_score:
                    continue

                # Get additional breakdown from cache if available
                breakdown = {}
                try:
                    breakdown_data = await client.get(f'confluence:breakdown:{symbol}'.encode())
                    if breakdown_data:
                        breakdown = json.loads(breakdown_data.decode())
                except Exception:
                    pass

                # Build opportunity from signal data
                current_price = signal.get('price', signal.get('current_price', 0))
                sentiment = signal.get('sentiment', 'NEUTRAL')

                # Calculate price levels based on sentiment
                if sentiment == 'BULLISH':
                    target_price = current_price * 1.03  # 3% target
                    stop_loss = current_price * 0.98  # 2% stop
                elif sentiment == 'BEARISH':
                    target_price = current_price * 0.97  # 3% down target
                    stop_loss = current_price * 1.02  # 2% stop
                else:
                    target_price = current_price * 1.02
                    stop_loss = current_price * 0.98

                try:
                    opportunity = AlphaOpportunity(
                        symbol=symbol,
                        exchange=exchange or signal.get('exchange', 'bybit'),
                        score=score,
                        potential_return=abs(target_price - current_price) / current_price if current_price else 0.03,
                        confidence=signal.get('reliability', breakdown.get('reliability', 0.5)),
                        risk_level=_categorize_risk(score),
                        timeframe=timeframe or signal.get('timeframe', '1h'),
                        entry_price=current_price,
                        target_price=target_price,
                        stop_loss=stop_loss,
                        analysis={
                            "trend": sentiment,
                            "momentum": "STRONG" if score > 70 else "MODERATE" if score > 50 else "WEAK",
                            "volume": breakdown.get('components', {}).get('volume', {}).get('interpretation', 'N/A'),
                            "technical": breakdown.get('components', {}).get('technical', {}).get('interpretation', 'N/A')
                        },
                        signals=signal.get('interpretations', signal.get('signals', [])) if isinstance(signal.get('interpretations', signal.get('signals', [])), list) else [],
                        timestamp=signal.get('timestamp', int(time.time() * 1000))
                    )
                    opportunities.append(opportunity)
                except Exception as e:
                    logger.debug(f"Skipping signal {symbol}: {e}")
                    continue

        await client.close()

        # Sort by score descending and limit
        opportunities.sort(key=lambda x: x.score, reverse=True)
        return opportunities[:limit]

    except Exception as e:
        logger.warning(f"Error reading cached opportunities: {e}")
        return []


def _categorize_risk(score: float) -> str:
    """Categorize risk level based on score."""
    if score >= 80:
        return "LOW"
    elif score >= 60:
        return "MEDIUM"
    else:
        return "HIGH"


@router.post("/scan", response_model=AlphaScanResponse)
async def scan_alpha_opportunities(
    scan_request: AlphaScanRequest
) -> AlphaScanResponse:
    """
    Get alpha opportunities from cache.

    NOTE: This endpoint reads CACHED data computed by virtuoso-trading.
    It does NOT perform real-time scanning in virtuoso-web.
    """
    start_time = time.time()

    try:
        opportunities = await _read_cached_opportunities(
            limit=scan_request.max_results,
            min_score=scan_request.min_score,
            timeframe=scan_request.timeframes[0] if scan_request.timeframes else None,
            symbols=scan_request.symbols
        )

        scan_duration = int((time.time() - start_time) * 1000)

        return AlphaScanResponse(
            opportunities=opportunities,
            scan_timestamp=datetime.now(timezone.utc),
            total_symbols_scanned=len(scan_request.symbols) if scan_request.symbols else len(opportunities),
            scan_duration_ms=scan_duration,
            metadata={
                "timeframes_analyzed": ",".join(scan_request.timeframes) if scan_request.timeframes else "1h",
                "min_score_threshold": scan_request.min_score,
                "opportunities_found": len(opportunities),
                "source": "cached"  # Indicate data is from cache
            }
        )

    except Exception as e:
        logger.error(f"Error in scan_alpha_opportunities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch cached opportunities: {str(e)}")


@router.get("/opportunities", response_model=List[AlphaOpportunity])
async def get_opportunities(
    limit: int = Query(default=10, ge=1, le=50),
    min_score: float = Query(default=70.0, ge=0, le=100),
    timeframe: Optional[str] = Query(default=None),
    exchange: Optional[str] = Query(default=None)
) -> List[AlphaOpportunity]:
    """
    Get alpha opportunities from cache.

    NOTE: Returns cached confluence data. Real-time computation
    happens in virtuoso-trading service.
    """
    try:
        opportunities = await _read_cached_opportunities(
            limit=limit,
            min_score=min_score,
            timeframe=timeframe,
            exchange=exchange
        )

        if not opportunities:
            logger.info("No cached opportunities found, returning empty list")
        else:
            logger.info(f"Returning {len(opportunities)} cached alpha opportunities")

        return opportunities

    except Exception as e:
        logger.error(f"Error in get_opportunities: {e}")
        return []


@router.get("/opportunities/top", response_model=List[AlphaOpportunity])
async def get_top_opportunities(
    limit: int = Query(default=10, ge=1, le=50),
    min_score: float = Query(default=70.0, ge=0, le=100),
    timeframe: Optional[str] = Query(default=None),
    exchange: Optional[str] = Query(default=None)
) -> List[AlphaOpportunity]:
    """
    Get top alpha opportunities from cache.

    NOTE: This is the primary endpoint polled by dashboards (~5min interval).
    It reads CACHED data only - NO ConfluenceAnalyzer instantiation.
    """
    try:
        opportunities = await _read_cached_opportunities(
            limit=limit,
            min_score=min_score,
            timeframe=timeframe,
            exchange=exchange
        )

        return opportunities

    except Exception as e:
        logger.error(f"Error in get_top_opportunities: {e}")
        # Return empty list instead of 500 error for graceful degradation
        return []


@router.get("/opportunities/{symbol}", response_model=Optional[AlphaOpportunity])
async def get_symbol_opportunity(
    symbol: str,
    exchange: Optional[str] = Query(default=None),
    timeframe: str = Query(default="1h")
) -> Optional[AlphaOpportunity]:
    """
    Get alpha opportunity for a specific symbol from cache.

    NOTE: Returns cached confluence data for the symbol.
    """
    try:
        opportunities = await _read_cached_opportunities(
            limit=1,
            min_score=0.0,  # Return regardless of score
            timeframe=timeframe,
            exchange=exchange,
            symbols=[symbol.upper()]
        )

        return opportunities[0] if opportunities else None

    except Exception as e:
        logger.error(f"Error in get_symbol_opportunity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch cached data: {str(e)}")


@router.get("/scan/status")
async def get_scan_status() -> dict:
    """Get current cache status for alpha scanning."""
    try:
        client = await get_cache_client()

        # Check if we have signals data in cache
        signals_data = await client.get(b'analysis:signals')
        has_signals = signals_data is not None

        signal_count = 0
        if has_signals:
            try:
                signals = json.loads(signals_data.decode())
                signal_count = len(signals.get('signals', []))
            except Exception:
                pass

        await client.close()

        return {
            "status": "active" if has_signals else "no_data",
            "last_check": datetime.now(timezone.utc).isoformat(),
            "data_source": "memcached",
            "cached_signals": signal_count,
            "supported_exchanges": ["binance", "bybit"],
            "supported_timeframes": ["15m", "1h", "4h", "1d"],
            "note": "Data computed by virtuoso-trading, read from cache"
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "last_check": datetime.now(timezone.utc).isoformat()
        }


@router.get("/health")
async def alpha_scanner_health() -> dict:
    """
    Health check for alpha scanner cache access.

    NOTE: Only checks cache connectivity, does NOT instantiate AlphaScannerEngine.
    """
    try:
        client = await get_cache_client()

        # Test cache connectivity
        test_result = await client.get(b'analysis:signals')
        cache_connected = True
        signal_count = 0

        if test_result:
            try:
                signals = json.loads(test_result.decode())
                signal_count = len(signals.get('signals', []))
            except Exception:
                pass

        await client.close()

        return {
            "status": "healthy" if cache_connected else "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cache_connected": cache_connected,
            "cached_signals": signal_count,
            "note": "Health check reads cache only - computation in virtuoso-trading"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }
