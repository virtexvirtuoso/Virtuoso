#!/usr/bin/env python3
"""
Virtuoso CCXT Trading System - Monitoring API Service
=====================================================

Dedicated monitoring API service providing system health metrics,
performance monitoring, and cache statistics.
"""

import asyncio
import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import monitoring components
from src.monitoring.monitor import MarketMonitor
from src.monitoring.health_monitor import HealthMonitor
from src.api.cache_adapter_direct import DirectCacheAdapter
from src.api.websocket_health import get_websocket_health

app = FastAPI(
    title="Virtuoso Monitoring API",
    description="System monitoring and performance metrics API",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global monitoring instances
market_monitor = None
health_monitor = None
cache_adapter = None

@app.on_event("startup")
async def startup_event():
    """Initialize monitoring services"""
    global market_monitor, health_monitor, cache_adapter

    try:
        # Initialize cache adapter
        cache_adapter = DirectCacheAdapter()

        # Initialize health monitor with metrics manager
        from src.monitoring.metrics_manager import MetricsManager
        from src.monitoring.alert_manager import AlertManager

        # Create basic config and alert manager
        config = {'metrics': {'collection_interval': 60}, 'alerts': {}}
        alert_manager = AlertManager(config)
        metrics_manager = MetricsManager(config, alert_manager)
        health_monitor = HealthMonitor(metrics_manager)

        # Initialize market monitor if available
        try:
            market_monitor = MarketMonitor()
        except Exception as e:
            print(f"Warning: Could not initialize market monitor: {e}")

        print(f"Monitoring API started successfully on port {os.getenv('MONITORING_PORT', 8001)}")

    except Exception as e:
        print(f"Error during monitoring API startup: {e}")

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "monitoring-api"
    }

@app.get("/api/monitoring/status")
async def get_monitoring_status():
    """Get overall system monitoring status"""
    try:
        status = {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "cache_adapter": cache_adapter is not None,
                "health_monitor": health_monitor is not None,
                "market_monitor": market_monitor is not None
            },
            "uptime": time.time() - startup_time if 'startup_time' in globals() else 0
        }

        # Add health monitor status if available
        if health_monitor:
            try:
                # Check if it's an async or sync method
                if hasattr(health_monitor, 'get_health_status'):
                    health_status = await health_monitor.get_health_status()
                elif hasattr(health_monitor, '_get_health_status'):
                    health_status = health_monitor._get_health_status()
                else:
                    health_status = {"status": "unknown", "message": "Health monitor method not found"}
                status["health"] = health_status
            except Exception as e:
                status["health"] = {"error": f"'HealthMonitor' object has no attribute 'get_health_status'", "details": str(e)}

        return status

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting monitoring status: {str(e)}")

@app.get("/api/monitoring/metrics")
async def get_metrics():
    """Get system performance metrics"""
    try:
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "cache": {},
            "system": {}
        }

        # Get cache metrics if available
        if cache_adapter:
            try:
                cache_stats = cache_adapter.get_stats()
                metrics["cache"] = cache_stats
            except Exception as e:
                metrics["cache"] = {"error": str(e)}

        # Get system metrics if health monitor available
        if health_monitor:
            try:
                system_metrics = await health_monitor.get_system_metrics()
                metrics["system"] = system_metrics
            except Exception as e:
                metrics["system"] = {"error": str(e)}

        return metrics

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting metrics: {str(e)}")

@app.get("/api/monitoring/cache")
async def get_cache_metrics():
    """Get detailed cache performance metrics"""
    try:
        if not cache_adapter:
            raise HTTPException(status_code=503, detail="Cache adapter not available")

        cache_stats = cache_adapter.get_stats()

        # Add additional cache analysis
        cache_metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "stats": cache_stats,
            "performance": {
                "hit_rate": cache_stats.get("cache_hit_rate", 0),
                "total_requests": cache_stats.get("total_requests", 0),
                "total_hits": cache_stats.get("cache_hits", 0),
                "total_misses": cache_stats.get("cache_misses", 0)
            }
        }

        return cache_metrics

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache metrics: {str(e)}")

@app.get("/api/monitoring/symbols")
async def get_symbol_monitoring():
    """Get monitoring status for active symbols"""
    try:
        if not market_monitor:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "symbols": [],
                "status": "market_monitor_not_available"
            }

        # Get active symbols from market monitor
        symbols_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbols": [],
            "total_symbols": 0
        }

        return symbols_status

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting symbol monitoring: {str(e)}")

@app.get("/api/monitoring/websocket")
async def get_websocket_health():
    """Get comprehensive WebSocket health status and diagnostics"""
    try:
        # Get market data manager from market monitor
        market_data_manager = None
        if market_monitor and hasattr(market_monitor, 'market_data_manager'):
            market_data_manager = market_monitor.market_data_manager

        # Get comprehensive WebSocket health
        websocket_health = await get_websocket_health(market_data_manager)

        return websocket_health

    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "error",
            "websocket": {
                "connected": False,
                "status": "error",
                "error": str(e)
            },
            "checks": [{
                "name": "websocket_health_check",
                "status": "failed",
                "message": f"Error getting WebSocket health: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }],
            "recommendations": [{
                "priority": "critical",
                "category": "system_error",
                "title": "WebSocket Health Check Failed",
                "description": "Unable to retrieve WebSocket health status",
                "action": "Check system logs and restart monitoring service"
            }]
        }

@app.get("/api/monitoring/websocket/status")
async def get_websocket_status_simple():
    """Get simple WebSocket connection status"""
    try:
        # Get market data manager from market monitor
        market_data_manager = None
        if market_monitor and hasattr(market_monitor, 'market_data_manager'):
            market_data_manager = market_monitor.market_data_manager

        if not market_data_manager:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "connected": False,
                "status": "market_data_manager_unavailable",
                "message": "MarketDataManager not available"
            }

        # Get WebSocket status from market monitor
        if hasattr(market_monitor, 'get_websocket_status'):
            ws_status = market_monitor.get_websocket_status()
        else:
            # Fallback: get status directly from websocket manager
            ws_manager = getattr(market_data_manager, 'websocket_manager', None)
            if ws_manager and hasattr(ws_manager, 'get_status'):
                ws_status = ws_manager.get_status()
            else:
                ws_status = {
                    "connected": False,
                    "status": "websocket_manager_unavailable"
                }

        # Add timestamp to response
        ws_status["timestamp"] = datetime.utcnow().isoformat()

        return ws_status

    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "connected": False,
            "status": "error",
            "message": f"Error getting WebSocket status: {str(e)}"
        }

@app.get("/api/monitoring/websocket/history")
async def get_websocket_health_history():
    """Get WebSocket health history and trends"""
    try:
        from src.api.websocket_health import websocket_health_monitor

        history = websocket_health_monitor.get_health_history(limit=50)
        trends = websocket_health_monitor.get_health_trends()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "history": history,
            "trends": trends,
            "count": len(history)
        }

    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "message": f"Error getting WebSocket health history: {str(e)}",
            "history": [],
            "trends": {}
        }

if __name__ == "__main__":
    startup_time = time.time()

    # Get port from environment
    port = int(os.getenv("MONITORING_PORT", 8001))

    print(f"Starting Virtuoso Monitoring API on port {port}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )