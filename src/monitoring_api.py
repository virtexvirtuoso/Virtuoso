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

        # Initialize health monitor
        health_monitor = HealthMonitor()

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
                health_status = await health_monitor.get_health_status()
                status["health"] = health_status
            except Exception as e:
                status["health"] = {"error": str(e)}

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