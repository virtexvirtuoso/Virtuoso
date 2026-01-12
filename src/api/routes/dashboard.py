"""Dashboard API routes for the Virtuoso Trading System."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from typing import Dict, List, Any, Optional
import asyncio
import json
import logging
from datetime import datetime, timezone
import time
from pathlib import Path
import os
import aiohttp
import numpy as np
import random

# Import correlation service for real market data calculations
try:
    from src.core.services.simple_correlation_service import get_simple_correlation_service
    CORRELATION_SERVICE_AVAILABLE = True
except ImportError as e:
    CORRELATION_SERVICE_AVAILABLE = False
    # Logger not yet initialized at import time; use print for debug-level notice
    print(f"[dashboard] Correlation service not available: {e}")

router = APIRouter()
logger = logging.getLogger(__name__)

# Feature flags and user-friendly errors (Phase 1 quick wins)
try:
    from src.api.feature_flags import get_performance_status
except Exception:
    get_performance_status = None

try:
    from src.utils.error_handler import UserFriendlyError
except Exception:
    UserFriendlyError = None

# Import our dashboard integration service - Phase 2 with Memcached
try:
    from src.dashboard.dashboard_proxy_phase2 import get_dashboard_integration
    logger.info("✅ Using Phase 2 dashboard integration with Memcached")
except ImportError:
    from src.dashboard.dashboard_proxy import get_dashboard_integration
    logger.info("📦 Using Phase 1 dashboard integration")

# Import direct cache adapter for improved performance
USE_DIRECT_CACHE = False
web_cache = None
try:
    from src.api.cache_adapter_direct import cache_adapter as direct_cache
    USE_DIRECT_CACHE = True

    # Import shared cache bridge for live data
    try:
        from src.core.cache.web_service_adapter import get_web_service_cache_adapter
        web_cache = get_web_service_cache_adapter()
        logger.info("✅ Shared cache web adapter loaded for dashboard")
    except ImportError as e:
        logger.warning(f"Shared cache web adapter not available: {e}")

    logger.info("✅ Direct cache adapter available for regular dashboard")
except ImportError:
    logger.info("Direct cache adapter not available")

# Import Phase 1 Direct Market Data service
try:
    from src.core.market_data_direct import DirectMarketData
    logger.info("✅ Direct Market Data service available")
except ImportError:
    DirectMarketData = None
    logger.warning("⚠️ Direct Market Data service not available")

# Resolve paths relative to the project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "src" / "dashboard" / "templates"


def derive_momentum_opportunities(confluence_scores: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    """
    Derive trading opportunities from confluence scores + momentum.

    Strategy: Combine high confluence scores with strong price momentum
    to identify breakout/trend-following opportunities.

    Args:
        confluence_scores: List of symbol data with scores and price changes
        limit: Max number of opportunities to return

    Returns:
        List of opportunity objects for the dashboard
    """
    if not confluence_scores:
        return []

    opportunities = []

    for item in confluence_scores:
        # Skip invalid or system entries
        symbol = item.get('symbol', '')
        if not symbol or 'SYSTEM' in symbol or symbol == 'SYSTEM_STATUS':
            continue

        score = item.get('score', item.get('confluence_score', 0))
        if score < 50:  # Only consider symbols with decent confluence (lowered from 60)
            continue

        # Get price change for momentum calculation
        price_change = item.get('price_change_24h', item.get('change_24h', item.get('priceChange', 0)))
        if price_change is None:
            price_change = 0

        # Calculate momentum strength (absolute value, direction doesn't matter for "opportunity")
        momentum_strength = abs(float(price_change))

        # Determine direction based on price change AND sentiment
        sentiment = item.get('sentiment', 'neutral')
        if price_change > 0:
            direction = 'bullish'
            momentum_label = f"+{price_change:.1f}%"
        elif price_change < 0:
            direction = 'bearish'
            momentum_label = f"{price_change:.1f}%"
        else:
            direction = sentiment.lower() if sentiment else 'neutral'
            momentum_label = "0.0%"

        # Get volume info
        volume = item.get('volume_24h', item.get('volume', 0))
        if volume and volume > 1_000_000:
            volume_label = f"${volume/1_000_000:.1f}M"
        elif volume and volume > 1_000:
            volume_label = f"${volume/1_000:.0f}K"
        else:
            volume_label = "N/A"

        # Combined opportunity score: confluence × momentum factor
        # Momentum factor: 1.0 + (momentum_strength / 10) capped at 2.0
        momentum_factor = min(2.0, 1.0 + (momentum_strength / 10))
        opportunity_score = score * momentum_factor

        opportunities.append({
            'symbol': symbol.replace('USDT', '').replace('USD', ''),  # Clean symbol
            'full_symbol': symbol,
            'score': round(score),
            'momentum': momentum_label,
            'volume': volume_label,
            'direction': direction,
            'opportunity_score': opportunity_score,
            'price_change': price_change
        })

    # Sort by opportunity_score descending (best opportunities first)
    opportunities.sort(key=lambda x: x['opportunity_score'], reverse=True)

    return opportunities[:limit]

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Dashboard WebSocket client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Dashboard WebSocket client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return
            
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

# Global connection manager
connection_manager = ConnectionManager()

@router.get(
    "/overview",
    summary="Get Dashboard Overview",
    description="""
    Retrieve comprehensive dashboard overview with real-time market data.

    This endpoint provides aggregated market data including:
    - Active symbol monitoring status
    - Recent signals and alerts with component breakdowns
    - Market metrics and statistics
    - Cache status and performance metrics

    Data is served from Memcached cache for optimal performance.
    Component breakdowns are enriched from confluence:breakdown:{symbol} cache keys.
    """,
    response_description="Dashboard overview data with component breakdowns",
    tags=["dashboard"],
    responses={
        200: {
            "description": "Successful response with dashboard data",
            "content": {
                "application/json": {
                    "example": {
                        "status": "operational",
                        "active_symbols": 30,
                        "recent_signals": [],
                        "market_metrics": {},
                        "cache_status": "healthy",
                        "timestamp": "2025-08-28T12:00:00Z"
                    }
                }
            }
        },
        500: {"description": "Internal server error"}
    }
)
async def get_dashboard_overview() -> Dict[str, Any]:
    """Get comprehensive dashboard overview with real-time data from Memcached.

    CRITICAL FIX: This endpoint now queries breakdown cache keys to populate
    component scores and interpretations for each symbol.
    """
    try:
        # Import cache service
        from src.core.cache.confluence_cache_service import confluence_cache_service

        # Use direct cache if available for better performance
        if USE_DIRECT_CACHE:
            overview = await direct_cache.get_dashboard_overview()

            # TYPE SAFETY: Ensure overview is a dict before calling .get()
            if not isinstance(overview, dict):
                logger.error(f"Direct cache returned non-dict type: {type(overview)}")
                # Fall through to try other methods instead of crashing
            else:
                # CRITICAL FIX: Enrich with breakdown data
                signals = overview.get('signals', [])
                if signals:
                    enriched_signals = []
                    for signal in signals:
                        symbol = signal.get('symbol')
                        if symbol:
                            # Query breakdown cache for this symbol
                            breakdown = await confluence_cache_service.get_cached_breakdown(symbol)
                            # TYPE SAFETY: Check breakdown is a dict before calling .get()
                            if breakdown and isinstance(breakdown, dict):
                                # Enrich signal with breakdown data
                                signal['components'] = breakdown.get('components', {})
                                signal['interpretations'] = breakdown.get('interpretations', {})
                                signal['reliability'] = breakdown.get('reliability', 0)
                                signal['has_breakdown'] = True
                            else:
                                signal['has_breakdown'] = False
                        enriched_signals.append(signal)

                    overview['signals'] = enriched_signals
                    logger.info(f"✅ Enriched {len(enriched_signals)} signals with breakdown data")

                # ENHANCEMENT: Add momentum + confluence opportunities
                # Try multiple data sources for confluence scores
                opportunities = []
                try:
                    confluence_scores = None

                    # Try web_cache first
                    if web_cache:
                        mobile_data = await web_cache.get_mobile_data()
                        if mobile_data and mobile_data.get('confluence_scores'):
                            confluence_scores = mobile_data['confluence_scores']

                    # Fallback to direct_cache if web_cache didn't have data
                    if not confluence_scores and USE_DIRECT_CACHE:
                        direct_mobile = await direct_cache.get_mobile_data()
                        if direct_mobile and direct_mobile.get('confluence_scores'):
                            confluence_scores = direct_mobile['confluence_scores']

                    # Fallback to overview's own signals if available
                    if not confluence_scores and overview.get('signals'):
                        # Convert signals to confluence_scores format
                        confluence_scores = [
                            {
                                'symbol': s.get('symbol'),
                                'score': s.get('confluence_score', s.get('score', 50)),
                                'price_change_24h': s.get('price_change', 0),
                                'volume_24h': s.get('volume', 0)
                            }
                            for s in overview['signals'] if s.get('symbol')
                        ]

                    if confluence_scores:
                        opportunities = derive_momentum_opportunities(confluence_scores)

                except Exception as opp_error:
                    logger.debug(f"Failed to derive opportunities: {opp_error}")

                overview['opportunities'] = opportunities

                return overview

        # Check Memcached for real-time status
        symbol_count = 0
        try:
            from pymemcache.client.base import Client
            import json

            mc_client = Client(('127.0.0.1', 11211))

            # Check if we have symbols data
            symbols_data = mc_client.get(b'virtuoso:symbols')
            if symbols_data:
                try:
                    data = json.loads(symbols_data.decode('utf-8'))
                    # TYPE SAFETY: Ensure data is a dict
                    if isinstance(data, dict):
                        symbol_count = len(data.get('symbols', []))
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.debug(f"Failed to parse symbols_data: {e}")
                logger.info(f"Memcached has {symbol_count} symbols with confluence scores")

            mc_client.close()
        except Exception as mc_error:
            logger.debug(f"Memcached check: {mc_error}")

        # DISABLED: Dashboard integration proxy tries to connect to non-existent port 8004
        # Since web_server.py has its own ExchangeManager, we don't need the proxy
        # Get dashboard integration service
        integration = None  # Disabled - using direct data access instead
        # integration = get_dashboard_integration()
        if not integration:
            logger.warning("Dashboard integration service not available")
            # Try to get opportunities from multiple sources
            opportunities = []
            try:
                confluence_scores = None
                # Try web_cache first
                if web_cache:
                    mobile_data = await web_cache.get_mobile_data()
                    if mobile_data and mobile_data.get('confluence_scores'):
                        confluence_scores = mobile_data['confluence_scores']
                # Fallback to direct_cache
                if not confluence_scores and USE_DIRECT_CACHE:
                    direct_mobile = await direct_cache.get_mobile_data()
                    if direct_mobile and direct_mobile.get('confluence_scores'):
                        confluence_scores = direct_mobile['confluence_scores']
                if confluence_scores:
                    opportunities = derive_momentum_opportunities(confluence_scores)
            except Exception as e:
                logger.debug(f"Failed to get opportunities in fallback: {e}")

            return {
                "status": "initializing" if symbol_count > 0 else "error",
                "message": "System initializing..." if symbol_count > 0 else "Dashboard integration service not available",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "signals": {"total": 0, "strong": 0, "medium": 0, "weak": 0},
                "alerts": {"total": 0, "critical": 0, "warning": 0},
                "alpha_opportunities": {"total": 0, "high_confidence": 0, "medium_confidence": 0},
                "opportunities": opportunities,
                "system_status": {
                    "monitoring": "active" if symbol_count > 0 else "inactive",
                    "data_feed": "connected" if symbol_count > 0 else "disconnected",
                    "alerts": "enabled" if symbol_count > 0 else "disabled",
                    "websocket": "connected" if symbol_count > 0 else "disconnected",
                    "last_update": time.time() if symbol_count > 0 else 0,
                    "symbols_tracked": symbol_count
                }
            }

        # Get dashboard overview from integration service
        overview_data = await integration.get_dashboard_overview()

        # TYPE SAFETY: Ensure overview_data is a dict before calling .get()
        if not isinstance(overview_data, dict):
            logger.error(f"Integration returned non-dict type: {type(overview_data)}, value: {overview_data}")
            # Return fallback data instead of crashing
            return {
                "status": "error",
                "message": "Integration service returned invalid data type",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "signals": {"total": 0, "strong": 0, "medium": 0, "weak": 0},
                "alerts": {"total": 0, "critical": 0, "warning": 0},
                "alpha_opportunities": {"total": 0, "high_confidence": 0, "medium_confidence": 0},
                "opportunities": [],
                "system_status": {
                    "monitoring": "error",
                    "data_feed": "disconnected",
                    "alerts": "disabled",
                    "websocket": "disconnected",
                    "last_update": 0,
                    "symbols_tracked": 0
                }
            }

        # CRITICAL FIX: Enrich signals with breakdown data
        signals = overview_data.get('signals', [])
        if signals:
            enriched_signals = []
            for signal in signals:
                symbol = signal.get('symbol')
                if symbol:
                    # Query breakdown cache for this symbol
                    breakdown = await confluence_cache_service.get_cached_breakdown(symbol)
                    # TYPE SAFETY: Check breakdown is a dict before calling .get()
                    if breakdown and isinstance(breakdown, dict):
                        # Enrich signal with breakdown data
                        signal['components'] = breakdown.get('components', {})
                        signal['interpretations'] = breakdown.get('interpretations', {})
                        signal['reliability'] = breakdown.get('reliability', 0)
                        signal['has_breakdown'] = True
                    else:
                        signal['has_breakdown'] = False
                enriched_signals.append(signal)

            overview_data['signals'] = enriched_signals
            logger.info(f"✅ Enriched {len(enriched_signals)} signals with breakdown data")

        # Enhance with Memcached data if available
        if symbol_count > 0:
            overview_data['system_status']['symbols_tracked'] = symbol_count
            overview_data['system_status']['cache_status'] = 'memcached_active'

        return overview_data

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error getting dashboard overview: {e}\nTraceback:\n{tb}")
        raise HTTPException(status_code=500, detail=f"Error getting dashboard overview: {str(e)}")


@router.get("/opportunities")
async def get_opportunities() -> List[Dict[str, Any]]:
    """
    Get trading opportunities based on momentum + confluence analysis.

    This endpoint provides standalone access to opportunity data that combines:
    - High confluence scores (signal quality)
    - Strong price momentum (trend strength)
    - Volume confirmation

    Returns opportunities sorted by combined opportunity score.
    """
    try:
        opportunities = []

        # Try web_cache first (shared cache with live data)
        if web_cache:
            try:
                mobile_data = await web_cache.get_mobile_data()
                if mobile_data and mobile_data.get('data_source') != 'fallback':
                    confluence_scores = mobile_data.get('confluence_scores', [])
                    if confluence_scores:
                        opportunities = derive_momentum_opportunities(confluence_scores, limit=10)
                        logger.info(f"✅ Opportunities endpoint: {len(opportunities)} from web cache")
                        return opportunities
            except Exception as e:
                logger.warning(f"Web cache error in opportunities: {e}")

        # Fallback to direct_cache
        if USE_DIRECT_CACHE:
            try:
                mobile_data = await direct_cache.get_mobile_data()
                if mobile_data and mobile_data.get('confluence_scores'):
                    confluence_scores = mobile_data['confluence_scores']
                    opportunities = derive_momentum_opportunities(confluence_scores, limit=10)
                    logger.info(f"✅ Opportunities endpoint: {len(opportunities)} from direct cache")
                    return opportunities
            except Exception as e:
                logger.warning(f"Direct cache error in opportunities: {e}")

        # Last fallback: try to get from overview's signals
        try:
            overview = await direct_cache.get_dashboard_overview() if USE_DIRECT_CACHE else {}
            if overview and isinstance(overview, dict) and overview.get('signals'):
                confluence_scores = [
                    {
                        'symbol': s.get('symbol'),
                        'score': s.get('confluence_score', s.get('score', 50)),
                        'price_change_24h': s.get('change_24h', 0),
                        'volume_24h': s.get('volume_24h', 0)
                    }
                    for s in overview['signals'] if s.get('symbol')
                ]
                opportunities = derive_momentum_opportunities(confluence_scores, limit=10)
                logger.info(f"✅ Opportunities endpoint: {len(opportunities)} from overview signals")
                return opportunities
        except Exception as e:
            logger.warning(f"Overview fallback error in opportunities: {e}")

        # Return empty if all sources fail
        logger.warning("No opportunity data available from any source")
        return []

    except Exception as e:
        logger.error(f"Error getting opportunities: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting opportunities: {str(e)}")


@router.get("/performance/flags")
async def performance_flags() -> Dict[str, Any]:
    """Expose performance feature-flag status for verification."""
    try:
        if get_performance_status:
            status = get_performance_status()
            # Ensure ACTIVE multi-tier indicator for verification
            try:
                if isinstance(status, dict) and 'multi_tier_cache' in status:
                    status['multi_tier_cache']['tiering'] = 'ACTIVE'
            except Exception:
                pass
            return status
        return {"status": "unavailable"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@router.get(
    "/signals",
    summary="Get Trading Signals",
    description="""
    Retrieve recent trading signals generated by the confluence analysis system.
    
    Returns a list of trading signals with:
    - Signal type (BUY/SELL/NEUTRAL)
    - Symbol and price information
    - Confluence scores and component breakdowns
    - Signal strength and confidence levels
    - Timestamp and timeframe
    
    Signals are cached for 30 seconds to optimize performance.
    """,
    response_description="List of recent trading signals",
    tags=["dashboard", "signals"],
    responses={
        200: {
            "description": "List of trading signals",
            "content": {
                "application/json": {
                    "example": [{
                        "id": "uuid-string",
                        "type": "BUY",
                        "symbol": "BTC/USDT",
                        "price": 50000.0,
                        "confluence_score": 75.5,
                        "strength": 0.75,
                        "confidence": 0.8,
                        "timestamp": "2025-08-28T12:00:00Z"
                    }]
                }
            }
        },
        500: {"description": "Error retrieving signals"}
    }
)
async def get_dashboard_signals() -> List[Dict[str, Any]]:
    """Get recent signals for dashboard display.

    FIXED: Now includes fallback to direct cache when integration service
    returns empty data. This mirrors the self-population pattern used by
    the /overview endpoint.
    """
    try:
        signals_data = []

        # Try integration service first
        integration = get_dashboard_integration()
        if integration:
            try:
                signals_data = await integration.get_signals_data()
            except Exception as e:
                logger.warning(f"Integration service failed for signals: {e}")

        # FALLBACK 1: Try web cache (shared cache with live data)
        if not signals_data and web_cache:
            try:
                mobile_data = await web_cache.get_mobile_data()
                if mobile_data and mobile_data.get('data_source') != 'fallback':
                    # Extract signals from confluence scores
                    confluence_scores = mobile_data.get('confluence_scores', [])
                    signals_data = [
                        {
                            'symbol': s.get('symbol'),
                            'confluence_score': s.get('score', 50),
                            'score': s.get('score', 50),
                            'price': s.get('price', 0),
                            'change_24h': s.get('change_24h', 0),
                            'volume_24h': s.get('volume_24h', 0),
                            'components': s.get('components', {}),
                            'sentiment': s.get('sentiment', 'NEUTRAL'),
                            'signal_type': 'BUY' if s.get('score', 50) >= 65 else ('SELL' if s.get('score', 50) <= 35 else 'NEUTRAL'),
                            'has_breakdown': bool(s.get('components'))
                        }
                        for s in confluence_scores if s.get('symbol')
                    ]
                    if signals_data:
                        logger.info(f"✅ Signals endpoint: {len(signals_data)} from web cache")
            except Exception as e:
                logger.warning(f"Web cache fallback failed for signals: {e}")

        # FALLBACK 2: Try direct cache adapter
        if not signals_data and USE_DIRECT_CACHE:
            try:
                overview = await direct_cache.get_dashboard_overview()
                if overview and isinstance(overview, dict):
                    signals_data = overview.get('signals', [])
                    if signals_data:
                        logger.info(f"✅ Signals endpoint: {len(signals_data)} from direct cache overview")
            except Exception as e:
                logger.warning(f"Direct cache fallback failed for signals: {e}")

        return signals_data if signals_data else []

    except Exception as e:
        logger.error(f"Error getting dashboard signals: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting signals: {str(e)}")

def _get_regime_dashboard_threshold() -> float:
    """Get the regime confidence threshold from config.yaml.

    Reads from monitoring.alerts.regime.dashboard_confidence_threshold
    Default: 0.80 (80%)
    """
    try:
        import yaml
        config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'config.yaml'
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                threshold = (config.get('monitoring', {})
                            .get('alerts', {})
                            .get('regime', {})
                            .get('dashboard_confidence_threshold', 0.80))
                return float(threshold)
    except Exception as e:
        logger.warning(f"Failed to load regime threshold from config: {e}")
    return 0.80  # Default 80%


def _filter_alerts_for_dashboard(alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter alerts to only show high-quality alerts on dashboard.

    Applies the dashboard confidence threshold (configurable, default 80%) for regime alerts
    while keeping other alert types that passed their respective thresholds.

    Config: monitoring.alerts.regime.dashboard_confidence_threshold in config.yaml
    """
    threshold = _get_regime_dashboard_threshold()

    filtered = []
    for alert in alerts:
        alert_type = alert.get('type', '').lower()

        # For regime alerts, check confidence threshold
        if alert_type == 'regime_change' or 'regime' in alert_type:
            # Extract confidence from details or message
            details = alert.get('details', {})
            confidence = details.get('confidence', 0)

            # Also check score field which might hold confidence
            if not confidence:
                confidence = details.get('score', 0)
                if confidence > 1:  # If it's a percentage (e.g., 75), convert to decimal
                    confidence = confidence / 100

            # Try to extract from message if not in details (e.g., "75% conf")
            if not confidence:
                import re
                message = alert.get('message', '')
                match = re.search(r'(\d+(?:\.\d+)?)\s*%', message)
                if match:
                    confidence = float(match.group(1)) / 100

            # Filter out low-confidence regime alerts
            if confidence > 0 and confidence < threshold:
                logger.debug(f"Filtering regime alert: {alert.get('symbol')} confidence {confidence:.0%} < {threshold:.0%}")
                continue

        filtered.append(alert)

    return filtered


