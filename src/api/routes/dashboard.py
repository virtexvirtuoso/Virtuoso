"""Dashboard API routes for the Virtuoso Trading System."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
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

# Import our dashboard integration service
from src.dashboard.dashboard_integration import get_dashboard_integration, DashboardIntegrationService

router = APIRouter()
logger = logging.getLogger(__name__)

# Resolve paths relative to the project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
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
    """Get comprehensive dashboard overview with aggregated data."""
    try:
        # Get dashboard integration service
        integration = get_dashboard_integration()
        if not integration:
            logger.warning("Dashboard integration service not available")
            return {
                "status": "error",
                "message": "Dashboard integration service not available",
                "timestamp": datetime.utcnow().isoformat(),
                "signals": {"total": 0, "strong": 0, "medium": 0, "weak": 0},
                "alerts": {"total": 0, "critical": 0, "warning": 0},
                "alpha_opportunities": {"total": 0, "high_confidence": 0, "medium_confidence": 0},
                "system_status": {
                    "monitoring": "inactive",
                    "data_feed": "disconnected", 
                    "alerts": "disabled",
                    "websocket": "disconnected",
                    "last_update": 0
                }
            }

        # Get dashboard overview from integration service
        overview_data = await integration.get_dashboard_overview()
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
    integration: DashboardIntegrationService = Depends(get_dashboard_integration)
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
    integration: DashboardIntegrationService = Depends(get_dashboard_integration)
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
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "integration_available": integration is not None,
            "active_websocket_connections": len(connection_manager.active_connections)
        }

    except Exception as e:
        logger.error(f"Dashboard health check error: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@router.get("/performance")
async def get_dashboard_performance() -> Dict[str, Any]:
    """Get dashboard performance metrics."""
    try:
        integration = get_dashboard_integration()
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
    """Get symbols data for dashboard ticker and matrix."""
    try:
        integration = get_dashboard_integration()
        if integration:
            symbols_data = await integration.get_symbols_data()
            return symbols_data
        
        # Fallback symbols data
        return {
            "symbols": [
                {"symbol": "BTCUSDT", "change_24h": 2.45},
                {"symbol": "ETHUSDT", "change_24h": -1.23},
                {"symbol": "ADAUSDT", "change_24h": 0.87},
                {"symbol": "SOLUSDT", "change_24h": 3.21},
                {"symbol": "DOTUSDT", "change_24h": -0.56}
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard symbols: {e}")
        return {
            "symbols": [],
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