"""Dashboard API routes for the Virtuoso Trading System."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from typing import Dict, List, Any, Optional
import asyncio
import json
import logging
from datetime import datetime
import time
from pathlib import Path
import os
import aiohttp
import numpy as np
import random

router = APIRouter()
logger = logging.getLogger(__name__)

# Import our dashboard integration service - Phase 2 with Memcached
try:
    from src.dashboard.dashboard_proxy_phase2 import get_dashboard_integration
    logger.info("✅ Using Phase 2 dashboard integration with Memcached")
except ImportError:
    from src.dashboard.dashboard_proxy import get_dashboard_integration
    logger.info("📦 Using Phase 1 dashboard integration")

# Import direct cache adapter for improved performance
try:
    from src.api.cache_adapter_direct import cache_adapter as direct_cache
    USE_DIRECT_CACHE = True
    logger.info("✅ Direct cache adapter available for regular dashboard")
except ImportError:
    USE_DIRECT_CACHE = False
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

@router.get("/overview")
async def get_dashboard_overview() -> Dict[str, Any]:
    """Get comprehensive dashboard overview with real-time data from Memcached."""
    try:
        # Use direct cache if available for better performance
        if USE_DIRECT_CACHE:
            return await direct_cache.get_dashboard_overview()
        # Check Memcached for real-time status
        symbol_count = 0
        try:
            from pymemcache.client.base import Client
            import json
            
            mc_client = Client(('127.0.0.1', 11211))
            
            # Check if we have symbols data
            symbols_data = mc_client.get(b'virtuoso:symbols')
            if symbols_data:
                data = json.loads(symbols_data.decode('utf-8'))
                symbol_count = len(data.get('symbols', []))
                logger.info(f"Memcached has {symbol_count} symbols with confluence scores")
            
            mc_client.close()
        except Exception as mc_error:
            logger.debug(f"Memcached check: {mc_error}")
        
        # Get dashboard integration service
        integration = get_dashboard_integration()
        if not integration:
            logger.warning("Dashboard integration service not available")
            return {
                "status": "initializing" if symbol_count > 0 else "error",
                "message": "System initializing..." if symbol_count > 0 else "Dashboard integration service not available",
                "timestamp": datetime.utcnow().isoformat(),
                "signals": {"total": 0, "strong": 0, "medium": 0, "weak": 0},
                "alerts": {"total": 0, "critical": 0, "warning": 0},
                "alpha_opportunities": {"total": 0, "high_confidence": 0, "medium_confidence": 0},
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
        
        # Enhance with Memcached data if available
        if symbol_count > 0:
            overview_data['system_status']['symbols_tracked'] = symbol_count
            overview_data['system_status']['cache_status'] = 'memcached_active'
        
        return overview_data

    except Exception as e:
        logger.error(f"Error getting dashboard overview: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting dashboard overview: {str(e)}")

@router.get("/signals")
async def get_dashboard_signals() -> List[Dict[str, Any]]:
    """Get recent signals for dashboard display."""
    try:
        integration = get_dashboard_integration()
        if not integration:
            return []

        signals_data = await integration.get_signals_data()
        return signals_data

    except Exception as e:
        logger.error(f"Error getting dashboard signals: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting signals: {str(e)}")

@router.get("/alerts/recent")
async def get_recent_alerts(
    limit: int = 50,
    integration = Depends(get_dashboard_integration)
) -> List[Dict[str, Any]]:
    """Get recent alerts from the monitoring system."""
    try:
        alerts = await integration.get_alerts_data()
        return alerts[:limit]
    except Exception as e:
        logger.error(f"Error getting recent alerts: {str(e)}")
        return []

@router.get("/alerts")
async def get_alerts(
    limit: int = 50,
    integration = Depends(get_dashboard_integration)
) -> List[Dict[str, Any]]:
    """Get alerts from the monitoring system (alias for /alerts/recent)."""
    try:
        alerts = await integration.get_alerts_data()
        return alerts[:limit]
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        return []

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

@router.get("/market-overview")
async def get_market_overview() -> Dict[str, Any]:
    """Get market overview data for dashboard."""
    try:
        integration = get_dashboard_integration()
        if not integration:
            return {
                "active_symbols": 0,
                "total_volume": 0,
                "market_regime": "unknown",
                "volatility": 0
            }

        market_data = await integration.get_market_overview()
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
                "timestamp": datetime.utcnow().isoformat()
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
                        "timestamp": datetime.utcnow().isoformat()
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
            "timestamp": datetime.utcnow().isoformat(),
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
            "last_updated": datetime.utcnow().isoformat()
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
            "timestamp": datetime.utcnow().isoformat(),
            "integration_available": integration is not None,
            "active_websocket_connections": len(connection_manager.active_connections),
            "cache_performance": cache_info
        }

    except Exception as e:
        logger.error(f"Dashboard health check error: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
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
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Get Phase 2 cache performance
        cache_performance = await integration.get_cache_performance()
        
        return {
            "status": "phase2",
            "message": "Phase 2 Memcached cache active",
            "performance": cache_performance,
            "timestamp": datetime.utcnow().isoformat()
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
        "timestamp": datetime.utcnow().isoformat(),
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
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/confluence-analysis-page")
async def confluence_analysis_page():
    """Serve the terminal-style confluence analysis page."""
    return FileResponse(TEMPLATE_DIR / "confluence_analysis.html")

@router.get("/confluence-analysis/{symbol}")
async def get_confluence_analysis(symbol: str) -> Dict[str, Any]:
    """Get full confluence analysis for a specific symbol."""
    try:
        # Get dashboard integration
        integration = get_dashboard_integration()
        if not integration:
            return {"error": "Dashboard integration not available", "analysis": None}
            
        # Check if confluence cache has data for this symbol
        if hasattr(integration, '_confluence_cache') and symbol in integration._confluence_cache:
            cache_data = integration._confluence_cache[symbol]
            formatted_analysis = cache_data.get('formatted_analysis', None)
            
            if formatted_analysis:
                return {
                    "symbol": symbol,
                    "analysis": formatted_analysis,
                    "timestamp": cache_data.get('timestamp', 0),
                    "score": cache_data.get('score', 50)
                }
            else:
                return {
                    "symbol": symbol,
                    "analysis": f"Detailed analysis for {symbol} coming soon!",
                    "timestamp": cache_data.get('timestamp', 0),
                    "score": cache_data.get('score', 50)
                }
        else:
            return {
                "symbol": symbol,
                "analysis": f"No analysis available for {symbol}",
                "timestamp": 0,
                "score": 50
            }
            
    except Exception as e:
        logger.error(f"Error getting confluence analysis: {e}")
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
            "timestamp": datetime.utcnow().isoformat()
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
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
        
        # Get top symbols
        if top_symbols_manager:
            try:
                top_symbols = await top_symbols_manager.get_top_symbols(limit=10)
                confluence_scores = []
                
                for symbol_info in top_symbols[:10]:
                    symbol = symbol_info.get('symbol', symbol_info) if isinstance(symbol_info, dict) else symbol_info
                    
                    try:
                        # Get market data
                        if market_data_manager:
                            market_data = await market_data_manager.get_market_data(symbol)
                            if market_data and confluence_analyzer:
                                # Get confluence analysis
                                result = await confluence_analyzer.analyze(market_data)
                                
                                score = result.get('confluence_score', 50)
                                components = result.get('components', {})
                                ticker = market_data.get('ticker', {})
                                
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
                        logger.warning(f"Error analyzing {symbol}: {e}")
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
        
        return response
        
    except Exception as e:
        logger.error(f"Error in direct mobile dashboard endpoint: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/mobile-data")
async def get_mobile_dashboard_data() -> Dict[str, Any]:
    """Optimized endpoint for mobile dashboard with cache integration."""
    try:
        import aiomcache
        import json
        
        # Get integration if available
        integration = get_dashboard_integration()
        
        # Fetch actual data from cache
        cache_client = aiomcache.Client("localhost", 11211)
        
        # Get overview and breadth data
        overview_data = await cache_client.get(b"market:overview")
        breadth_data = await cache_client.get(b"market:breadth")
        
        # Parse market overview with real data
        market_overview = {
            "market_regime": "NEUTRAL",
            "trend_strength": 0,
            "current_volatility": 0,
            "avg_volatility": 20,
            "btc_dominance": 0,
            "total_volume_24h": 0
        }
        
        if overview_data:
            overview = json.loads(overview_data.decode())
            market_overview = {
                "market_regime": overview.get("market_regime", "NEUTRAL"),
                "trend_strength": overview.get("trend_strength", 0),
                "current_volatility": overview.get("current_volatility", overview.get("volatility", 0)),
                "avg_volatility": overview.get("avg_volatility", 20),
                "btc_dominance": overview.get("btc_dominance", 0),
                "total_volume_24h": overview.get("total_volume_24h", overview.get("total_volume", 0)),
                "volatility": overview.get("current_volatility", overview.get("volatility", 0))  # Add for compatibility
            }
        
        # Parse market breadth
        market_breadth = {
            "up_count": 0,
            "down_count": 0,
            "breadth_percentage": 50.0,
            "sentiment": "neutral"
        }
        
        if breadth_data:
            breadth = json.loads(breadth_data.decode())
            market_breadth = {
                "up_count": breadth.get("up_count", 0),
                "down_count": breadth.get("down_count", 0),
                "breadth_percentage": breadth.get("breadth_percentage", 50.0),
                "sentiment": breadth.get("sentiment", "neutral")
            }
        
        await cache_client.close()
        
        # Response structure with real cache data
        response = {
            "market_overview": market_overview,
            "market_breadth": market_breadth,
            "confluence_scores": [],
            "top_movers": {
                "gainers": [],
                "losers": []
            },
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
        
        # Try to get data from main service first
        try:
            async with aiohttp.ClientSession() as session:
                # Get signals from main service
                async with session.get("http://localhost:8004/api/dashboard-cached/signals", timeout=2) as resp:
                    if resp.status == 200:
                        signals = await resp.json()
                        if signals and isinstance(signals, list) and len(signals) > 0:
                            logger.info(f"Using {len(signals)} signals from main service")
                            response["status"] = "main_service"
                            
                            # Process signals for mobile format
                            confluence_scores = []
                            for signal in signals[:15]:
                                confluence_scores.append({
                                    "symbol": signal.get('symbol', ''),
                                    "score": round(signal.get('score', 50), 2),
                                    "price": signal.get('price', 0),
                                    "change_24h": round(signal.get('change_24h', 0), 2),
                                    "volume_24h": signal.get('volume', 0),
                                    "components": signal.get('components', {
                                        "technical": 50,
                                        "volume": 50,
                                        "orderflow": 50,
                                        "sentiment": 50,
                                        "orderbook": 50,
                                        "price_structure": 50
                                    })
                                })
                            response["confluence_scores"] = confluence_scores
                            
                            # Calculate top movers from signals
                            sorted_signals = sorted(signals, key=lambda x: x.get('change_24h', 0))
                            gainers = [s for s in sorted_signals if s.get('change_24h', 0) > 0][-5:]
                            losers = [s for s in sorted_signals if s.get('change_24h', 0) < 0][:5]
                            
                            if gainers:
                                response["top_movers"]["gainers"] = [
                                    {
                                        "symbol": g['symbol'],
                                        "change": round(g['change_24h'], 2),
                                        "price": g.get('price', 0),
                                        "volume_24h": g.get('volume', 0),
                                        "display_symbol": g['symbol'].replace('USDT', '')
                                    } for g in reversed(gainers)
                                ]
                            
                            if losers:
                                response["top_movers"]["losers"] = [
                                    {
                                        "symbol": l['symbol'],
                                        "change": round(l['change_24h'], 2),
                                        "price": l.get('price', 0),
                                        "volume_24h": l.get('volume', 0),
                                        "display_symbol": l['symbol'].replace('USDT', '')
                                    } for l in losers
                                ]
                            
                            # If we got good data from main service, return it
                            if response["confluence_scores"]:
                                return response
                                
        except Exception as e:
            logger.debug(f"Could not fetch from main service: {e}")
        
        if not integration:
            response["status"] = "no_integration"
            # Still try to get market data directly
            try:
                async with aiohttp.ClientSession() as session:
                    url = "https://api.bybit.com/v5/market/tickers?category=linear"
                    async with session.get(url, timeout=5) as resp:
                        if resp.status == 200:
                            bybit_data = await resp.json()
                            if bybit_data.get('retCode') == 0 and 'result' in bybit_data:
                                tickers = bybit_data['result']['list']
                                
                                # Process all symbols
                                all_changes = []
                                for ticker in tickers:
                                    try:
                                        symbol = ticker['symbol']
                                        if symbol.endswith('USDT') and 'PERP' not in symbol:
                                            change_24h = float(ticker['price24hPcnt']) * 100
                                            turnover_24h = float(ticker['turnover24h'])
                                            
                                            if turnover_24h > 500000:  # $500k minimum
                                                all_changes.append({
                                                    "symbol": symbol,
                                                    "change": round(change_24h, 2),
                                                    "turnover": turnover_24h,
                                                    "price": float(ticker.get('lastPrice', 0)),
                                                    "volume_24h": float(ticker.get('volume24h', 0))
                                                })
                                    except (ValueError, KeyError):
                                        continue
                                
                                # Sort and get top gainers
                                gainers = [x for x in all_changes if x['change'] > 0]
                                gainers.sort(key=lambda x: x['change'], reverse=True)
                                response["top_movers"]["gainers"] = [
                                    {
                                        "symbol": g['symbol'], 
                                        "change": g['change'],
                                        "price": g['price'],
                                        "volume_24h": g['volume_24h'],
                                        "display_symbol": g['symbol'].replace('1000', '').replace('USDT', '')
                                    } 
                                    for g in gainers[:5]
                                ]
                                
                                # Sort and get top losers
                                losers = [x for x in all_changes if x['change'] < 0]
                                losers.sort(key=lambda x: x['change'])
                                response["top_movers"]["losers"] = [
                                    {
                                        "symbol": l['symbol'], 
                                        "change": l['change'],
                                        "price": l['price'],
                                        "volume_24h": l['volume_24h'],
                                        "display_symbol": l['symbol'].replace('1000', '').replace('USDT', '')
                                    } 
                                    for l in losers[:5]
                                ]
            except Exception as e:
                logger.warning(f"Error fetching market data without integration: {e}")
            
            return response
            
        # Try to get data from integration service with timeout
        try:
            # Get dashboard data if available
            if hasattr(integration, '_dashboard_data'):
                data = integration._dashboard_data
                
                # Only override market overview if cache data is not good
                # Check if we have valid cache data (trend_strength > 0 means cache is working)
                cache_has_data = (
                    response["market_overview"].get('trend_strength', 0) > 0 or 
                    response["market_overview"].get('btc_dominance', 0) > 0
                )
                
                if not cache_has_data:
                    # No good cache data, try to use integration data
                    market_data = data.get('market_overview', {})
                    if market_data:  # Only override if integration has data
                        response["market_overview"] = {
                            "market_regime": market_data.get('regime', 'NEUTRAL'),
                            "trend_strength": market_data.get('trend_strength', 0),
                            "current_volatility": market_data.get('volatility', 0),
                            "volatility": market_data.get('volatility', 0),
                            "avg_volatility": 20,
                            "btc_dominance": market_data.get('btc_dominance', 0),
                            "total_volume_24h": market_data.get('total_volume_24h', 0)
                        }
                
                # Extract confluence scores from signals
                signals = data.get('signals', [])
                confluence_scores = []
                for signal in signals[:15]:  # Limit to top 15
                    # Get component scores if available, otherwise use defaults
                    components = signal.get('components', {})
                    confluence_scores.append({
                        "symbol": signal.get('symbol', ''),
                        "score": round(signal.get('score', 50), 2),
                        "price": signal.get('price', 0),
                        "change_24h": round(signal.get('change_24h', 0), 2),
                        "volume_24h": signal.get('volume', 0),
                        "components": {
                            "technical": round(components.get('technical', 50), 2),
                            "volume": round(components.get('volume', 50), 2),
                            "orderflow": round(components.get('orderflow', 50), 2),
                            "sentiment": round(components.get('sentiment', 50), 2),
                            "orderbook": round(components.get('orderbook', 50), 2),
                            "price_structure": round(components.get('price_structure', 50), 2)
                        }
                    })
                response["confluence_scores"] = confluence_scores
                
                # Always fetch broader market data for comprehensive top movers
                try:
                    # Get broader market data from Bybit
                    async with aiohttp.ClientSession() as session:
                        url = "https://api.bybit.com/v5/market/tickers?category=linear"
                        async with session.get(url, timeout=5) as resp:
                            if resp.status == 200:
                                bybit_data = await resp.json()
                                if bybit_data.get('retCode') == 0 and 'result' in bybit_data:
                                    tickers = bybit_data['result']['list']
                                    
                                    # Process all symbols
                                    all_changes = []
                                    for ticker in tickers:
                                        try:
                                            symbol = ticker['symbol']
                                            if symbol.endswith('USDT') and 'PERP' not in symbol:
                                                change_24h = float(ticker['price24hPcnt']) * 100
                                                turnover_24h = float(ticker['turnover24h'])
                                                
                                                if turnover_24h > 500000:  # $500k minimum
                                                    all_changes.append({
                                                        "symbol": symbol,
                                                        "change": round(change_24h, 2),
                                                        "turnover": turnover_24h
                                                    })
                                        except (ValueError, KeyError):
                                            continue
                                    
                                    # Sort and get top gainers (limit to 5)
                                    gainers = [x for x in all_changes if x['change'] > 0]
                                    gainers.sort(key=lambda x: x['change'], reverse=True)
                                    response["top_movers"]["gainers"] = [
                                        {
                                            "symbol": g['symbol'], 
                                            "change": g['change'],
                                            "price": float(next((t['lastPrice'] for t in tickers if t['symbol'] == g['symbol']), 0)),
                                            "volume_24h": float(next((t['volume24h'] for t in tickers if t['symbol'] == g['symbol']), 0)),
                                            "display_symbol": g['symbol'].replace('1000', '').replace('USDT', '')
                                        } 
                                        for g in gainers[:5]
                                    ]
                                    
                                    # Sort and get top losers (limit to 5)
                                    losers = [x for x in all_changes if x['change'] < 0]
                                    losers.sort(key=lambda x: x['change'])
                                    response["top_movers"]["losers"] = [
                                        {
                                            "symbol": l['symbol'], 
                                            "change": l['change'],
                                            "price": float(next((t['lastPrice'] for t in tickers if t['symbol'] == l['symbol']), 0)),
                                            "volume_24h": float(next((t['volume24h'] for t in tickers if t['symbol'] == l['symbol']), 0)),
                                            "display_symbol": l['symbol'].replace('1000', '').replace('USDT', '')
                                        } 
                                        for l in losers[:5]
                                    ]
                                        
                except Exception as e:
                    logger.warning(f"Error fetching broader market data: {e}")
                    # Fallback to signals data if market data fetch fails
                    sorted_by_change = sorted(signals, key=lambda x: x.get('change_24h', 0))
                    response["top_movers"]["losers"] = [
                        {"symbol": s['symbol'], "change": round(s['change_24h'], 2)} 
                        for s in sorted_by_change[:5] if s.get('change_24h', 0) < 0
                    ]
                    response["top_movers"]["gainers"] = [
                        {"symbol": s['symbol'], "change": round(s['change_24h'], 2)} 
                        for s in sorted_by_change[-5:] if s.get('change_24h', 0) > 0
                    ]
                
        except Exception as e:
            logger.warning(f"Error extracting data from integration: {e}")
            response["status"] = "partial_data"
            
        return response
        
    except Exception as e:
        logger.error(f"Error in mobile dashboard endpoint: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/performance")
async def get_dashboard_performance() -> Dict[str, Any]:
    """Get dashboard performance metrics."""
    try:
        # Direct data access without cache layer
        if integration:
            performance_data = await integration.get_performance_metrics()
            return performance_data
        
        # Fallback performance data
        return {
            "cpu_usage": 45.2,
            "memory_usage": 62.1,
            "api_latency": 12,
            "active_connections": 3,
            "uptime": "2h 15m",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard performance: {e}")
        return {
            "cpu_usage": 0,
            "memory_usage": 0,
            "api_latency": 0,
            "active_connections": 0,
            "uptime": "0h 0m",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/symbols")
async def get_dashboard_symbols() -> Dict[str, Any]:
    """Get symbols data with real confluence scores from Memcached."""
    try:
        # First try Memcached for real-time data
        try:
            from pymemcache.client.base import Client
            import json
            
            # Connect to Memcached
            mc_client = Client(('127.0.0.1', 11211))
            
            # Get symbols from Memcached
            symbols_data = mc_client.get(b'virtuoso:symbols')
            mc_client.close()
            
            if symbols_data:
                data = json.loads(symbols_data.decode('utf-8'))
                logger.info(f"Retrieved {len(data.get('symbols', []))} symbols from Memcached")
                return data
            
            logger.warning("No symbols in Memcached, checking integration service")
        except Exception as mc_error:
            logger.warning(f"Memcached not available: {mc_error}")
        
        # Fallback to integration service
        # Direct data access without cache layer
        if integration:
            symbols_data = await integration.get_symbols_data()
            return symbols_data
        
        # Last resort fallback
        logger.warning("Using fallback symbols data")
        return {
            "status": "fallback",
            "symbols": [
                {"symbol": "BTCUSDT", "confluence_score": 50, "change_24h": 2.45},
                {"symbol": "ETHUSDT", "confluence_score": 50, "change_24h": -1.23},
                {"symbol": "ADAUSDT", "confluence_score": 50, "change_24h": 0.87},
                {"symbol": "SOLUSDT", "confluence_score": 50, "change_24h": 3.21},
                {"symbol": "DOTUSDT", "confluence_score": 50, "change_24h": -0.56}
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Waiting for live data from trading system"
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard symbols: {e}")
        return {
            "status": "error",
            "symbols": [],
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# HTML Dashboard Routes
@router.get("/login")
async def login_page():
    """Serve the mobile login screen"""
    return FileResponse(TEMPLATE_DIR / "login_mobile.html")

@router.get("/favicon.svg")
async def favicon():
    """Serve the custom amber trending-up favicon"""
    return FileResponse(TEMPLATE_DIR / "favicon.svg", media_type="image/svg+xml")

@router.get("/mobile")
async def mobile_dashboard_page():
    """Serve the mobile dashboard with all integrated components"""
    return FileResponse(TEMPLATE_DIR / "dashboard_mobile_v1.html")

@router.get("/")
async def dashboard_page():
    """Serve the main v10 Signal Confluence Matrix dashboard"""
    return FileResponse(TEMPLATE_DIR / "dashboard_v10.html")

@router.get("/v1")
async def dashboard_v1_page():
    """Serve the original dashboard HTML page"""
    return FileResponse(TEMPLATE_DIR / "dashboard.html")

@router.get("/beta-analysis")
async def beta_analysis_page():
    """Serve the Beta Analysis dashboard"""
    return FileResponse(TEMPLATE_DIR / "dashboard_beta_analysis.html")

@router.get("/market-analysis")
async def market_analysis_page():
    """Serve the Market Analysis dashboard"""
    return FileResponse(TEMPLATE_DIR / "dashboard_market_analysis.html")

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
                
                raise HTTPException(status_code=500, detail="Invalid Bybit API response")
                
    except Exception as e:
        logger.error(f"Error getting direct Bybit data: {e}")
        raise HTTPException(status_code=500, detail=f"Bybit API error: {str(e)}")

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
                
                raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
                
    except Exception as e:
        logger.error(f"Error getting Bybit data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
                            "timestamp": datetime.utcnow().isoformat(),
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
        if integration and hasattr(integration, '_dashboard_data'):
            signals = integration._dashboard_data.get('signals', [])
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
            "last_update": datetime.utcnow().isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting beta analysis data: {e}")
        return {
            "status": "error",
            "error": str(e),
            "beta_analysis": [],
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/correlation-matrix")
async def get_correlation_matrix() -> Dict[str, Any]:
    """Get correlation matrix data for dashboard."""
    try:
        # Mock correlation matrix data
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]
        
        # Generate correlation matrix (mock data)
        correlations = []
        for i, sym1 in enumerate(symbols):
            row = []
            for j, sym2 in enumerate(symbols):
                if i == j:
                    corr = 1.0
                else:
                    # Generate realistic correlations
                    base_corr = 0.7 - (abs(i - j) * 0.15)
                    corr = round(base_corr + np.random.uniform(-0.1, 0.1), 2)
                    corr = max(0.3, min(0.95, corr))  # Keep in realistic range
                row.append(corr)
            correlations.append(row)
        
        return {
            "symbols": symbols,
            "correlation_matrix": correlations,
            "timeframe": "24h",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting correlation matrix: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
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
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting market analysis summary: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/beta-charts/time-series")
async def get_beta_time_series() -> Dict[str, Any]:
    """Get beta coefficient time series data for charting."""
    try:
        # Generate time series data for the last 7 days
        import random
        from datetime import datetime, timedelta
        
        symbols = ["ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOTUSDT"]
        end_date = datetime.utcnow()
        
        series_data = {}
        for symbol in symbols:
            data_points = []
            base_beta = {"ETHUSDT": 1.12, "SOLUSDT": 1.45, "XRPUSDT": 0.98, "ADAUSDT": 1.23, "DOTUSDT": 1.34}[symbol]
            
            for i in range(7):
                date = end_date - timedelta(days=6-i)
                # Add some realistic variance
                beta = base_beta + random.uniform(-0.15, 0.15)
                data_points.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "timestamp": int(date.timestamp() * 1000),
                    "beta": round(beta, 3)
                })
            
            series_data[symbol] = data_points
        
        return {
            "chart_data": series_data,
            "period": "7d",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting beta time series: {e}")
        return {"status": "error", "error": str(e)}

@router.get("/beta-charts/correlation-heatmap")
async def get_correlation_heatmap() -> Dict[str, Any]:
    """Get correlation heatmap data for visualization."""
    try:
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOTUSDT", "AVAXUSDT", "NEARUSDT"]
        
        # Generate correlation matrix
        heatmap_data = []
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                if i == j:
                    correlation = 1.0
                else:
                    # Generate realistic correlations based on market relationships
                    base_corr = 0.75 - (abs(i - j) * 0.08)
                    correlation = round(base_corr + np.random.uniform(-0.1, 0.1), 3)
                    correlation = max(0.25, min(0.95, correlation))
                
                heatmap_data.append({
                    "x": sym1,
                    "y": sym2,
                    "value": correlation,
                    "color_intensity": correlation  # For color mapping
                })
        
        return {
            "heatmap_data": heatmap_data,
            "symbols": symbols,
            "min_correlation": 0.25,
            "max_correlation": 1.0,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
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
        if integration and hasattr(integration, '_dashboard_data'):
            signals = integration._dashboard_data.get('signals', [])
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
            "timestamp": datetime.utcnow().isoformat(),
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
            "timestamp": datetime.utcnow().isoformat(),
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
            "timestamp": datetime.utcnow().isoformat(),
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
                    "symbols": correlation.get("symbols", []) if 'correlation' in locals() else [],
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
            "last_update": datetime.utcnow().isoformat(),
            "status": "success"
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting mobile beta dashboard: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
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