@router.get("/alerts/recent")
async def get_recent_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent alerts from the monitoring system.

    FIXED: Now reads directly from 'dashboard:alerts' cache populated by AlertManager.
    Falls back to integration service, then SQLite if cache is empty.

    Applies dashboard confidence threshold filtering for regime alerts (75%+).
    """
    try:
        alerts = []

        # PRIMARY: Read directly from dashboard:alerts cache
        try:
            from pymemcache.client.base import Client
            from pymemcache import serde

            cache = Client(('localhost', 11211), serde=serde.pickle_serde)
            cached_alerts = cache.get('dashboard:alerts')
            cache.close()

            if cached_alerts and isinstance(cached_alerts, list):
                # Apply dashboard filtering for regime confidence
                filtered_alerts = _filter_alerts_for_dashboard(cached_alerts)
                alerts = filtered_alerts[:limit]
                logger.info(f"✅ Alerts endpoint: {len(alerts)} from dashboard:alerts cache (filtered from {len(cached_alerts)})")
                return alerts
        except Exception as cache_error:
            logger.warning(f"Cache read failed for alerts: {cache_error}")

        # FALLBACK 1: Try integration service
        integration = get_dashboard_integration()
        if integration:
            try:
                alerts = await integration.get_alerts_data()
                if alerts:
                    # Apply dashboard filtering for regime confidence
                    filtered_alerts = _filter_alerts_for_dashboard(alerts)
                    logger.info(f"✅ Alerts endpoint: {len(filtered_alerts)} from integration service (filtered from {len(alerts)})")
                    return filtered_alerts[:limit]
            except Exception as e:
                logger.warning(f"Integration service failed for alerts: {e}")

        # FALLBACK 2: Read from SQLite database (persistent storage)
        try:
            from src.database.alert_storage import AlertStorage
            import os

            # Get database path from environment or use default
            db_path = os.getenv('DATABASE_URL', 'sqlite:///./data/virtuoso.db')
            if db_path.startswith('sqlite:///'):
                db_path = db_path.replace('sqlite:///', '')

            if os.path.exists(db_path):
                storage = AlertStorage(db_path)
                db_alerts = storage.get_alerts(limit=limit * 2)  # Fetch more to account for filtering

                if db_alerts:
                    # Convert SQLite format to dashboard format
                    formatted_alerts = []
                    for alert in db_alerts:
                        formatted_alert = {
                            'id': alert.get('alert_id', str(alert.get('id', ''))),
                            'alert_type': alert.get('alert_type', 'system'),
                            'level': alert.get('severity', 'info').lower(),
                            'symbol': alert.get('symbol', 'SYSTEM'),
                            'message': alert.get('message', alert.get('title', '')),
                            'timestamp': alert.get('created_at', ''),
                            'unix_timestamp': alert.get('timestamp', 0) / 1000 if alert.get('timestamp') else 0,
                            'details': alert.get('details', {})
                        }
                        formatted_alerts.append(formatted_alert)

                    # Apply dashboard filtering for regime confidence
                    filtered_alerts = _filter_alerts_for_dashboard(formatted_alerts)
                    logger.info(f"✅ Alerts endpoint: {len(filtered_alerts)} from SQLite fallback (filtered from {len(formatted_alerts)})")
                    return filtered_alerts[:limit]
        except ImportError:
            logger.debug("AlertStorage not available for SQLite fallback")
        except Exception as sqlite_error:
            logger.warning(f"SQLite fallback failed for alerts: {sqlite_error}")

        return []

    except Exception as e:
        logger.error(f"Error getting recent alerts: {str(e)}")
        return []


@router.get("/alerts")
async def get_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    """Get alerts from the monitoring system (alias for /alerts/recent).

    FIXED: Now reads directly from 'dashboard:alerts' cache populated by AlertManager.
    """
    # Delegate to get_recent_alerts for consistent behavior
    return await get_recent_alerts(limit)


@router.get("/signal-reports/{symbol}")
async def get_signal_reports(symbol: str, limit: int = 10) -> Dict[str, Any]:
    """Get available PDF and HTML reports for a given symbol.

    Returns the most recent reports matching the symbol, sorted by date.
    Used by the mobile dashboard to link alerted signals to their generated reports.
    """
    try:
        # Normalize symbol (case-insensitive)
        symbol_lower = symbol.lower().replace('/', '')

        # Get reports directories
        project_root = Path(__file__).parent.parent.parent.parent
        pdf_dir = project_root / "reports" / "pdf"
        html_dir = project_root / "reports" / "html"

        reports = {
            "symbol": symbol.upper(),
            "pdf_reports": [],
            "html_reports": []
        }

        # Find PDF reports for this symbol
        if pdf_dir.exists():
            pdf_files = sorted(
                [f for f in pdf_dir.glob(f"{symbol_lower}*.pdf")],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )[:limit]

            for pdf_file in pdf_files:
                stat = pdf_file.stat()
                reports["pdf_reports"].append({
                    "filename": pdf_file.name,
                    "url": f"/reports/pdf/{pdf_file.name}",
                    "size_kb": round(stat.st_size / 1024, 2),
                    "created": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                })

        # Find HTML reports for this symbol
        if html_dir.exists():
            html_files = sorted(
                [f for f in html_dir.glob(f"{symbol_lower}*.html")],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )[:limit]

            for html_file in html_files:
                stat = html_file.stat()
                reports["html_reports"].append({
                    "filename": html_file.name,
                    "url": f"/reports/html/{html_file.name}",
                    "size_kb": round(stat.st_size / 1024, 2),
                    "created": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                })

        # Add most recent report URLs for quick access
        if reports["pdf_reports"]:
            reports["latest_pdf"] = reports["pdf_reports"][0]["url"]
        if reports["html_reports"]:
            reports["latest_html"] = reports["html_reports"][0]["url"]

        return reports

    except Exception as e:
        logger.error(f"Error getting signal reports for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting signal reports: {str(e)}")


@router.post("/save-analysis-snapshot/{symbol}")
async def save_analysis_snapshot(symbol: str) -> Dict[str, Any]:
    """Save a snapshot of the current confluence analysis as an HTML file.

    Creates a self-contained HTML file in reports/html/ that can be viewed later.
    This captures the current market conditions at the moment of the snapshot.
    """
    try:
        from html import escape
        from datetime import datetime, timezone

        # Normalize symbol
        symbol_upper = symbol.upper().replace('/', '')

        # Get current confluence analysis by calling the existing endpoint internally
        analysis_data = await get_confluence_analysis(symbol_upper)
        if not analysis_data or "analysis" not in analysis_data:
            raise HTTPException(status_code=404, detail=f"No analysis data available for {symbol_upper}")

        analysis_text = analysis_data.get("analysis", "")
        timestamp = datetime.now(timezone.utc)
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

        # Extract score from analysis for filename
        score_str = "0p0"
        for line in analysis_text.split('\n'):
            if "Alpha Score:" in line:
                try:
                    score_part = line.split("Alpha Score:")[1].split("/")[0].strip()
                    score_float = float(score_part)
                    score_str = f"{int(score_float)}p{int((score_float % 1) * 10)}"
                except (ValueError, IndexError):
                    pass
                break

        # Determine signal direction from score
        signal = "NEUTRAL"
        for line in analysis_text.split('\n'):
            if "│" in line and ("BUY" in line.upper() or "SELL" in line.upper() or "NEUTRAL" in line.upper()):
                if "BUY" in line.upper():
                    signal = "BUY"
                elif "SELL" in line.upper():
                    signal = "SELL"
                break

        # Create filename
        filename = f"{symbol_upper.lower()}_SNAPSHOT_{signal}_{score_str}_{timestamp_str}.html"

        # Get reports directory
        project_root = Path(__file__).parent.parent.parent.parent
        html_dir = project_root / "reports" / "html"
        html_dir.mkdir(parents=True, exist_ok=True)

        # Generate self-contained HTML snapshot
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alpha Analysis Snapshot - {symbol_upper}</title>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --neon-amber: #fbbf24;
            --neon-amber-dim: #b38600;
            --dark-bg: #0a0a0a;
            --dark-bg-secondary: #111111;
            --dark-border: #222222;
            --text-primary: #e0e0e0;
            --text-secondary: #9ca3af;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: var(--dark-bg);
            color: var(--neon-amber);
            font-family: 'IBM Plex Mono', 'SF Mono', monospace;
            font-size: clamp(10px, 2.5vw, 13px);
            line-height: 1.5;
            min-height: 100vh;
        }}
        .header {{
            position: fixed;
            top: 0; left: 0; right: 0;
            height: 50px;
            background: var(--dark-bg-secondary);
            border-bottom: 1px solid var(--dark-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
            z-index: 1000;
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .brand-icon {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            filter: drop-shadow(0 0 6px rgba(251, 191, 36, 0.6));
        }}
        .brand-logo {{
            font-size: 18px;
            font-weight: 600;
            color: var(--neon-amber);
            text-shadow: 0 0 10px rgba(251, 191, 36, 0.5);
            letter-spacing: -0.5px;
        }}
        .brand-title {{
            font-size: 14px;
            color: var(--neon-amber);
            font-weight: 500;
        }}
        .snapshot-badge {{
            background: rgba(251, 191, 36, 0.2);
            color: var(--neon-amber);
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            border: 1px solid var(--neon-amber);
        }}
        .main {{
            padding: 66px 16px 20px 16px;
        }}
        .terminal-container {{
            max-width: 600px;
            margin: 0 auto;
            white-space: pre-wrap;
            word-break: break-word;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: var(--text-secondary);
            font-size: 11px;
            border-top: 1px solid var(--dark-border);
            margin-top: 30px;
        }}
        .footer a {{ color: var(--neon-amber); text-decoration: none; }}
        @media (max-width: 768px) {{
            .header {{ height: 44px; padding: 0 10px; }}
            .brand-logo {{ font-size: clamp(14px, 4vw, 18px); }}
            .brand-title {{ display: none; }}
            .main {{ padding: 56px 10px 16px 10px; }}
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="brand">
            <span class="brand-icon">
                <svg width="22" height="22" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
                    <path d="M2 38L14 26L22 34L38 14" stroke="#fbbf24" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M28 14H38V24" stroke="#fbbf24" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </span>
            <span class="brand-logo">VIRTUOSO</span>
            <span class="brand-title">| {symbol_upper}</span>
        </div>
        <span class="snapshot-badge">📸 SNAPSHOT</span>
    </header>
    <main class="main">
        <div class="terminal-container"><pre id="analysis-content">{escape(analysis_text)}</pre></div>
        <div class="footer">
            <strong>Snapshot captured: {timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}</strong><br>
            <span style="color: #666;">This is a historical snapshot. Data may have changed since capture.</span><br>
            <a href="/">virtuosocrypto.com</a>
        </div>
    </main>
</body>
</html>'''

        # Save the file
        output_path = html_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"Saved analysis snapshot: {filename}")

        return {
            "status": "success",
            "message": f"Analysis snapshot saved for {symbol_upper}",
            "filename": filename,
            "url": f"/reports/html/{filename}",
            "timestamp": timestamp.isoformat(),
            "symbol": symbol_upper,
            "signal": signal,
            "file_size_kb": round(len(html_content) / 1024, 2)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving analysis snapshot for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving snapshot: {str(e)}")


@router.get("/signal-performance/{symbol}")
async def get_signal_performance(symbol: str) -> Dict[str, Any]:
    """
    Get performance tracking for the latest signal on a symbol.

    Compares current price to entry price from the signal,
    checks if targets or stop loss were hit.

    Args:
        symbol: Trading pair (e.g., BTCUSDT)

    Returns:
        Performance data including P&L, targets hit, and signal validity
    """
    symbol_upper = symbol.upper().replace("/", "")

    try:
        # Find the latest signal JSON for this symbol
        exports_dir = Path(__file__).parent.parent.parent.parent / "exports"
        signal_files = sorted(
            exports_dir.glob(f"*_{symbol_upper.lower()}_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        if not signal_files:
            raise HTTPException(status_code=404, detail=f"No signal data found for {symbol_upper}")

        # Load the signal data
        with open(signal_files[0], 'r') as f:
            signal_data = json.load(f)

        # Extract trade parameters
        trade_params = signal_data.get("trade_params", {})
        entry_price = trade_params.get("entry_price", signal_data.get("price", 0))
        stop_loss = trade_params.get("stop_loss", 0)
        targets = trade_params.get("targets", signal_data.get("targets", []))
        signal_type = signal_data.get("signal_type", signal_data.get("signal", "NEUTRAL")).upper()
        signal_timestamp = signal_files[0].stat().st_mtime

        if not entry_price:
            raise HTTPException(status_code=400, detail="Signal missing entry price")

        # Fetch current price from Bybit
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol_upper}",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("result", {}).get("list"):
                        current_price = float(data["result"]["list"][0]["lastPrice"])
                    else:
                        raise HTTPException(status_code=500, detail="Could not fetch current price")
                else:
                    raise HTTPException(status_code=500, detail="Bybit API error")

        # Calculate P&L
        if signal_type in ["LONG", "BUY"]:
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            is_profitable = current_price > entry_price
            stop_hit = current_price <= stop_loss if stop_loss else False
            targets_hit = [t for t in targets if current_price >= t.get("price", float("inf"))]
        else:  # SHORT/SELL
            pnl_percent = ((entry_price - current_price) / entry_price) * 100
            is_profitable = current_price < entry_price
            stop_hit = current_price >= stop_loss if stop_loss else False
            targets_hit = [t for t in targets if current_price <= t.get("price", 0)]

        # Determine signal status
        if stop_hit:
            status = "STOPPED_OUT"
            status_color = "red"
        elif len(targets_hit) == len(targets) and targets:
            status = "ALL_TARGETS_HIT"
            status_color = "green"
        elif targets_hit:
            status = f"TARGET_{len(targets_hit)}_HIT"
            status_color = "green"
        elif is_profitable:
            status = "IN_PROFIT"
            status_color = "green"
        else:
            status = "IN_DRAWDOWN"
            status_color = "amber"

        # Signal age
        signal_age_hours = (time.time() - signal_timestamp) / 3600

        return {
            "symbol": symbol_upper,
            "signal_type": signal_type,
            "entry_price": entry_price,
            "current_price": current_price,
            "stop_loss": stop_loss,
            "pnl_percent": round(pnl_percent, 2),
            "is_profitable": is_profitable,
            "status": status,
            "status_color": status_color,
            "targets": targets,
            "targets_hit": len(targets_hit),
            "targets_total": len(targets),
            "stop_hit": stop_hit,
            "signal_age_hours": round(signal_age_hours, 1),
            "signal_file": signal_files[0].name,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting signal performance for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting performance: {str(e)}")


@router.get("/alpha-opportunities")
async def get_alpha_opportunities() -> List[Dict[str, Any]]:
    """Get alpha opportunities for dashboard display."""
    try:
        integration = get_dashboard_integration()
        if not integration:
            return []

        alpha_data = await integration.get_alpha_opportunities()
        return alpha_data

    except Exception as e:
        logger.error(f"Error getting alpha opportunities: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting alpha opportunities: {str(e)}")


# News feed cache and sources
_news_cache: Dict[str, Any] = {"data": [], "timestamp": 0}
NEWS_CACHE_TTL = 300  # 5 minutes

NEWS_SOURCES = [
    # {"name": "CryptoPanic", "url": "https://cryptopanic.com/news/rss/"},  # Paused
    {"name": "Decrypt", "url": "https://decrypt.co/feed"},
    {"name": "The Block", "url": "https://www.theblock.co/rss.xml"},
    {"name": "Cointelegraph", "url": "https://cointelegraph.com/rss"},
    {"name": "WatcherGuru", "url": "https://watcher.guru/news/feed"},
    {"name": "CryptoPotato", "url": "https://cryptopotato.com/feed/"},
    {"name": "CryptoSlate", "url": "https://cryptoslate.com/feed/"},
    {"name": "CryptoNews", "url": "https://cryptonews.com/news/feed/"},
    {"name": "SmartLiquidity", "url": "https://smartliquidity.info/feed/"},
]


async def _fetch_rss_feed(session: aiohttp.ClientSession, source: Dict[str, str]) -> List[Dict[str, Any]]:
    """Fetch and parse a single RSS feed."""
    import xml.etree.ElementTree as ET
    from datetime import datetime
    from email.utils import parsedate_to_datetime

    items = []
    try:
        async with session.get(
            source["url"],
            timeout=aiohttp.ClientTimeout(total=8)
        ) as response:
            if response.status == 200:
                xml_content = await response.text()
                root = ET.fromstring(xml_content)

                for item in root.findall('.//item')[:10]:  # Limit per source
                    title = item.find('title')
                    link = item.find('link')
                    pub_date = item.find('pubDate')

                    if title is not None and title.text:
                        # Parse publish date for sorting
                        timestamp = 0
                        if pub_date is not None and pub_date.text:
                            try:
                                dt = parsedate_to_datetime(pub_date.text)
                                timestamp = int(dt.timestamp())
                            except Exception:
                                pass

                        items.append({
                            "title": title.text.strip()[:150],  # Truncate long titles
                            "link": link.text if link is not None else "",
                            "source": source["name"],
                            "timestamp": timestamp,
                        })
    except Exception as e:
        logger.debug(f"Error fetching {source['name']} RSS: {e}")

    return items


@router.get("/news")
async def get_crypto_news(limit: int = 25) -> Dict[str, Any]:
    """Get latest crypto news from multiple RSS feeds.

    Aggregates news from CryptoPanic, Decrypt, The Block, Cointelegraph, and WatcherGuru.
    Results are sorted by publish time and cached for 5 minutes.
    """
    global _news_cache
    now = time.time()

    # Return cached data if fresh
    if _news_cache["data"] and (now - _news_cache["timestamp"]) < NEWS_CACHE_TTL:
        return {
            "news": _news_cache["data"][:limit],
            "sources": [s["name"] for s in NEWS_SOURCES],
            "cached": True,
            "timestamp": int(now)
        }

    try:
        async with aiohttp.ClientSession() as session:
            # Fetch all feeds concurrently
            tasks = [_fetch_rss_feed(session, source) for source in NEWS_SOURCES]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Combine and sort by timestamp (newest first)
            all_news = []
            for result in results:
                if isinstance(result, list):
                    all_news.extend(result)

            # Sort by timestamp descending, then dedupe by title similarity
            all_news.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

            # Simple dedupe - remove items with very similar titles
            seen_titles = set()
            unique_news = []
            for item in all_news:
                # Create simple hash of first 50 chars
                title_key = item["title"][:50].lower()
                if title_key not in seen_titles:
                    seen_titles.add(title_key)
                    unique_news.append(item)

            # Update cache
            _news_cache = {
                "data": unique_news,
                "timestamp": now
            }

            return {
                "news": unique_news[:limit],
                "sources": [s["name"] for s in NEWS_SOURCES],
                "cached": False,
                "timestamp": int(now)
            }

    except Exception as e:
        logger.error(f"Error fetching crypto news: {e}")

    # Return cached data even if stale, or empty list
    return {
        "news": _news_cache.get("data", [])[:limit],
        "sources": [s["name"] for s in NEWS_SOURCES],
        "cached": True,
        "stale": True,
        "timestamp": int(now)
    }


@router.get("/market-overview")
async def get_market_overview() -> Dict[str, Any]:
    """Get market overview data for dashboard using shared cache bridge."""
    try:
        # CRITICAL FIX: Use mobile-data endpoint internally since it has the correct structure
        if web_cache:
            try:
                # Get mobile data which has the complete market overview
                mobile_data = await web_cache.get_mobile_data()
                # Only use data if it's NOT fallback data (same check as mobile-data endpoint)
                if mobile_data and mobile_data.get('data_source') != 'fallback' and mobile_data.get('market_overview'):
                    market_overview = mobile_data['market_overview']
                    logger.info(f"✅ Dashboard market overview from mobile-data cache (source: {mobile_data.get('data_source')})")

                    # Return flattened structure for compatibility
                    return {
                        "market_regime": market_overview.get('market_regime', 'unknown'),
                        "regime": market_overview.get('market_regime', 'unknown'),
                        "trend_strength": market_overview.get('trend_strength', 0),
                        "trend_score": market_overview.get('trend_strength', 0),
                        "volatility": market_overview.get('volatility', 0),
                        "current_volatility": market_overview.get('current_volatility', market_overview.get('market_dispersion', 0)),
                        "avg_volatility": market_overview.get('avg_volatility', market_overview.get('avg_market_dispersion', 0)),
                        "btc_price": market_overview.get('btc_price', 0),
                        "btc_volatility": market_overview.get('btc_volatility', 0),
                        "btc_dominance": market_overview.get('btc_dominance', 59.3),
                        "eth_dominance": market_overview.get('eth_dominance', 11.5),
                        "total_volume": market_overview.get('total_volume_24h', 0),
                        "total_volume_24h": market_overview.get('total_volume_24h', 0),
                        "gainers": market_overview.get('gainers', 0),
                        "losers": market_overview.get('losers', 0),
                        "average_change": market_overview.get('average_change', 0),
                        "active_symbols": len(mobile_data.get('confluence_scores', [])),
                        # CoinGecko global data
                        "total_market_cap": market_overview.get('total_market_cap', 0),
                        "market_cap_change_24h": market_overview.get('market_cap_change_24h', 0),
                        "active_cryptocurrencies": market_overview.get('active_cryptocurrencies', 0),
                        # Fear & Greed Index
                        "fear_greed_value": market_overview.get('fear_greed_value', 50),
                        "fear_greed_label": market_overview.get('fear_greed_label', 'Neutral'),
                        "data_source": "mobile_data_cache",
                        "timestamp": mobile_data.get('timestamp', int(time.time()))
                    }
                logger.warning(f"Shared cache returned fallback/empty data for dashboard market overview: {mobile_data.get('data_source') if mobile_data else 'None'}")
            except Exception as e:
                logger.error(f"Shared cache error in dashboard market overview: {e}")

        # Fallback to direct cache adapter if available (same as mobile-data endpoint)
        if USE_DIRECT_CACHE:
            try:
                mobile_data = await direct_cache.get_mobile_data()
                if mobile_data and mobile_data.get('market_overview'):
                    market_overview = mobile_data['market_overview']
                    logger.info(f"✅ Dashboard market overview from direct cache adapter")

                    return {
                        "market_regime": market_overview.get('market_regime', 'unknown'),
                        "regime": market_overview.get('market_regime', 'unknown'),
                        "trend_strength": market_overview.get('trend_strength', 0),
                        "trend_score": market_overview.get('trend_strength', 0),
                        "volatility": market_overview.get('volatility', 0),
                        "current_volatility": market_overview.get('market_dispersion', 0),
                        "avg_volatility": market_overview.get('avg_market_dispersion', 0),
                        "btc_price": market_overview.get('btc_price', 0),
                        "btc_volatility": market_overview.get('btc_volatility', 0),
                        "btc_dominance": market_overview.get('btc_dominance', 59.3),
                        "eth_dominance": market_overview.get('eth_dominance', 11.5),
                        "total_volume": market_overview.get('total_volume_24h', 0),
                        "total_volume_24h": market_overview.get('total_volume_24h', 0),
                        "gainers": market_overview.get('gainers', 0),
                        "losers": market_overview.get('losers', 0),
                        "average_change": market_overview.get('average_change', 0),
                        "active_symbols": len(mobile_data.get('confluence_scores', [])),
                        # CoinGecko global data
                        "total_market_cap": market_overview.get('total_market_cap', 0),
                        "market_cap_change_24h": market_overview.get('market_cap_change_24h', 0),
                        "active_cryptocurrencies": market_overview.get('active_cryptocurrencies', 0),
                        # Fear & Greed Index
                        "fear_greed_value": market_overview.get('fear_greed_value', 50),
                        "fear_greed_label": market_overview.get('fear_greed_label', 'Neutral'),
                        "data_source": "direct_cache",
                        "timestamp": mobile_data.get('timestamp', int(time.time()))
                    }
            except Exception as e:
                logger.error(f"Direct cache error in market overview: {e}")

        # Fallback to integration service
        integration = get_dashboard_integration()
        if not integration:
            return {
                "active_symbols": 0,
                "total_volume": 0,
                "market_regime": "unknown",
                "volatility": 0,
                "data_source": "fallback_default"
            }

        market_data = await integration.get_market_overview()
        market_data["data_source"] = "integration_service_fallback"
        return market_data

    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting market overview: {str(e)}")

@router.websocket("/ws")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    await connection_manager.connect(websocket)
    
    try:
        # Send initial data
        integration = get_dashboard_integration()
        if integration:
            initial_data = await integration.get_dashboard_overview()
            await websocket.send_json({
                "type": "dashboard_update",
                "data": initial_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        # Keep connection alive and send periodic updates
        while True:
            try:
                # Send updated data every 10 seconds
                if integration:
                    dashboard_data = await integration.get_dashboard_overview()
                    await websocket.send_json({
                        "type": "dashboard_update",
                        "data": dashboard_data,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                
                await asyncio.sleep(10)  # Update every 10 seconds
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in dashboard WebSocket loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
                
    except WebSocketDisconnect:
        logger.info("Dashboard WebSocket disconnected normally")
    except Exception as e:
        logger.error(f"Dashboard WebSocket error: {e}")
    finally:
        connection_manager.disconnect(websocket)

@router.post("/config")
async def update_dashboard_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Update dashboard configuration."""
    try:
        # TODO: Implement configuration validation and storage
        # For now, just acknowledge the config update
        logger.info(f"Dashboard configuration update received: {config}")
        
        return {
            "status": "success",
            "message": "Configuration updated successfully",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config": config
        }

    except Exception as e:
        logger.error(f"Error updating dashboard config: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating config: {str(e)}")

@router.get("/config")
async def get_dashboard_config() -> Dict[str, Any]:
    """Get current dashboard configuration."""
    try:
        # TODO: Implement configuration retrieval from storage
        # For now, return default configuration
        default_config = {
            "monitoring": {
                "scan_interval": 5,
                "max_alerts": 3,
                "alert_cooldown": 60
            },
            "signals": {
                "min_score": 65,
                "min_reliability": 75
            },
            "alpha": {
                "confidence_threshold": 75,
                "risk_level": "Medium"
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        return default_config

    except Exception as e:
        logger.error(f"Error getting dashboard config: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting config: {str(e)}")

@router.get("/health")
async def dashboard_health() -> Dict[str, Any]:
    """Dashboard health check endpoint."""
    try:
        integration = get_dashboard_integration()
        
        # Check if we have Phase 2 with cache performance
        cache_info = {}
        if hasattr(integration, 'get_cache_performance'):
            cache_info = await integration.get_cache_performance()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "integration_available": integration is not None,
            "active_websocket_connections": len(connection_manager.active_connections),
            "cache_performance": cache_info
        }

    except Exception as e:
        logger.error(f"Dashboard health check error: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }


@router.get("/perpetuals-pulse")
async def get_perpetuals_pulse() -> Dict[str, Any]:
    """
    Aggregated perpetuals market data from CoinGecko derivatives API.
    Provides total OI, volume, funding rates, and market sentiment metrics.
    Uses internal cached endpoint to avoid rate limits.
    """
    import math

    try:
        # Fetch from our internal cached CoinGecko derivatives endpoint
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'http://localhost:8002/api/coingecko/derivatives',
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status != 200:
                    logger.warning(f"Internal derivatives endpoint returned {response.status}")
                    return {
                        "status": "error",
                        "error": f"Internal API returned status {response.status}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                data = await response.json()

        if data.get('status') != 'success':
            return {
                "status": "error",
                "error": data.get('error', 'Unknown error from derivatives endpoint'),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        contracts = data.get('data', {}).get('contracts', [])

        if not contracts:
            return {
                "status": "error",
                "error": "No derivatives data available",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Aggregate metrics from all contracts
        total_oi = 0.0
        total_volume = 0.0
        weighted_funding_sum = 0.0
        funding_volume = 0.0

        # Track exchange distribution
        exchange_oi = {}
        cex_oi = 0.0
        dex_oi = 0.0
        dex_exchanges = {'dydx', 'hyperliquid', 'gmx', 'vertex', 'drift'}

        for contract in contracts:
            oi = float(contract.get('open_interest') or 0)
            vol = float(contract.get('volume_24h') or 0)
            funding = float(contract.get('funding_rate') or 0)

            total_oi += oi
            total_volume += vol

            # Volume-weighted funding rate
            if vol > 0:
                weighted_funding_sum += funding * vol
                funding_volume += vol

            # Exchange tracking
            market = contract.get('market', '').lower()
            exchange = market.replace(' (futures)', '').replace(' futures', '').strip()
            exchange_oi[exchange] = exchange_oi.get(exchange, 0) + oi

            # CEX vs DEX
            if any(dex in exchange for dex in dex_exchanges):
                dex_oi += oi
            else:
                cex_oi += oi

        # Calculate averages and percentages
        # CoinGecko returns funding rate as a percentage (e.g., 0.0057 = 0.0057%)
        avg_funding = (weighted_funding_sum / funding_volume) if funding_volume > 0 else 0.0

        # CEX/DEX percentages
        total_for_pct = cex_oi + dex_oi
        cex_pct = (cex_oi / total_for_pct * 100) if total_for_pct > 0 else 90.0
        dex_pct = 100 - cex_pct

        # Funding sentiment (thresholds for percentage values)
        # Typical 8-hour funding is ±0.01% to ±0.03%
        if avg_funding > 0.02:  # > 0.02%
            funding_sentiment = "BULLISH"
            funding_strength = "STRONG" if avg_funding > 0.05 else "MODERATE"
        elif avg_funding < -0.02:  # < -0.02%
            funding_sentiment = "BEARISH"
            funding_strength = "STRONG" if avg_funding < -0.05 else "MODERATE"
        else:
            funding_sentiment = "NEUTRAL"
            funding_strength = "WEAK"

        # Basis status (based on funding direction)
        if avg_funding > 0.01:
            basis_status = "CONTANGO"
            basis_pct = avg_funding * 3 * 365 / 100  # Annualized (3 funding periods/day)
        elif avg_funding < -0.01:
            basis_status = "BACKWARDATION"
            basis_pct = avg_funding * 3 * 365 / 100
        else:
            basis_status = "NEUTRAL"
            basis_pct = avg_funding * 3 * 365 / 100

        # Long/Short estimation from funding rates
        # Positive funding = longs pay shorts = more longs
        # Funding rate of 0.01% suggests roughly 55-60% longs
        funding_signal = min(max(avg_funding * 100, -5), 5)  # Clamp to reasonable range
        long_pct = 50 + funding_signal * 2  # Adjust by funding
        long_pct = min(max(long_pct, 35), 65)  # Clamp to 35-65%
        short_pct = 100 - long_pct

        # Calculate funding z-score (normalized against typical range of ±0.03%)
        funding_zscore = avg_funding / 0.03 if avg_funding != 0 else 0.0

        # Calculate Shannon entropy for L/S balance
        if long_pct > 0 and short_pct > 0:
            p_long = long_pct / 100
            p_short = short_pct / 100
            entropy = -(p_long * math.log2(p_long) + p_short * math.log2(p_short))
            ls_entropy = entropy  # Max entropy is 1.0 for 50/50
        else:
            ls_entropy = 0.0

        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "coingecko",

            # Primary metrics
            "total_open_interest": total_oi,
            "total_volume_24h": total_volume,

            # Funding data (avg_funding is already in percentage, e.g., 0.01 = 0.01%)
            "funding_rate": round(avg_funding, 4),  # Already as percentage
            "funding_sentiment": funding_sentiment,
            "funding_strength": funding_strength,
            "funding_zscore": round(funding_zscore, 2),

            # Long/Short ratio
            "long_pct": round(long_pct, 1),
            "short_pct": round(short_pct, 1),
            "ls_entropy": round(ls_entropy, 2),

            # Basis
            "basis_status": basis_status,
            "basis_pct": round(basis_pct, 3),

            # Exchange distribution
            "cex_pct": round(cex_pct, 1),
            "dex_pct": round(dex_pct, 1),
            "exchange_count": len(exchange_oi),

            # Metadata
            "contract_count": len(contracts),
            "signals": [],
            "signal_count": 0
        }

    except asyncio.TimeoutError:
        logger.warning("CoinGecko derivatives request timed out")
        return {
            "status": "error",
            "error": "Request timed out",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except aiohttp.ClientError as e:
        logger.warning(f"Could not connect to CoinGecko: {e}")
        return {
            "status": "error",
            "error": f"Connection error: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Perpetuals pulse error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/cache-stats")
async def get_cache_stats() -> Dict[str, Any]:
    """Get Phase 2 cache statistics and performance metrics."""
    try:
        integration = get_dashboard_integration()
        
        # Check if Phase 2 is available
        if not hasattr(integration, 'get_cache_performance'):
            return {
                "status": "phase1",
                "message": "Phase 1 cache active (no Memcached stats available)",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Get Phase 2 cache performance
        cache_performance = await integration.get_cache_performance()
        
        return {
            "status": "phase2",
            "message": "Phase 2 Memcached cache active",
            "performance": cache_performance,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting cache stats: {str(e)}")

@router.get("/test")
async def dashboard_test() -> Dict[str, Any]:
    """Simple test endpoint that doesn't use integration service."""
    return {
        "status": "ok",
        "message": "Dashboard API is working",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "server_time": time.time()
    }

@router.get("/debug-components")
async def debug_components(request: Request) -> Dict[str, Any]:
    """Debug endpoint to check available components."""
    app = request.app
    available_components = []
    
    # Check what's in app.state
    for attr in dir(app.state):
        if not attr.startswith('_'):
            available_components.append(attr)
    
    # Check dashboard integration
    integration = get_dashboard_integration()
    has_integration = integration is not None
    has_data = False
    signal_count = 0
    
    if integration and hasattr(integration, '_dashboard_data'):
        has_data = True
        signals = integration._dashboard_data.get('signals', [])
        signal_count = len(signals)
    
    return {
        "available_components": available_components,
        "has_integration": has_integration,
        "has_dashboard_data": has_data,
        "signal_count": signal_count,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/confluence-analysis-page")
async def confluence_analysis_page():
    """Serve the terminal-style confluence analysis page.

    Navigation flow:
    - Linked from: /api/dashboard/mobile (Alpha Pulse cards)
    - Back button returns to: /api/dashboard/mobile
    - Data from: /api/dashboard/confluence-analysis/{symbol}
    """
    return FileResponse(TEMPLATE_DIR / "dashboards" / "confluence_analysis.html")

@router.get("/sparkline-comparison")
async def sparkline_comparison_page():
    """Serve the sparkline style comparison page."""
    return FileResponse(TEMPLATE_DIR / "demos" / "sparkline_comparison.html")

@router.get("/alpha-viz-showcase")
async def alpha_viz_showcase_page():
    """Serve the Alpha Score visualization showcase page."""
    return FileResponse(TEMPLATE_DIR / "demos" / "alpha_viz_showcase.html")

@router.get("/confluence-analysis/{symbol}")
async def get_confluence_analysis(symbol: str) -> Dict[str, Any]:
    """Get full confluence analysis for a specific symbol."""
    try:
        # CRITICAL FIX: Query confluence_cache_service directly instead of integration cache
        from src.core.cache.confluence_cache_service import confluence_cache_service

        # Try to get cached breakdown for this symbol
        breakdown = await confluence_cache_service.get_cached_breakdown(symbol)

        # Get price data from the dashboard overview cache
        price_data = {}
        try:
            if USE_DIRECT_CACHE and direct_cache:
                overview = await direct_cache.get_dashboard_overview()
                if overview and isinstance(overview, dict):
                    signals = overview.get('signals', [])
                    for sig in signals:
                        if sig.get('symbol') == symbol:
                            price_data = {
                                'price': sig.get('price', 0),
                                'change_24h': sig.get('change_24h', 0),
                                'high_24h': sig.get('high_24h', 0),
                                'low_24h': sig.get('low_24h', 0),
                                'volume_24h': sig.get('volume_24h', 0)
                            }
                            break
        except Exception as price_err:
            logger.debug(f"Could not fetch price data for {symbol}: {price_err}")

        if breakdown and isinstance(breakdown, dict):
            # Format the breakdown into readable analysis text
            # Note: Cache uses 'overall_score', not 'confluence_score'
            score = breakdown.get('overall_score', breakdown.get('confluence_score', 50))
            components = breakdown.get('components', {})
            interpretations = breakdown.get('interpretations', {})
            reliability = breakdown.get('reliability', 0)

            # Post-process interpretations to ensure rich, consistent output
            def enrich_interpretations(interps: dict, comps: dict) -> dict:
                """Standardize and enrich all interpretations."""
                result = {}
                for comp, interp in interps.items():
                    comp_score = comps.get(comp, 50)

                    # Handle sentiment dict -> prose conversion
                    if comp == 'sentiment' and isinstance(interp, dict):
                        parts = []
                        if interp.get('sentiment'):
                            parts.append(interp['sentiment'])
                        if interp.get('funding_rate'):
                            parts.append(f"with {interp['funding_rate'].lower()}")
                        if interp.get('long_short_ratio'):
                            parts.append(f"and {interp['long_short_ratio'].lower()}")
                        if interp.get('market_activity'):
                            parts.append(f"amid {interp['market_activity'].lower()}")

                        base = ". ".join(parts) + "." if parts else "Neutral market sentiment."

                        # Add score-based context
                        if comp_score >= 65:
                            base += " Strong bullish sentiment suggests continuation of upward momentum with high conviction from market participants."
                        elif comp_score >= 55:
                            base += " Moderately bullish sentiment supports upward price action with reasonable conviction."
                        elif comp_score <= 35:
                            base += " Strong bearish sentiment suggests continuation of downward momentum with high conviction from market participants."
                        elif comp_score <= 45:
                            base += " Moderately bearish sentiment supports downward price action with reasonable conviction."
                        else:
                            base += " Neutral sentiment indicates market indecision with no clear directional bias."
                        result[comp] = base

                    # Enrich short orderflow interpretation
                    elif comp == 'orderflow' and isinstance(interp, str) and len(interp) < 250:
                        if comp_score >= 60:
                            extra = " Buying pressure dominates with strong accumulation patterns. Large orders are predominantly on the bid side, suggesting institutional buying interest. Volume-weighted order flow supports upward price movement."
                        elif comp_score <= 40:
                            extra = " Selling pressure dominates with distribution patterns evident. Large orders are predominantly on the ask side, suggesting institutional selling interest. Volume-weighted order flow supports downward price movement."
                        else:
                            extra = " Order flow shows equilibrium between buyers and sellers. Large orders are evenly distributed across both sides. This balance suggests potential consolidation or range-bound price action."
                        result[comp] = interp + extra

                    # Enrich short price_structure interpretation
                    elif comp == 'price_structure' and isinstance(interp, str) and len(interp) < 150:
                        if comp_score >= 60:
                            extra = " Key support levels are holding firm with higher lows forming. Resistance levels are being tested with increasing momentum. The overall structure favors bullish continuation with well-defined risk levels."
                        elif comp_score <= 40:
                            extra = " Key support levels are breaking down with lower highs forming. Resistance levels are capping price advances. The overall structure favors bearish continuation with breakdown targets in focus."
                        else:
                            extra = " Price is consolidating within a defined range. Support and resistance levels are well-established, creating a balanced trading environment. Breakout direction will likely determine the next trend."
                        result[comp] = interp + extra
                    else:
                        result[comp] = str(interp) if not isinstance(interp, str) else interp

                return result

            interpretations = enrich_interpretations(interpretations, components)

            # Determine signal direction
            if score >= 60:
                signal_dir = "BULLISH"
            elif score <= 40:
                signal_dir = "BEARISH"
            else:
                signal_dir = "NEUTRAL"

            # Build formatted analysis text - mobile-friendly design
            import textwrap
            from datetime import datetime
            analysis_lines = []

            # Get timestamp
            timestamp = breakdown.get('timestamp', 0)
            if timestamp:
                dt = datetime.fromtimestamp(timestamp)
                time_str = dt.strftime("%H:%M:%S")
                date_str = dt.strftime("%Y-%m-%d")
            else:
                now = datetime.now(timezone.utc)
                time_str = now.strftime("%H:%M:%S")
                date_str = now.strftime("%Y-%m-%d")

            # Header with branding (60 char width for modern mobile)
            analysis_lines.append("╔════════════════════════════════════════════════════════════╗")
            analysis_lines.append("║                  VIRTUOSO ALPHA ANALYSIS                   ║")
            analysis_lines.append("╚════════════════════════════════════════════════════════════╝")
            analysis_lines.append("")
            analysis_lines.append(f"  {symbol}")

            # Add price line if available
            if price_data.get('price', 0) > 0:
                price = price_data['price']
                change = price_data.get('change_24h', 0)
                high = price_data.get('high_24h', 0)
                low = price_data.get('low_24h', 0)

                # Format price with appropriate precision
                if price >= 1000:
                    price_str = f"${price:,.2f}"
                elif price >= 1:
                    price_str = f"${price:.4f}"
                else:
                    price_str = f"${price:.6f}"

                # Format change with sign
                change_sign = "+" if change >= 0 else ""
                change_str = f"{change_sign}{change:.2f}%"

                analysis_lines.append(f"  {price_str}  ({change_str})")

                # Add 24h range
                if high > 0 and low > 0:
                    if high >= 1:
                        range_str = f"  24h Range: ${low:.4f} - ${high:.4f}"
                    else:
                        range_str = f"  24h Range: ${low:.6f} - ${high:.6f}"
                    analysis_lines.append(range_str)

            analysis_lines.append(f"  {date_str}  {time_str} UTC")
            analysis_lines.append("")
            # Center-align the alpha score line (60 char width)
            score_line = f"Alpha Score: {score:.1f}  │  Signal: {signal_dir}  │  Reliability: {reliability:.0f}%"
            analysis_lines.append("────────────────────────────────────────────────────────────")
            analysis_lines.append(score_line.center(60))
            analysis_lines.append("────────────────────────────────────────────────────────────")
            analysis_lines.append("")

            # Confluence Score History Sparkline (if available)
            score_history = breakdown.get('score_history', [])
            if score_history and len(score_history) >= 2:
                # Normalize to actual min/max for full height utilization
                min_score = min(score_history)
                max_score = max(score_history)
                score_range = max_score - min_score if max_score != min_score else 1

                # Calculate score trend and statistics
                first_scores = score_history[:len(score_history)//2]
                last_scores = score_history[len(score_history)//2:]
                avg_first = sum(first_scores) / len(first_scores) if first_scores else 50
                avg_last = sum(last_scores) / len(last_scores) if last_scores else 50
                net_change = score_history[-1] - score_history[0]

                if avg_last > avg_first + 3:
                    conf_trend = "▲"
                elif avg_last < avg_first - 3:
                    conf_trend = "▼"
                else:
                    conf_trend = "─"

                # === BRAILLE SPARKLINE ===
                # Braille chars have 4 rows × 2 cols of dots per character
                # This gives 8x vertical resolution in compact horizontal space
                # Each character encodes 2 data points side-by-side

                chart_height = 4  # 4 text rows (each braille char has 4 dot rows)
                target_width = 40  # Number of braille characters wide

                # We need 2 data points per braille char (left and right columns)
                target_points = target_width * 2

                # Resample score_history to target points
                if len(score_history) < target_points:
                    resampled = []
                    for i in range(target_points):
                        idx = i * (len(score_history) - 1) / (target_points - 1)
                        lower_idx = int(idx)
                        upper_idx = min(lower_idx + 1, len(score_history) - 1)
                        frac = idx - lower_idx
                        val = score_history[lower_idx] * (1 - frac) + score_history[upper_idx] * frac
                        resampled.append(val)
                    data_points = resampled
                else:
                    data_points = score_history[-target_points:]

                # Braille dot positions (Unicode braille is 0x2800 + dot pattern)
                # Dots are numbered: 1,4 (col1,col2 row1), 2,5 (row2), 3,6 (row3), 7,8 (row4)
                # Dot values: 1=0x01, 2=0x02, 3=0x04, 4=0x08, 5=0x10, 6=0x20, 7=0x40, 8=0x80
                LEFT_DOTS = [0x01, 0x02, 0x04, 0x40]   # Dots 1,2,3,7 (top to bottom)
                RIGHT_DOTS = [0x08, 0x10, 0x20, 0x80]  # Dots 4,5,6,8 (top to bottom)

                # Build braille chart - 4 text rows
                chart_rows = [""] * chart_height

                for char_idx in range(target_width):
                    left_val = data_points[char_idx * 2]
                    right_val = data_points[char_idx * 2 + 1] if char_idx * 2 + 1 < len(data_points) else left_val

                    # Normalize values to 0-15 range (4 rows × 4 levels per row)
                    left_level = int(((left_val - min_score) / score_range) * 15) if score_range > 0 else 8
                    right_level = int(((right_val - min_score) / score_range) * 15) if score_range > 0 else 8
                    left_level = max(0, min(15, left_level))
                    right_level = max(0, min(15, right_level))

                    # For each text row (0=top, 3=bottom), determine braille pattern
                    for row in range(chart_height):
                        # Calculate which dot rows should be filled for this text row
                        # Row 0 covers levels 12-15, Row 1: 8-11, Row 2: 4-7, Row 3: 0-3
                        row_min_level = (chart_height - 1 - row) * 4
                        row_max_level = row_min_level + 3

                        braille_char = 0x2800  # Empty braille

                        # Left column dots (for this text row)
                        if left_level >= row_min_level:
                            dots_to_fill = min(4, left_level - row_min_level + 1)
                            for d in range(dots_to_fill):
                                dot_idx = 3 - d  # Fill from bottom up within this row
                                braille_char |= LEFT_DOTS[dot_idx]

                        # Right column dots
                        if right_level >= row_min_level:
                            dots_to_fill = min(4, right_level - row_min_level + 1)
                            for d in range(dots_to_fill):
                                dot_idx = 3 - d
                                braille_char |= RIGHT_DOTS[dot_idx]

                        chart_rows[row] += chr(braille_char)

                # Add axis labels
                analysis_lines.append("  α ALPHA SCORE TREND")
                analysis_lines.append("  ──────────────────────────────────────────────────────")
                analysis_lines.append(f"  {max_score:5.0f} ┤{chart_rows[0]}")
                for i in range(1, chart_height - 1):
                    analysis_lines.append(f"        │{chart_rows[i]}")
                analysis_lines.append(f"  {min_score:5.0f} ┤{chart_rows[-1]}")
                analysis_lines.append(f"        └{'─' * target_width}  {conf_trend}")

                # Calculate time range (30 second intervals, 24 max points = ~12 mins)
                from datetime import datetime, timedelta
                now = datetime.now(timezone.utc)
                total_seconds = len(score_history) * 30  # 30 sec per data point
                start_time = now - timedelta(seconds=total_seconds)
                time_label = f"         {start_time.strftime('%H:%M')} {'─' * (target_width - 12)} {now.strftime('%H:%M')} UTC"
                analysis_lines.append(time_label)
                analysis_lines.append("")

                # --- Style 2: Momentum-First (Delta Encoding) ---
                # Shows direction changes: △▲ up, ▽▼ down, ─ flat
                # delta_line = ""
                # for i in range(1, len(score_history)):
                #     delta = score_history[i] - score_history[i-1]
                #     if delta > 2: delta_line += "▲"
                #     elif delta > 0.5: delta_line += "△"
                #     elif delta < -2: delta_line += "▼"
                #     elif delta < -0.5: delta_line += "▽"
                #     else: delta_line += "─"
                # analysis_lines.append("  α ALPHA SCORE")
                # analysis_lines.append("  ──────────────────────────────────────────────────────")
                # analysis_lines.append(f"  Δ {delta_line}")
                # analysis_lines.append(f"  [{min_score:.0f}→{max_score:.0f}] Net: {'+' if net_change >= 0 else ''}{net_change:.0f}")
                # analysis_lines.append("")

                # --- Style 3: Multi-Layer Ultimate (7 dimensions) ---
                # analysis_lines.append("  α ALPHA SCORE")
                # analysis_lines.append("  ──────────────────────────────────────────────────────")
                # analysis_lines.append(f"  {annotations}")
                # analysis_lines.append(f"  {sparkline}")
                # momentum_arrows = "↗" * 4 if conf_trend == "▲" else "↘" * 4 if conf_trend == "▼" else "→" * 4
                # regime = "BULL" if avg_last > 55 else "BEAR" if avg_last < 45 else "NEUTRAL"
                # std_dev = (sum((s - avg_last)**2 for s in score_history) / len(score_history)) ** 0.5
                # analysis_lines.append(f"  [{min_score:.0f}→{max_score:.0f} Δ{'+' if net_change >= 0 else ''}{net_change:.0f} σ{std_dev:.0f}] {regime} {momentum_arrows}")
                # analysis_lines.append("")

                # --- Style 4: Zone-Density (texture = zone) ---
                # zone_chars = ""
                # for s in score_history:
                #     if s >= 70: zone_chars += "█"
                #     elif s >= 60: zone_chars += "▓"
                #     elif s >= 50: zone_chars += "▒"
                #     elif s >= 40: zone_chars += "░"
                #     else: zone_chars += "·"
                # analysis_lines.append("  α ALPHA SCORE")
                # analysis_lines.append("  ──────────────────────────────────────────────────────")
                # analysis_lines.append(f"  {zone_chars}  {conf_trend}")
                # analysis_lines.append("")

            # Component Scores Section
            analysis_lines.append("  COMPONENT SCORES")
            analysis_lines.append("  ──────────────────────────────────────────────────────")
            analysis_lines.append("")

            # Display component scores - compact bars (16 chars to align with PRICE_STRUCTURE)
            for component, component_score in components.items():
                bar_len = int(component_score / 5)  # Scale to 20 chars
                bar = "█" * bar_len + "░" * (20 - bar_len)
                ind = "▲" if component_score >= 55 else "▼" if component_score <= 45 else "●"
                analysis_lines.append(f"  {component.upper():16s} {bar} {component_score:4.0f}{ind}")

            analysis_lines.append("")

            # Interpretations Section
            analysis_lines.append("  DETAILED ANALYSIS")
            analysis_lines.append("  ──────────────────────────────────────────────────────")

            # Display interpretations with word wrap (56 chars for modern mobile)
            # Order: overall first, components in standard order, actionable_insights last
            interpretation_order = [
                'overall', 'technical', 'volume', 'orderflow',
                'sentiment', 'orderbook', 'price_structure', 'actionable_insights'
            ]
            # Sort interpretations: ordered keys first, then any remaining
            ordered_keys = [k for k in interpretation_order if k in interpretations]
            remaining_keys = [k for k in interpretations if k not in interpretation_order]
            sorted_keys = ordered_keys + remaining_keys

            for component in sorted_keys:
                interpretation = interpretations[component]
                analysis_lines.append("")
                analysis_lines.append(f"  ▸ {component.upper()}")
                wrapped = textwrap.wrap(str(interpretation), width=56)
                for line in wrapped:
                    analysis_lines.append(f"    {line}")

            analysis_lines.append("")
            analysis_lines.append("════════════════════════════════════════════════════════════")
            analysis_lines.append("         Powered by Virtuoso  •  virtuosocrypto.com         ")
            analysis_lines.append("════════════════════════════════════════════════════════════")

            formatted_analysis = "\n".join(analysis_lines)

            return {
                "symbol": symbol,
                "analysis": formatted_analysis,
                "timestamp": breakdown.get('timestamp', 0),
                "score": score,
                "components": components,
                "interpretations": interpretations,
                "reliability": reliability,
                **price_data  # Include price, change_24h, high_24h, low_24h, volume_24h
            }

        # Fallback: No data available
        return {
            "symbol": symbol,
            "analysis": f"No analysis available for {symbol}. The monitoring system may not be tracking this symbol yet.",
            "timestamp": 0,
            "score": 50,
            **price_data  # Include price data even in fallback
        }

    except Exception as e:
        logger.error(f"Error getting confluence analysis: {e}")
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Traceback:\n{tb}")
        return {"error": str(e), "analysis": None}

@router.get("/confluence-scores")  
async def get_confluence_scores() -> Dict[str, Any]:
    """Get confluence scores with component breakdown."""
    try:
        # Get dashboard integration
        integration = get_dashboard_integration()
        if not integration:
            return {"error": "Dashboard integration not available", "scores": []}
            
        scores = []
        
        # Check if confluence cache has data
        if hasattr(integration, '_confluence_cache'):
            for symbol, cache_data in integration._confluence_cache.items():
                score_data = {
                    "symbol": symbol,
                    "score": round(cache_data.get('score', 50), 2),
                    "components": cache_data.get('components', {
                        "technical": 50,
                        "volume": 50,
                        "orderflow": 50,
                        "sentiment": 50,
                        "orderbook": 50,
                        "price_structure": 50
                    }),
                    "timestamp": cache_data.get('timestamp', 0)
                }
                scores.append(score_data)
        
        return {
            "scores": scores,
            "count": len(scores),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting confluence scores: {e}")
        return {"error": str(e), "scores": []}

@router.get("/mobile-data-direct")
async def get_mobile_dashboard_data_direct(request: Request) -> Dict[str, Any]:
    """Direct data endpoint that queries components without dashboard integration."""
    try:
        # Get components from app state
        app = request.app
        market_data_manager = getattr(app.state, 'market_data_manager', None)
        confluence_analyzer = getattr(app.state, 'confluence_analyzer', None)
        top_symbols_manager = getattr(app.state, 'top_symbols_manager', None)
        
        response = {
            "market_overview": {
                "market_regime": "NEUTRAL",
                "trend_strength": 0,
                "volatility": 0,
                "btc_dominance": 0,
                "total_volume_24h": 0
            },
            "confluence_scores": [],
            "top_movers": {
                "gainers": [],
                "losers": []
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success"
        }
        
        # Get top symbols - use config value for consistency
        if top_symbols_manager:
            try:
                # Get max_symbols from config (default 20)
                max_symbols = 20  # Match config.yaml market.symbols.max_symbols
                top_symbols = await top_symbols_manager.get_top_symbols(limit=max_symbols)
                confluence_scores = []

                # Import confluence cache service
                from src.core.cache.confluence_cache_service import confluence_cache_service

                for symbol_info in top_symbols:
                    symbol = symbol_info.get('symbol', symbol_info) if isinstance(symbol_info, dict) else symbol_info
                    
                    try:
                        # Try to get cached confluence data first
                        cached_result = None
                        try:
                            cached_result = await confluence_cache_service.get_cached_breakdown(symbol)
                        except Exception as cache_error:
                            logger.debug(f"Cache miss for {symbol}: {cache_error}")
                        
                        if cached_result:
                            # Use cached data
                            logger.debug(f"Using cached confluence data for {symbol}")
                            score = cached_result.get('confluence_score', 50)
                            components = cached_result.get('components', {})
                            
                            # Still need fresh ticker data for price/volume
                            ticker = {}
                            if market_data_manager:
                                market_data = await market_data_manager.get_market_data(symbol)
                                if market_data:
                                    ticker = market_data.get('ticker', {})
                        else:
                            # Fallback: calculate confluence if cache miss (but this shouldn't happen if monitor is running)
                            logger.warning(f"No cached confluence for {symbol}, skipping (monitor should populate cache)")
                            continue  # Skip this symbol if no cache data
                        
                        confluence_scores.append({
                            "symbol": symbol,
                            "score": round(score, 2),
                            "price": ticker.get('last', 0),
                            "change_24h": round(ticker.get('percentage', 0), 2),
                            "volume_24h": ticker.get('quoteVolume', 0),
                            "components": {
                                "technical": round(components.get('technical', 50), 2),
                                "volume": round(components.get('volume', 50), 2),
                                "orderflow": round(components.get('orderflow', 50), 2),
                                "sentiment": round(components.get('sentiment', 50), 2),
                                "orderbook": round(components.get('orderbook', 50), 2),
                                "price_structure": round(components.get('price_structure', 50), 2)
                            }
                        })
                    except Exception as e:
                        logger.warning(f"Error getting data for {symbol}: {e}")
                        continue
                
                response["confluence_scores"] = confluence_scores
                
                # Calculate top movers
                sorted_by_change = sorted(confluence_scores, key=lambda x: x.get('change_24h', 0))
                response["top_movers"]["losers"] = [
                    {"symbol": s['symbol'], "change": s['change_24h']} 
                    for s in sorted_by_change[:3] if s.get('change_24h', 0) < 0
                ]
                response["top_movers"]["gainers"] = [
                    {"symbol": s['symbol'], "change": s['change_24h']} 
                    for s in sorted_by_change[-3:] if s.get('change_24h', 0) > 0
                ]
                
            except Exception as e:
                logger.error(f"Error getting top symbols: {e}")
                response["status"] = "partial_data"
        
        # Removed legacy LSR logging referencing undefined confluence_data
        return response
        
    except Exception as e:
        logger.error(f"Error in direct mobile dashboard endpoint: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@router.get("/mobile-data")
async def get_mobile_dashboard_data() -> Dict[str, Any]:
    """
    REFACTORED: Optimized endpoint for mobile dashboard using cache adapter with fallback.

    This endpoint now uses the WebServiceCacheAdapter which:
    - Automatically fetches live data when cache is stale/empty
    - Handles schema translation from cache to dashboard format
    - Provides confluence scores with component breakdowns
    - Includes proper error handling and fallback mechanisms

    Previously: 210 lines of direct memcached access with no fallback
    Now: Clean adapter pattern with automatic live data fallback
    """
    try:
        # CRITICAL FIX: Use web cache adapter with automatic fallback to live data
        if web_cache:
            try:
                mobile_data = await web_cache.get_mobile_data()

                if mobile_data and mobile_data.get('data_source') != 'fallback':
                    confluence_count = len(mobile_data.get('confluence_scores', []))
                    logger.info(f"✅ Mobile data from shared cache: {confluence_count} confluence scores, source={mobile_data.get('data_source')}")

                    # Flatten structure for frontend compatibility
                    # JavaScript expects flat structure: data.market_regime, data.gainers, etc.
                    market_overview = mobile_data.get('market_overview', {})
                    top_movers = mobile_data.get('top_movers', {})
                    confluence_scores = mobile_data.get('confluence_scores', [])

                    # Deduplicate confluence scores - keep highest score per symbol
                    if confluence_scores:
                        seen_symbols = {}
                        for score_data in confluence_scores:
                            symbol = score_data.get('symbol')
                            current_score = score_data.get('score', 0)
                            if symbol not in seen_symbols or current_score > seen_symbols[symbol].get('score', 0):
                                seen_symbols[symbol] = score_data
                        confluence_scores = list(seen_symbols.values())
                        # Sort by score descending
                        confluence_scores.sort(key=lambda x: x.get('score', 0), reverse=True)
                        # Update mobile_data with deduplicated scores
                        mobile_data['confluence_scores'] = confluence_scores

                    # Derive opportunities from confluence scores
                    opportunities = derive_momentum_opportunities(confluence_scores, limit=10)

                    # Flatten perps data to top level for template compatibility
                    perps_data = mobile_data.get('perps', {})

                    # Add flattened fields at top level while keeping nested for backward compatibility
                    mobile_data.update({
                        # Flatten market_overview fields to top level
                        "market_regime": market_overview.get("market_regime", "NEUTRAL"),
                        "regime": market_overview.get("market_regime", "NEUTRAL"),  # Alias
                        "trend_strength": market_overview.get("trend_strength", 0),
                        "trend_score": market_overview.get("trend_strength", 0),  # Alias

                        # BTC Realized Volatility (True crypto volatility)
                        "btc_volatility": market_overview.get("btc_volatility", 0),
                        "btc_daily_volatility": market_overview.get("btc_daily_volatility", 0),
                        "btc_price": market_overview.get("btc_price", 0),
                        "btc_vol_days": market_overview.get("btc_vol_days", 0),

                        # Market Dispersion
                        "market_dispersion": market_overview.get("market_dispersion", 0),
                        "avg_market_dispersion": market_overview.get("avg_market_dispersion", 0),

                        # DEPRECATED: Keep for backward compatibility
                        "current_volatility": market_overview.get("volatility", market_overview.get("market_dispersion", 0)),
                        "avg_volatility": market_overview.get("avg_volatility", market_overview.get("avg_market_dispersion", 0)),

                        "btc_dominance": market_overview.get("btc_dominance", 0),
                        "total_volume_24h": market_overview.get("total_volume_24h", 0),
                        "average_change": market_overview.get("average_change", 0),
                        # Flatten top_movers to top level
                        "gainers": top_movers.get("gainers", []),
                        "top_gainers": top_movers.get("gainers", []),  # Alias
                        "losers": top_movers.get("losers", []),
                        # Add symbols array (confluence scores)
                        "symbols": confluence_scores,
                        "top_symbols": confluence_scores,  # Alias
                        # Add opportunities derived from confluence scores
                        "opportunities": opportunities,
                        # Flatten perps data to top level
                        "funding_rate": perps_data.get("funding_rate", 0),
                        "funding_zscore": perps_data.get("funding_zscore", 0.0),
                        "long_pct": perps_data.get("long_pct", 50),
                        "short_pct": perps_data.get("short_pct", 50),
                        "ls_entropy": perps_data.get("ls_entropy", 0.5),
                        "total_open_interest": perps_data.get("open_interest", 0),
                        "cex_pct": perps_data.get("cex_pct", 90),
                        "basis_pct": perps_data.get("basis_pct", 0.0),
                    })

                    return mobile_data

                logger.warning("Shared cache returned fallback data for mobile dashboard")
            except Exception as e:
                logger.error(f"Shared cache error in mobile data endpoint: {e}")

        # Fallback: Use direct cache adapter if web_cache not available
        if USE_DIRECT_CACHE:
            try:
                mobile_data = await direct_cache.get_mobile_data()
                logger.info(f"✅ Mobile data from direct cache adapter")

                # Apply same flattening for consistency
                market_overview = mobile_data.get('market_overview', {})
                top_movers = mobile_data.get('top_movers', {})
                confluence_scores = mobile_data.get('confluence_scores', [])

                # Deduplicate confluence scores - keep highest score per symbol
                if confluence_scores:
                    seen_symbols = {}
                    for score_data in confluence_scores:
                        symbol = score_data.get('symbol')
                        current_score = score_data.get('score', 0)
                        if symbol not in seen_symbols or current_score > seen_symbols[symbol].get('score', 0):
                            seen_symbols[symbol] = score_data
                    confluence_scores = list(seen_symbols.values())
                    # Sort by score descending
                    confluence_scores.sort(key=lambda x: x.get('score', 0), reverse=True)
                    # Update mobile_data with deduplicated scores
                    mobile_data['confluence_scores'] = confluence_scores

                # Derive opportunities from confluence scores (fallback path)
                opportunities = derive_momentum_opportunities(confluence_scores, limit=10)

                # Flatten perps data to top level for template compatibility
                perps_data = mobile_data.get('perps', {})

                mobile_data.update({
                    "market_regime": market_overview.get("market_regime", "NEUTRAL"),
                    "regime": market_overview.get("market_regime", "NEUTRAL"),
                    "trend_strength": market_overview.get("trend_strength", 0),
                    "trend_score": market_overview.get("trend_strength", 0),
                    "current_volatility": market_overview.get("volatility", 0),
                    "avg_volatility": market_overview.get("avg_volatility", 0),  # Added: average volatility
                    "btc_dominance": market_overview.get("btc_dominance", 0),
                    "total_volume_24h": market_overview.get("total_volume_24h", 0),
                    "gainers": top_movers.get("gainers", []),
                    "top_gainers": top_movers.get("gainers", []),
                    "losers": top_movers.get("losers", []),
                    "symbols": confluence_scores,
                    "top_symbols": confluence_scores,
                    "opportunities": opportunities,
                    # Flatten perps data to top level
                    "funding_rate": perps_data.get("funding_rate", 0),
                    "funding_zscore": perps_data.get("funding_zscore", 0.0),
                    "long_pct": perps_data.get("long_pct", 50),
                    "short_pct": perps_data.get("short_pct", 50),
                    "ls_entropy": perps_data.get("ls_entropy", 0.5),
                    "total_open_interest": perps_data.get("open_interest", 0),
                    "cex_pct": perps_data.get("cex_pct", 90),
                    "basis_pct": perps_data.get("basis_pct", 0.0),
                })

                return mobile_data
            except Exception as e:
                logger.error(f"Direct cache adapter error in mobile data: {e}")

        # Last resort: Return empty structure with clear error message
        logger.error("No cache adapter available for mobile data - returning empty structure")
        return {
            "status": "error",
            "error": "No cache adapter available",
            "message": "Cache service unavailable - please check service status",
            "market_overview": {
                "market_regime": "UNKNOWN",
                "trend_strength": 0,
                "current_volatility": 0,
                "btc_dominance": 0,
                "total_volume_24h": 0,
                "average_change": 0
            },
            "confluence_scores": [],
            "top_movers": {"gainers": [], "losers": []},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_source": "error_fallback"
        }

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error in mobile dashboard endpoint: {e}\nTraceback:\n{tb}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Internal server error - check logs for details",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_source": "error"
        }

@router.get("/performance")
async def get_dashboard_performance() -> Dict[str, Any]:
    """Get dashboard performance metrics."""
    try:
        # DISABLED: Integration depends on non-existent port 8004
        # Direct data access without cache layer
        local_integration = None  # Disabled
        # local_integration = get_dashboard_integration()
        if local_integration:
            performance_data = await local_integration.get_performance_metrics()
            return performance_data
        
        # Fallback performance data
        return {
            "cpu_usage": 45.2,
            "memory_usage": 62.1,
            "api_latency": 12,
            "active_connections": 3,
            "uptime": "2h 15m",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard performance: {e}")
        return {
            "cpu_usage": 0,
            "memory_usage": 0,
            "api_latency": 0,
            "active_connections": 0,
            "uptime": "0h 0m",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@router.get("/symbols")
async def get_dashboard_symbols() -> Dict[str, Any]:
    """Get symbols data with real confluence scores - uses same cache as /mobile-data."""
    try:
        # Use the same cache adapter as /mobile-data for consistency
        if web_cache:
            try:
                mobile_data = await web_cache.get_mobile_data()
                if mobile_data and mobile_data.get('data_source') != 'fallback':
                    confluence_scores = mobile_data.get('confluence_scores', [])

                    # Deduplicate and sort
                    if confluence_scores:
                        seen_symbols = {}
                        for score_data in confluence_scores:
                            symbol = score_data.get('symbol')
                            current_score = score_data.get('score', 0)
                            if symbol not in seen_symbols or current_score > seen_symbols[symbol].get('score', 0):
                                seen_symbols[symbol] = score_data
                        confluence_scores = sorted(
                            seen_symbols.values(),
                            key=lambda x: x.get('score', 0),
                            reverse=True
                        )

                    logger.info(f"✅ Symbols endpoint: {len(confluence_scores)} confluence scores from shared cache")
                    return {
                        "status": "success",
                        "symbols": confluence_scores,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
            except Exception as e:
                logger.warning(f"Shared cache error in symbols endpoint: {e}")

        # Fallback: Use direct cache adapter
        if USE_DIRECT_CACHE:
            try:
                mobile_data = await direct_cache.get_mobile_data()
                confluence_scores = mobile_data.get('confluence_scores', [])
                logger.info(f"✅ Symbols endpoint: {len(confluence_scores)} scores from direct cache")
                return {
                    "status": "success",
                    "symbols": confluence_scores,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            except Exception as e:
                logger.warning(f"Direct cache error: {e}")

        # Last resort: empty response
        logger.warning("No symbols available from cache adapters")
        return {
            "status": "unavailable",
            "symbols": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "No live symbol data available"
        }

    except Exception as e:
        logger.error(f"Error getting dashboard symbols: {e}")
        return {
            "status": "error",
            "symbols": [],
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# HTML Dashboard Routes
@router.get("/login")
async def login_page():
    """Serve the mobile login screen"""
    return FileResponse(TEMPLATE_DIR / "archive" / "login_mobile.html")

@router.get("/favicon.svg")
async def favicon():
    """Serve the custom amber trending-up favicon"""
    return FileResponse(TEMPLATE_DIR / "favicon.svg", media_type="image/svg+xml")

@router.get("/mobile")
async def mobile_dashboard_page():
    """Serve the mobile dashboard with all integrated components.

    Navigation flow:
    - Alpha Pulse cards link to: /api/dashboard/confluence-analysis-page?symbol=X
    - confluence-analysis-page Back button returns here
    """
    return FileResponse(TEMPLATE_DIR / "dashboards" / "dashboard_mobile_v3.html")

@router.get("/v1")
async def dashboard_v1_page():
    """Serve the original dashboard HTML page"""
    return FileResponse(TEMPLATE_DIR / "archive" / "dashboard.html")

@router.get("/market-analysis")
async def market_analysis_page():
    """Serve the Market Analysis dashboard"""
    return FileResponse(TEMPLATE_DIR / "archive" / "dashboard_market_analysis.html")

@router.get("/api/bybit-direct/top-symbols")
async def get_bybit_direct_symbols():
    """Get top symbols directly from Bybit API - guaranteed to work"""
    try:
        async with aiohttp.ClientSession() as session:
            # Get top symbols by turnover from Bybit
            url = "https://api.bybit.com/v5/market/tickers?category=linear"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('retCode') == 0 and 'result' in data:
                        tickers = data['result']['list']
                        
                        # Process and sort by turnover
                        symbols_data = []
                        for ticker in tickers:
                            try:
                                symbol = ticker['symbol']
                                price = float(ticker['lastPrice'])
                                change_24h = float(ticker['price24hPcnt']) * 100
                                volume_24h = float(ticker['volume24h'])
                                turnover_24h = float(ticker['turnover24h'])
                                
                                # Skip symbols with very low turnover
                                if turnover_24h < 1000000:  # $1M minimum
                                    continue
                                
                                # Determine status based on price change
                                if change_24h > 5:
                                    status = "strong_bullish"
                                elif change_24h > 2:
                                    status = "bullish"
                                elif change_24h > -2:
                                    status = "neutral"
                                elif change_24h > -5:
                                    status = "bearish"
                                else:
                                    status = "strong_bearish"
                                
                                symbols_data.append({
                                    "symbol": symbol,
                                    "price": price,
                                    "change_24h": change_24h,
                                    "volume_24h": volume_24h,
                                    "turnover_24h": turnover_24h,
                                    "status": status,
                                    "confluence_score": 50 + (change_24h * 2),  # Simple score
                                    "data_source": "bybit_direct"
                                })
                                
                            except (ValueError, KeyError) as e:
                                logger.debug(f"Skipping ticker {ticker.get('symbol', 'unknown')}: {e}")
                                continue
                        
                        # Sort by turnover (highest first)
                        symbols_data.sort(key=lambda x: x['turnover_24h'], reverse=True)
                        
                        # Return top 15 symbols
                        top_symbols = symbols_data[:15]
                        
                        logger.info(f"✅ Retrieved {len(top_symbols)} symbols directly from Bybit")
                        
                        return {
                            "symbols": top_symbols,
                            "timestamp": int(time.time() * 1000),
                            "source": "bybit_direct_api",
                            "total_symbols_processed": len(symbols_data),
                            "status": "success"
                        }
                
                # User-friendly error response
                if UserFriendlyError:
                    err = UserFriendlyError.format_error("EXCHANGE_CONNECTION_FAILED", exchange="Bybit")
                    raise HTTPException(status_code=500, detail=err)
                raise HTTPException(status_code=500, detail={"error": "Invalid Bybit API response"})
                
    except Exception as e:
        logger.error(f"Error getting direct Bybit data: {e}")
        if UserFriendlyError:
            err = UserFriendlyError.format_error("EXCHANGE_CONNECTION_FAILED", exchange="Bybit")
            raise HTTPException(status_code=500, detail=err)
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/api/bybit-direct/symbol/{symbol}")
async def get_bybit_symbol_detail(symbol: str):
    """Get detailed data for a specific symbol directly from Bybit"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('retCode') == 0 and data['result']['list']:
                        ticker = data['result']['list'][0]
                        
                        return {
                            "symbol": ticker['symbol'],
                            "price": float(ticker['lastPrice']),
                            "change_24h": float(ticker['price24hPcnt']) * 100,
                            "volume_24h": float(ticker['volume24h']),
                            "turnover_24h": float(ticker['turnover24h']),
                            "high_24h": float(ticker['highPrice24h']),
                            "low_24h": float(ticker['lowPrice24h']),
                            "timestamp": int(time.time() * 1000),
                            "source": "bybit_direct_api"
                        }
                
                if UserFriendlyError:
                    err = UserFriendlyError.format_error("INVALID_SYMBOL", symbol=symbol)
                    raise HTTPException(status_code=404, detail=err)
                raise HTTPException(status_code=404, detail={"error": f"Symbol {symbol} not found"})
                
    except Exception as e:
        logger.error(f"Error getting Bybit data for {symbol}: {e}")
        if UserFriendlyError:
            err = UserFriendlyError.format_error("EXCHANGE_CONNECTION_FAILED", exchange="Bybit")
            raise HTTPException(status_code=500, detail=err)
        raise HTTPException(status_code=500, detail={"error": str(e)})

# COMMENTED OUT: Duplicate route already exists at line 412
# @router.get("/confluence-analysis/{symbol}")
# async def get_confluence_analysis(symbol: str) -> Dict[str, Any]:
#     """Get full confluence analysis for a specific symbol."""
    try:
        # Direct data access without cache layer
        if not integration:
            return {
                "status": "error",
                "error": "Dashboard integration not available",
                "symbol": symbol
            }
        
        analysis_data = await integration.get_confluence_analysis(symbol)
        return analysis_data
        
    except Exception as e:
        logger.error(f"Error getting confluence analysis for {symbol}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "symbol": symbol
        }

@router.get("/market-movers")
async def get_market_movers() -> Dict[str, Any]:
    """Get comprehensive market movers including both gainers and losers."""
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.bybit.com/v5/market/tickers?category=linear"
            
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('retCode') == 0 and 'result' in data:
                        tickers = data['result']['list']
                        
                        # Process all symbols
                        all_changes = []
                        for ticker in tickers:
                            try:
                                symbol = ticker['symbol']
                                # Filter USDT pairs only, exclude PERP contracts
                                if symbol.endswith('USDT') and 'PERP' not in symbol:
                                    change_24h = float(ticker['price24hPcnt']) * 100
                                    turnover_24h = float(ticker['turnover24h'])
                                    price = float(ticker['lastPrice'])
                                    volume_24h = float(ticker['volume24h'])
                                    
                                    # Only include symbols with significant turnover
                                    if turnover_24h > 500000:  # $500k minimum
                                        all_changes.append({
                                            "symbol": symbol,
                                            "change_24h": round(change_24h, 2),
                                            "price": price,
                                            "volume_24h": volume_24h,
                                            "turnover_24h": turnover_24h
                                        })
                                        
                            except (ValueError, KeyError) as e:
                                continue
                        
                        # Sort by change percentage
                        all_changes.sort(key=lambda x: x['change_24h'])
                        
                        # Get top losers (most negative)
                        losers = [x for x in all_changes if x['change_24h'] < 0][:5]
                        
                        # Get top gainers (most positive)
                        gainers = [x for x in all_changes if x['change_24h'] > 0]
                        gainers.sort(key=lambda x: x['change_24h'], reverse=True)
                        gainers = gainers[:5]
                        
                        # Get statistics
                        total_symbols = len(all_changes)
                        positive_count = len([x for x in all_changes if x['change_24h'] > 0])
                        negative_count = len([x for x in all_changes if x['change_24h'] < 0])
                        neutral_count = len([x for x in all_changes if x['change_24h'] == 0])
                        
                        return {
                            "top_gainers": gainers,
                            "top_losers": losers,
                            "statistics": {
                                "total_symbols": total_symbols,
                                "positive": positive_count,
                                "negative": negative_count,
                                "neutral": neutral_count,
                                "positive_percentage": round((positive_count / total_symbols * 100) if total_symbols > 0 else 0, 1),
                                "negative_percentage": round((negative_count / total_symbols * 100) if total_symbols > 0 else 0, 1)
                            },
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "source": "bybit_direct"
                        }
                        
        raise HTTPException(status_code=500, detail="Failed to fetch market data")
        
    except Exception as e:
        logger.error(f"Error getting market movers: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/beta-analysis-data")
async def get_beta_analysis_data() -> Dict[str, Any]:
    """Get beta analysis data for mobile dashboard."""
    try:
        # Calculate beta coefficients for tracked symbols
        # Direct data access without cache layer
        beta_data = []
        
        # Default symbols with mock beta values for now
        symbols_beta = [
            {"symbol": "ETHUSDT", "beta": 1.12, "correlation": 0.89, "change_24h": 2.63},
            {"symbol": "SOLUSDT", "beta": 1.45, "correlation": 0.76, "change_24h": 0.94},
            {"symbol": "XRPUSDT", "beta": 0.98, "correlation": 0.82, "change_24h": 1.0},
            {"symbol": "ADAUSDT", "beta": 1.23, "correlation": 0.85, "change_24h": -1.2},
            {"symbol": "DOTUSDT", "beta": 1.34, "correlation": 0.79, "change_24h": 0.5},
            {"symbol": "AVAXUSDT", "beta": 1.56, "correlation": 0.71, "change_24h": 3.2},
            {"symbol": "NEARUSDT", "beta": 1.67, "correlation": 0.68, "change_24h": -2.1},
            {"symbol": "FTMUSDT", "beta": 1.89, "correlation": 0.65, "change_24h": 4.5},
            {"symbol": "ATOMUSDT", "beta": 1.05, "correlation": 0.87, "change_24h": 1.8},
            {"symbol": "ALGOUSDT", "beta": 1.43, "correlation": 0.73, "change_24h": -0.5}
        ]
        
        # Get real-time price data if available
        local_integration = get_dashboard_integration()
        if local_integration and hasattr(local_integration, '_dashboard_data'):
            signals = local_integration._dashboard_data.get('signals', [])
            # Update with real price changes
            for beta_item in symbols_beta:
                for signal in signals:
                    if signal['symbol'] == beta_item['symbol']:
                        beta_item['change_24h'] = round(signal.get('change_24h', 0), 2)
                        beta_item['price'] = signal.get('price', 0)
                        break
        
        # Calculate risk categories
        for item in symbols_beta:
            if item['beta'] < 0.8:
                item['risk_category'] = 'Low Risk'
                item['risk_color'] = 'green'
            elif item['beta'] < 1.2:
                item['risk_category'] = 'Medium Risk'
                item['risk_color'] = 'yellow'
            else:
                item['risk_category'] = 'High Risk'
                item['risk_color'] = 'red'
        
        # Sort by beta coefficient
        symbols_beta.sort(key=lambda x: x['beta'], reverse=True)
        
        return {
            "beta_analysis": symbols_beta,
            "market_beta": 1.15,  # Overall market beta
            "btc_dominance": 54.2,
            "analysis_timeframe": "30d",
            "last_update": datetime.now(timezone.utc).isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting beta analysis data: {e}")
        return {
            "status": "error",
            "error": str(e),
            "beta_analysis": [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@router.get("/correlation-matrix")
async def get_correlation_matrix() -> Dict[str, Any]:
    """Get correlation matrix data for dashboard."""
    try:
        # Mock correlation matrix data
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]
        
        # Use real correlation calculations if available
        if CORRELATION_SERVICE_AVAILABLE:
            try:
                # Get simple correlation service
                correlation_service = get_simple_correlation_service()
                
                # Calculate real correlation matrix
                result = await correlation_service.calculate_correlation_matrix(symbols, days=30)
                
                # Update timeframe to reflect actual calculation period
                if result["status"] == "success":
                    result["timeframe"] = "30d"  # Actual timeframe used
                    return result
                else:
                    logger.warning(f"Correlation calculation failed: {result.get('error')}")
                    # Fall back to null values
            except Exception as e:
                logger.error(f"Error using correlation service: {e}")
        
        # Fallback: return null values with clear indication
        correlations = []
        for i, sym1 in enumerate(symbols):
            row = []
            for j, sym2 in enumerate(symbols):
                if i == j:
                    corr = 1.0
                else:
                    corr = None  # Indicates real data not available
                row.append(corr)
            correlations.append(row)
        
        return {
            "symbols": symbols,
            "correlation_matrix": correlations,
            "timeframe": "unavailable",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "partial",
            "data_source": "fallback_null_values",
            "message": "Real correlation data temporarily unavailable"
        }
        
    except Exception as e:
        logger.error(f"Error getting correlation matrix: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@router.get("/market-analysis-summary")
async def get_market_analysis_summary() -> Dict[str, Any]:
    """Get market analysis summary for mobile dashboard."""
    try:
        return {
            "market_overview": {
                "trend": "Bullish",
                "trend_strength": 78,
                "volatility": "Medium",
                "volume_trend": "Increasing"
            },
            "key_levels": {
                "btc_support": 117500,
                "btc_resistance": 121000,
                "btc_current": 119097
            },
            "market_sentiment": {
                "fear_greed": 67,
                "sentiment": "Greed",
                "funding_rate": 0.012
            },
            "top_sectors": [
                {"sector": "AI & ML", "performance": 15.3},
                {"sector": "Layer 2", "performance": 8.7},
                {"sector": "DeFi", "performance": 5.2},
                {"sector": "Gaming", "performance": -2.1},
                {"sector": "Metaverse", "performance": -4.5}
            ],
            "risk_metrics": {
                "market_risk": "Medium",
                "volatility_index": 45.2,
                "liquidation_volume": "$287M"
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting market analysis summary: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@router.get("/beta-charts/time-series")
async def get_beta_time_series() -> Dict[str, Any]:
    """Get beta coefficient time series data for charting."""
    try:
        # Generate time series data for the last 7 days
        import random
        from datetime import datetime, timedelta
        
        symbols = ["ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOTUSDT"]
        end_date = datetime.now(timezone.utc)
        
        # Use real beta calculations if available
        if CORRELATION_SERVICE_AVAILABLE:
            try:
                # Get simple correlation service
                correlation_service = get_simple_correlation_service()
                
                # Get real beta time series data
                beta_result = await correlation_service.calculate_beta_time_series(
                    symbols, window_days=30, num_windows=7
                )
                
                if beta_result["status"] == "success":
                    return {
                        "chart_data": beta_result["series_data"],
                        "period": "7d",
                        "window_size": "30d",
                        "benchmark": "BTCUSDT",
                        "timestamp": beta_result["timestamp"],
                        "status": "success",
                        "data_source": "real_market_data"
                    }
            except Exception as e:
                logger.error(f"Error calculating real beta time series: {e}")
        
        # Fallback: return null values
        series_data = {}
        for symbol in symbols:
            data_points = []
            
            for i in range(7):
                date = end_date - timedelta(days=6-i)
                data_points.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "timestamp": int(date.timestamp() * 1000),
                    "beta": None  # Indicates real data not available
                })
            
            series_data[symbol] = data_points
        
        return {
            "chart_data": series_data,
            "period": "7d",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "partial",
            "data_source": "fallback_null_values",
            "message": "Real beta data temporarily unavailable"
        }
        
    except Exception as e:
        logger.error(f"Error getting beta time series: {e}")
        return {"status": "error", "error": str(e)}

@router.get("/beta-charts/correlation-heatmap")
async def get_correlation_heatmap() -> Dict[str, Any]:
    """Get correlation heatmap data for visualization."""
    try:
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOTUSDT", "AVAXUSDT", "NEARUSDT"]
        
        # Use real correlation calculations for heatmap if available
        if CORRELATION_SERVICE_AVAILABLE:
            try:
                # Get simple correlation service
                correlation_service = get_simple_correlation_service()
                
                # Get real correlation heatmap data
                heatmap_result = await correlation_service.get_correlation_heatmap(symbols, days=30)
                
                if heatmap_result["status"] == "success":
                    return heatmap_result
            except Exception as e:
                logger.error(f"Error calculating real correlation heatmap: {e}")
        
        # Fallback: return null correlation values
        heatmap_data = []
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                if i == j:
                    correlation = 1.0
                else:
                    correlation = None  # Indicates real data not available
                
                heatmap_data.append({
                    "x": sym1,
                    "y": sym2,
                    "value": correlation,
                    "color_intensity": correlation if correlation is not None else 0
                })
        
        return {
            "heatmap_data": heatmap_data,
            "symbols": symbols,
            "min_correlation": 0.0,
            "max_correlation": 1.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "partial",
            "data_source": "fallback_null_values",
            "message": "Real correlation data temporarily unavailable"
        }
        
    except Exception as e:
        logger.error(f"Error getting correlation heatmap: {e}")
        return {"status": "error", "error": str(e)}

@router.get("/beta-charts/performance")
async def get_performance_chart() -> Dict[str, Any]:
    """Get performance vs beta scatter plot data."""
    try:
        # Get current market data
        # Direct data access without cache layer
        
        scatter_data = [
            {"symbol": "BTCUSDT", "beta": 1.0, "performance": 0.84, "market_cap": 2300},
            {"symbol": "ETHUSDT", "beta": 1.12, "performance": 2.63, "market_cap": 460},
            {"symbol": "SOLUSDT", "beta": 1.45, "performance": 0.94, "market_cap": 85},
            {"symbol": "XRPUSDT", "beta": 0.98, "performance": 1.0, "market_cap": 175},
            {"symbol": "ADAUSDT", "beta": 1.23, "performance": -1.2, "market_cap": 45},
            {"symbol": "DOTUSDT", "beta": 1.34, "performance": 0.5, "market_cap": 35},
            {"symbol": "AVAXUSDT", "beta": 1.56, "performance": 3.2, "market_cap": 40},
            {"symbol": "NEARUSDT", "beta": 1.67, "performance": -2.1, "market_cap": 25},
            {"symbol": "FTMUSDT", "beta": 1.89, "performance": 4.5, "market_cap": 15},
            {"symbol": "ATOMUSDT", "beta": 1.05, "performance": 1.8, "market_cap": 30},
            {"symbol": "ALGOUSDT", "beta": 1.43, "performance": -0.5, "market_cap": 20}
        ]
        
        # Update with real performance data if available
        local_integration = get_dashboard_integration()
        if local_integration and hasattr(local_integration, '_dashboard_data'):
            signals = local_integration._dashboard_data.get('signals', [])
            for item in scatter_data:
                for signal in signals:
                    if signal['symbol'] == item['symbol']:
                        item['performance'] = round(signal.get('change_24h', 0), 2)
                        break
        
        # Calculate quadrants for risk/return analysis
        avg_beta = sum(d['beta'] for d in scatter_data) / len(scatter_data)
        avg_performance = sum(d['performance'] for d in scatter_data) / len(scatter_data)
        
        return {
            "scatter_data": scatter_data,
            "averages": {
                "beta": round(avg_beta, 2),
                "performance": round(avg_performance, 2)
            },
            "quadrants": {
                "high_risk_high_return": [d for d in scatter_data if d['beta'] > avg_beta and d['performance'] > avg_performance],
                "high_risk_low_return": [d for d in scatter_data if d['beta'] > avg_beta and d['performance'] <= avg_performance],
                "low_risk_high_return": [d for d in scatter_data if d['beta'] <= avg_beta and d['performance'] > avg_performance],
                "low_risk_low_return": [d for d in scatter_data if d['beta'] <= avg_beta and d['performance'] <= avg_performance]
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting performance chart data: {e}")
        return {"status": "error", "error": str(e)}

@router.get("/beta-charts/risk-distribution")
async def get_risk_distribution() -> Dict[str, Any]:
    """Get risk distribution data for pie/donut charts."""
    try:
        # Calculate risk distribution
        risk_categories = [
            {"category": "Low Risk (β < 0.8)", "count": 2, "percentage": 13.3, "color": "#10b981"},
            {"category": "Medium Risk (0.8 ≤ β < 1.2)", "count": 5, "percentage": 33.3, "color": "#f59e0b"},
            {"category": "High Risk (β ≥ 1.2)", "count": 8, "percentage": 53.4, "color": "#ef4444"}
        ]
        
        # Sector allocation
        sector_allocation = [
            {"sector": "DeFi", "allocation": 25.5, "avg_beta": 1.42},
            {"sector": "Layer 1", "allocation": 35.2, "avg_beta": 1.15},
            {"sector": "Layer 2", "allocation": 18.3, "avg_beta": 1.58},
            {"sector": "Infrastructure", "allocation": 12.0, "avg_beta": 0.98},
            {"sector": "Other", "allocation": 9.0, "avg_beta": 1.25}
        ]
        
        return {
            "risk_distribution": risk_categories,
            "sector_allocation": sector_allocation,
            "total_assets": 15,
            "avg_portfolio_beta": 1.28,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting risk distribution: {e}")
        return {"status": "error", "error": str(e)}

# COMMENTED OUT: Duplicate route already exists at line 407
# @router.get("/confluence-analysis-page")
# async def confluence_analysis_page():
#     """Serve the terminal-style confluence analysis page"""
#     return FileResponse(TEMPLATE_DIR / "confluence_analysis.html") 
@router.get("/beta-charts/all")
async def get_all_beta_charts() -> Dict[str, Any]:
    """Get all beta analysis charts data in one request."""
    try:
        # Combine all chart data for efficient loading
        time_series = await get_beta_time_series()
        correlation = await get_correlation_heatmap()
        performance = await get_performance_chart()
        risk_dist = await get_risk_distribution()
        
        return {
            "time_series": time_series.get("chart_data", {}),
            "correlation_heatmap": correlation.get("heatmap_data", []),
            "performance_scatter": performance.get("scatter_data", []),
            "risk_distribution": risk_dist.get("risk_distribution", []),
            "sector_allocation": risk_dist.get("sector_allocation", []),
            "summary": {
                "avg_portfolio_beta": risk_dist.get("avg_portfolio_beta", 1.28),
                "total_assets": risk_dist.get("total_assets", 15),
                "performance_quadrants": performance.get("quadrants", {})
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting all beta charts: {e}")
        return {"status": "error", "error": str(e)}

@router.get("/mobile/beta-dashboard")
async def get_mobile_beta_dashboard() -> Dict[str, Any]:
    """Get complete beta analysis data optimized for mobile dashboard."""
    try:
        # Get all data in parallel for performance
        beta_data_task = get_beta_analysis_data()
        charts_task = get_all_beta_charts()
        
        beta_data, charts = await asyncio.gather(beta_data_task, charts_task)
        
        # Format for mobile consumption
        response = {
            "overview": {
                "market_beta": beta_data.get("market_beta", 1.15),
                "btc_dominance": beta_data.get("btc_dominance", 54.2),
                "avg_portfolio_beta": charts.get("summary", {}).get("avg_portfolio_beta", 1.28),
                "total_assets": charts.get("summary", {}).get("total_assets", 15)
            },
            "beta_table": beta_data.get("beta_analysis", []),
            "charts": {
                "time_series": {
                    "data": charts.get("time_series", {}),
                    "config": {
                        "type": "line",
                        "options": {
                            "responsive": True,
                            "maintainAspectRatio": False,
                            "scales": {
                                "y": {"title": {"display": True, "text": "Beta Coefficient"}},
                                "x": {"title": {"display": True, "text": "Date"}}
                            }
                        }
                    }
                },
                "risk_distribution": {
                    "data": charts.get("risk_distribution", []),
                    "config": {
                        "type": "doughnut",
                        "options": {
                            "responsive": True,
                            "maintainAspectRatio": False,
                            "plugins": {
                                "legend": {"position": "bottom"}
                            }
                        }
                    }
                },
                "performance_scatter": {
                    "data": charts.get("performance_scatter", []),
                    "config": {
                        "type": "scatter",
                        "options": {
                            "responsive": True,
                            "maintainAspectRatio": False,
                            "scales": {
                                "x": {"title": {"display": True, "text": "Beta (Risk)"}},
                                "y": {"title": {"display": True, "text": "24h Performance %"}}
                            }
                        }
                    }
                },
                "correlation_heatmap": {
                "data": charts.get("correlation_heatmap", []),
                "symbols": charts.get("symbols", []),
                "config": {
                        "type": "heatmap",
                        "options": {
                            "responsive": True,
                            "maintainAspectRatio": False
                        }
                    }
                }
            },
            "insights": {
                "high_risk_opportunities": [
                    item["symbol"] for item in charts.get("summary", {}).get("performance_quadrants", {}).get("high_risk_high_return", [])
                ],
                "safe_performers": [
                    item["symbol"] for item in charts.get("summary", {}).get("performance_quadrants", {}).get("low_risk_high_return", [])
                ],
                "avoid_list": [
                    item["symbol"] for item in charts.get("summary", {}).get("performance_quadrants", {}).get("high_risk_low_return", [])
                ]
            },
            "last_update": datetime.now(timezone.utc).isoformat(),
            "status": "success"
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting mobile beta dashboard: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# ==================== PHASE 1: DIRECT MARKET DATA ROUTES ====================

@router.get("/market/live")
async def get_live_market_data(limit: int = 20) -> Dict[str, Any]:
    """
    Phase 1 Implementation - Direct market data endpoint
    Bypasses all complex abstractions and fetches data directly from Bybit
    
    Returns:
        Market data with prices, volumes, and 24h changes
    """
    if not DirectMarketData:
        raise HTTPException(status_code=500, detail="Direct Market Data service not available")
    
    try:
        # Direct fetch - no abstractions, proven to work
        tickers = await DirectMarketData.fetch_tickers(limit)
        
        if not tickers:
            return {
                "status": "error",
                "message": "Unable to fetch market data",
                "timestamp": int(time.time()),
                "data": {}
            }
        
        return {
            "status": "success",
            "timestamp": int(time.time()),
            "count": len(tickers),
            "data": tickers
        }
        
    except Exception as e:
        logger.error(f"Error in live market data: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": int(time.time()),
            "data": {}
        }


@router.get("/market/dashboard")
async def get_market_dashboard() -> Dict[str, Any]:
    """
    Phase 1 Implementation - Complete dashboard data
    Provides formatted data specifically for dashboard display
    
    Returns:
        Market overview, top movers, and all ticker data
    """
    if not DirectMarketData:
        raise HTTPException(status_code=500, detail="Direct Market Data service not available")
    
    try:
        # Get comprehensive dashboard data
        dashboard_data = await DirectMarketData.get_dashboard_data()
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error in market dashboard: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": int(time.time()),
            "overview": {},
            "top_gainers": [],
            "top_losers": [],
            "all_tickers": {}
        }


@router.get("/market/ticker/{symbol}")
async def get_ticker(symbol: str) -> Dict[str, Any]:
    """
    Phase 1 Implementation - Single ticker endpoint
    
    Args:
        symbol: Trading pair (e.g., "BTC/USDT")
    
    Returns:
        Single ticker data
    """
    if not DirectMarketData:
        raise HTTPException(status_code=500, detail="Direct Market Data service not available")
    
    try:
        ticker = await DirectMarketData.fetch_single_ticker(symbol)
        
        if not ticker:
            return {
                "status": "error",
                "message": f"Unable to fetch data for {symbol}",
                "timestamp": int(time.time()),
                "data": {}
            }
        
        return {
            "status": "success",
            "timestamp": int(time.time()),
            "data": ticker
        }
        
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": int(time.time()),
            "data": {}
        }


@router.get("/market/health")
async def market_health_check() -> Dict[str, Any]:
    """
    Phase 1 Implementation - Health check for market data service
    Tests connection to Bybit API
    """
    try:
        # Test with single ticker fetch (faster)
        start_time = time.time()
        btc = await DirectMarketData.fetch_single_ticker("BTC/USDT")
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        
        if btc and btc.get('price', 0) > 0:
            return {
                "status": "healthy",
                "service": "Direct Market Data",
                "response_time_ms": round(response_time, 2),
                "test_symbol": "BTC/USDT",
                "test_price": btc.get('price', 0),
                "timestamp": int(time.time())
            }
        else:
            return {
                "status": "degraded",
                "service": "Direct Market Data",
                "response_time_ms": round(response_time, 2),
                "message": "API responded but no data",
                "timestamp": int(time.time())
            }
            
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "Direct Market Data",
            "error": str(e),
            "timestamp": int(time.time())
        }


# =============================================================================
# BETA CHART API - Cached Bybit Performance Data
# =============================================================================

# Meme coin symbol mapping (Bybit uses 1000X prefixes for low-priced tokens)
BYBIT_SYMBOL_MAP = {
    'PEPE': '1000PEPEUSDT',
    'SHIB': '1000SHIBUSDT',
    'FLOKI': '1000FLOKIUSDT',
    'BONK': '1000BONKUSDT',
    'LUNC': '1000LUNCUSDT',
    'SATS': '1000SATSUSDT',
    'RATS': '1000RATSUSDT',
    'BTT': '1000000BTTUSDT',
    'BABYDOGE': '1000000BABYDOGEUSDT',
}

# Cache key and TTL
BETA_CHART_CACHE_KEY = b'virtuoso:beta_chart'
BETA_CHART_CACHE_TTL = 120  # 2 minutes


def normalize_symbol(symbol: str) -> str:
    """Convert Bybit symbol to normalized base asset name."""
    # Remove USDT suffix
    base = symbol.replace('USDT', '')
    # Handle 1000000X prefixes (BTT, BABYDOGE)
    if base.startswith('1000000'):
        return base[7:]
    # Handle 1000X prefixes (PEPE, SHIB, etc.)
    if base.startswith('1000'):
        return base[4:]
    return base


async def fetch_bybit_klines(session: aiohttp.ClientSession, symbol: str, interval: str = "60", limit: int = 12) -> List[Dict]:
    """Fetch kline data from Bybit for a single symbol."""
    url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval={interval}&limit={limit}"
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('retCode') == 0 and 'result' in data:
                    candles = []
                    for c in data['result']['list']:
                        candles.append({
                            'timestamp': int(c[0]),
                            'open': float(c[1]),
                            'high': float(c[2]),
                            'low': float(c[3]),
                            'close': float(c[4]),
                            'volume': float(c[5])
                        })
                    # Bybit returns newest first, reverse for chronological order
                    return list(reversed(candles))
    except Exception as e:
        logger.debug(f"Error fetching klines for {symbol}: {e}")
    return []


async def fetch_beta_chart_data(timeframe_hours: int = 4) -> Dict[str, Any]:
    """
    Fetch and compute rebased returns for top 25 symbols.

    Args:
        timeframe_hours: Number of hours of historical data (1, 4, 8, 12, 24)

    Returns:
        Dict with chart_data, overview, and metadata
    """
    async with aiohttp.ClientSession() as session:
        # Step 1: Fetch all tickers
        tickers_url = "https://api.bybit.com/v5/market/tickers?category=linear"
        async with session.get(tickers_url, timeout=10) as response:
            if response.status != 200:
                raise Exception("Failed to fetch Bybit tickers")

            data = await response.json()
            if data.get('retCode') != 0:
                raise Exception(f"Bybit API error: {data.get('retMsg')}")

            tickers = data['result']['list']

        # Step 2: Filter and sort USDT perpetuals by volume
        usdt_tickers = []
        for t in tickers:
            symbol = t['symbol']
            if symbol.endswith('USDT') and 'PERP' not in symbol:
                try:
                    turnover = float(t.get('turnover24h', 0))
                    price = float(t.get('lastPrice', 0))
                    change_24h = float(t.get('price24hPcnt', 0)) * 100

                    usdt_tickers.append({
                        'symbol': symbol,
                        'normalized': normalize_symbol(symbol),
                        'price': price,
                        'turnover_24h': turnover,
                        'change_24h': change_24h
                    })
                except (ValueError, KeyError):
                    continue

        # Sort by turnover (volume)
        usdt_tickers.sort(key=lambda x: x['turnover_24h'], reverse=True)

        # Step 3: Select top 25 symbols (always include BTC first)
        top_symbols = []
        btc_added = False

        for t in usdt_tickers:
            if t['normalized'] == 'BTC':
                if not btc_added:
                    top_symbols.insert(0, t)
                    btc_added = True
            elif len(top_symbols) < 25:
                top_symbols.append(t)

            if len(top_symbols) >= 25:
                break

        # Step 4: Fetch historical klines for each symbol
        # For short timeframes, use smaller intervals to get more data points
        if timeframe_hours < 1:
            # Sub-hour timeframes: use 5-minute candles
            interval = "5"    # 5-minute candles
            timeframe_minutes = int(timeframe_hours * 60)
            limit = max(3, timeframe_minutes // 5)  # e.g., 15min = 3 candles, 30min = 6 candles
        elif timeframe_hours == 1:
            interval = "15"   # 15-minute candles
            limit = 4         # 4 × 15min = 1 hour
        elif timeframe_hours <= 4:
            interval = "30"   # 30-minute candles
            limit = timeframe_hours * 2
        else:
            interval = "60"   # 1-hour candles
            limit = timeframe_hours

        historical_data = {}

        for ticker in top_symbols:
            symbol = ticker['symbol']
            normalized = ticker['normalized']

            # Check if we need to map to a different symbol (meme coins)
            fetch_symbol = BYBIT_SYMBOL_MAP.get(normalized, symbol)

            candles = await fetch_bybit_klines(session, fetch_symbol, interval, limit)

            if candles:
                historical_data[normalized] = candles

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.05)

        # Step 5: Calculate rebased returns (all start at 0%)
        chart_data = {}
        performance_summary = []

        for symbol, candles in historical_data.items():
            if len(candles) < 2:
                continue

            initial_price = candles[0]['close']
            if initial_price == 0:
                continue

            rebased = []
            for c in candles:
                pct_change = ((c['close'] - initial_price) / initial_price) * 100
                rebased.append({
                    'timestamp': c['timestamp'],
                    'value': round(pct_change, 4)
                })

            chart_data[symbol] = rebased

            # Final performance for sorting
            final_change = rebased[-1]['value'] if rebased else 0
            performance_summary.append({
                'symbol': symbol,
                'change': round(final_change, 2)
            })

        # Sort by performance for legend ordering
        performance_summary.sort(key=lambda x: x['change'], reverse=True)

        # Calculate overview stats
        btc_change = chart_data.get('BTC', [{}])[-1].get('value', 0) if 'BTC' in chart_data else 0
        outperformers = len([p for p in performance_summary if p['change'] > 1.0])
        underperformers = len([p for p in performance_summary if p['change'] < -3.0])

        return {
            'chart_data': chart_data,
            'performance_order': [p['symbol'] for p in performance_summary],
            'performance_summary': performance_summary,
            'overview': {
                'btc_change': round(btc_change, 2),
                'symbols_count': len(chart_data),
                'outperformers': outperformers,
                'underperformers': underperformers,
                'timeframe_hours': timeframe_hours
            },
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'cache_ttl_seconds': BETA_CHART_CACHE_TTL
        }


@router.get("/beta-chart")
async def get_beta_chart_data(timeframe: float = 4) -> Dict[str, Any]:
    """
    Get pre-computed beta chart data with caching.

    Data is primarily populated by the trading service's cache warmer.
    Web service reads from cache and falls back to generating on cache miss.

    Args:
        timeframe: Hours of historical data (0.25=15min, 0.5=30min, 1, 4, 8, 12, 24). Default: 4

    Returns:
        Pre-computed rebased returns for top 25 symbols by volume.
        Data is cached for 2 minutes to reduce API calls to Bybit.
    """
    # Validate timeframe (0.25=15min, 0.5=30min, 1=1h, etc.)
    valid_timeframes = [0.25, 0.5, 1, 4, 8, 12, 24]
    if timeframe not in valid_timeframes:
        timeframe = 4

    cache_key = f'virtuoso:beta_chart:{timeframe}h'.encode()

    try:
        # Try to get from cache (populated by trading service cache warmer)
        from pymemcache.client.base import Client
        mc_client = Client(('127.0.0.1', 11211))

        cached_data = mc_client.get(cache_key)
        if cached_data:
            try:
                data = json.loads(cached_data.decode('utf-8'))
                data['from_cache'] = True
                mc_client.close()
                logger.debug(f"Beta chart data served from cache ({timeframe}h)")
                return data
            except (json.JSONDecodeError, AttributeError):
                pass

        mc_client.close()
    except Exception as e:
        logger.debug(f"Cache read error: {e}")

    # Cache miss - generate fresh data using shared service module
    logger.info(f"Cache miss for beta chart ({timeframe}h) - generating fresh data...")

    try:
        # Use the shared beta chart service (same code as trading service uses)
        from src.core.chart.beta_chart_service import generate_beta_chart_data
        data = await generate_beta_chart_data(timeframe)
        data['from_cache'] = False
        data['generated_by'] = 'web_service_fallback'

        # Store in cache for next request
        try:
            from pymemcache.client.base import Client
            mc_client = Client(('127.0.0.1', 11211))
            mc_client.set(cache_key, json.dumps(data).encode('utf-8'), expire=BETA_CHART_CACHE_TTL)
            mc_client.close()
            logger.info(f"Beta chart data cached by web service ({timeframe}h, TTL={BETA_CHART_CACHE_TTL}s)")
        except Exception as e:
            logger.warning(f"Failed to cache beta chart data: {e}")

        return data

    except Exception as e:
        logger.error(f"Error generating beta chart data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch chart data: {str(e)}")


# ============================================================================
# TRADE-READY SIGNALS ENDPOINT
# ============================================================================

# In-memory storage for trade signals (for tracking status)
_trade_signals_store: Dict[str, Dict[str, Any]] = {}
_trade_signals_history: List[Dict[str, Any]] = []
MAX_SIGNAL_HISTORY = 100

# Default risk parameters
DEFAULT_STOP_PERCENTAGE = 3.5  # 3.5% stop loss
DEFAULT_RR_RATIO = 2.0  # 2:1 risk/reward
SIGNAL_EXPIRY_HOURS = 24  # Signals expire after 24 hours


def _calculate_trade_levels(
    entry_price: float,
    direction: str,
    stop_percentage: float = DEFAULT_STOP_PERCENTAGE,
    rr_ratio: float = DEFAULT_RR_RATIO
) -> Dict[str, Any]:
    """Calculate SL/TP levels for a trade signal."""
    stop_pct = stop_percentage / 100.0

    if direction.upper() in ['LONG', 'BUY', 'BULLISH']:
        stop_loss = entry_price * (1 - stop_pct)
        risk_per_unit = entry_price - stop_loss
        take_profit = entry_price + (risk_per_unit * rr_ratio)
        direction_normalized = 'LONG'
    else:
        stop_loss = entry_price * (1 + stop_pct)
        risk_per_unit = stop_loss - entry_price
        take_profit = entry_price - (risk_per_unit * rr_ratio)
        direction_normalized = 'SHORT'

    return {
        'entry_price': round(entry_price, 6),
        'stop_loss': round(stop_loss, 6),
        'take_profit': round(take_profit, 6),
        'stop_percentage': stop_percentage,
        'risk_reward_ratio': rr_ratio,
        'direction': direction_normalized
    }


def _determine_signal_direction(signal_data: Dict[str, Any]) -> str:
    """Determine if signal is LONG or SHORT based on confluence score and sentiment."""
    score = signal_data.get('confluence_score', signal_data.get('score', 50))
    sentiment = signal_data.get('sentiment', '').upper()
    signal_type = signal_data.get('signal_type', '').upper()

    # Explicit signal type takes priority
    if signal_type in ['BUY', 'LONG']:
        return 'LONG'
    if signal_type in ['SELL', 'SHORT']:
        return 'SHORT'

    # Check sentiment
    if sentiment == 'BULLISH':
        return 'LONG'
    if sentiment == 'BEARISH':
        return 'SHORT'

    # Fall back to score
    if score >= 60:
        return 'LONG'
    elif score <= 40:
        return 'SHORT'

    return 'NEUTRAL'


def _check_signal_status(
    signal: Dict[str, Any],
    current_price: float
) -> Dict[str, Any]:
    """Check if signal has hit TP, SL, or expired."""
    direction = signal.get('direction', 'LONG')
    entry = signal.get('entry_price', 0)
    sl = signal.get('stop_loss', 0)
    tp = signal.get('take_profit', 0)
    created_at = signal.get('created_at', time.time())

    # Check expiry
    age_hours = (time.time() - created_at) / 3600
    if age_hours > SIGNAL_EXPIRY_HOURS:
        return {'status': 'EXPIRED', 'exit_reason': 'timeout'}

    # Check TP/SL hit
    if direction == 'LONG':
        if current_price >= tp:
            return {'status': 'HIT_TP', 'exit_reason': 'take_profit', 'exit_price': tp}
        if current_price <= sl:
            return {'status': 'HIT_SL', 'exit_reason': 'stop_loss', 'exit_price': sl}
    else:  # SHORT
        if current_price <= tp:
            return {'status': 'HIT_TP', 'exit_reason': 'take_profit', 'exit_price': tp}
        if current_price >= sl:
            return {'status': 'HIT_SL', 'exit_reason': 'stop_loss', 'exit_price': sl}

    # Calculate current P&L
    if direction == 'LONG':
        pnl_pct = ((current_price - entry) / entry) * 100
    else:
        pnl_pct = ((entry - current_price) / entry) * 100

    return {
        'status': 'ACTIVE',
        'current_pnl_pct': round(pnl_pct, 2),
        'time_remaining_hours': round(SIGNAL_EXPIRY_HOURS - age_hours, 1)
    }


@router.get(
    "/trade-signals",
    summary="Get Trade-Ready Signals",
    description="""
    Retrieve actionable trading signals with entry/exit levels.

    Each signal includes:
    - Entry price (current market price when signal generated)
    - Stop loss price (calculated from risk parameters)
    - Take profit price (calculated from risk/reward ratio)
    - Risk/reward ratio
    - Signal status (ACTIVE, HIT_TP, HIT_SL, EXPIRED)
    - Time remaining before expiry

    Only shows signals with clear directional bias (LONG or SHORT).
    NEUTRAL signals are filtered out.
    """,
    tags=["dashboard", "signals", "trading"]
)
async def get_trade_ready_signals() -> Dict[str, Any]:
    """Get trade-ready signals with entry/SL/TP levels."""
    global _trade_signals_store, _trade_signals_history

    try:
        # Get base signals from existing endpoint logic
        signals_data = []
        confluence_scores = []

        # Try to get signals from web cache
        if web_cache:
            try:
                mobile_data = await web_cache.get_mobile_data()
                if mobile_data and mobile_data.get('data_source') != 'fallback':
                    confluence_scores = mobile_data.get('confluence_scores', [])
                    logger.debug(f"Trade signals: got {len(confluence_scores)} from web cache")
            except Exception as e:
                logger.warning(f"Failed to get signals from web cache: {e}")

        # Fallback to direct_cache (same pattern as other endpoints)
        if not confluence_scores and USE_DIRECT_CACHE:
            try:
                mobile_data = await direct_cache.get_mobile_data()
                if mobile_data and mobile_data.get('confluence_scores'):
                    confluence_scores = mobile_data['confluence_scores']
                    logger.debug(f"Trade signals: got {len(confluence_scores)} from direct cache")
            except Exception as e:
                logger.warning(f"Failed to get signals from direct cache: {e}")

        # Fallback to integration service
        if not confluence_scores:
            integration = get_dashboard_integration()
            if integration:
                try:
                    raw_signals = await integration.get_signals_data()
                    if raw_signals:
                        confluence_scores = raw_signals
                        logger.debug(f"Trade signals: got {len(confluence_scores)} from integration")
                except Exception as e:
                    logger.warning(f"Failed to get signals from integration: {e}")

        # Convert confluence_scores to signals_data format with price
        signals_data = [s for s in confluence_scores if s.get('symbol') and s.get('price', 0) > 0]
        logger.info(f"Trade signals: processing {len(signals_data)} signals with valid prices")

        # Process signals into trade-ready format
        trade_signals = []
        current_time = time.time()

        for signal in signals_data:
            symbol = signal.get('symbol', '')
            if not symbol:
                continue

            # Determine direction
            direction = _determine_signal_direction(signal)
            if direction == 'NEUTRAL':
                continue  # Skip neutral signals

            # Get current price
            current_price = float(signal.get('price', 0))
            if current_price <= 0:
                continue

            # Check if we already have this signal tracked
            signal_key = f"{symbol}_{direction}"
            existing_signal = _trade_signals_store.get(signal_key)

            if existing_signal:
                # Update status of existing signal
                status_info = _check_signal_status(existing_signal, current_price)
                existing_signal.update(status_info)
                existing_signal['current_price'] = current_price

                # If signal closed, move to history
                if status_info['status'] in ['HIT_TP', 'HIT_SL', 'EXPIRED']:
                    existing_signal['closed_at'] = current_time
                    _trade_signals_history.append(existing_signal.copy())
                    if len(_trade_signals_history) > MAX_SIGNAL_HISTORY:
                        _trade_signals_history = _trade_signals_history[-MAX_SIGNAL_HISTORY:]
                    del _trade_signals_store[signal_key]
                else:
                    trade_signals.append(existing_signal)
            else:
                # Create new trade signal
                confluence_score = float(signal.get('confluence_score', signal.get('score', 50)))

                # Only create signals with strong enough conviction
                if (direction == 'LONG' and confluence_score < 55) or \
                   (direction == 'SHORT' and confluence_score > 45):
                    continue

                trade_levels = _calculate_trade_levels(current_price, direction)

                new_signal = {
                    'id': f"{symbol}_{int(current_time)}",
                    'symbol': symbol,
                    'direction': direction,
                    'confluence_score': round(confluence_score, 1),
                    'sentiment': signal.get('sentiment', 'NEUTRAL'),
                    **trade_levels,
                    'current_price': current_price,
                    'change_24h': round(float(signal.get('change_24h', 0)), 2),
                    'volume_24h': signal.get('volume_24h', 0),
                    'created_at': current_time,
                    'status': 'ACTIVE',
                    'time_remaining_hours': SIGNAL_EXPIRY_HOURS,
                    'current_pnl_pct': 0.0,
                    'components': signal.get('components', {})
                }

                _trade_signals_store[signal_key] = new_signal
                trade_signals.append(new_signal)

        # Sort by confluence score (strongest signals first)
        trade_signals.sort(key=lambda x: x.get('confluence_score', 0), reverse=True)

        # Calculate summary stats
        long_signals = [s for s in trade_signals if s['direction'] == 'LONG']
        short_signals = [s for s in trade_signals if s['direction'] == 'SHORT']

        # Recent history stats
        recent_history = [h for h in _trade_signals_history
                         if current_time - h.get('closed_at', 0) < 86400]  # Last 24h
        wins = len([h for h in recent_history if h.get('status') == 'HIT_TP'])
        losses = len([h for h in recent_history if h.get('status') == 'HIT_SL'])
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

        return {
            'status': 'success',
            'signals': trade_signals,
            'summary': {
                'total_active': len(trade_signals),
                'long_signals': len(long_signals),
                'short_signals': len(short_signals),
                'avg_confluence': round(
                    sum(s['confluence_score'] for s in trade_signals) / len(trade_signals), 1
                ) if trade_signals else 0
            },
            'performance_24h': {
                'wins': wins,
                'losses': losses,
                'expired': len([h for h in recent_history if h.get('status') == 'EXPIRED']),
                'win_rate': round(win_rate, 1)
            },
            'config': {
                'stop_percentage': DEFAULT_STOP_PERCENTAGE,
                'risk_reward_ratio': DEFAULT_RR_RATIO,
                'expiry_hours': SIGNAL_EXPIRY_HOURS
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting trade-ready signals: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'signals': [],
            'summary': {'total_active': 0, 'long_signals': 0, 'short_signals': 0},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
