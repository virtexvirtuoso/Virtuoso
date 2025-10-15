#!/usr/bin/env python3
"""
Simple web server for Virtuoso CCXT with basic dashboard functionality
"""

import asyncio
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# Create FastAPI app
app = FastAPI(
    title="Virtuoso Trading Dashboard",
    description="Simple web server with dashboard functionality",
    version="2.0.0"
)

# Add CORS middleware for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dashboard template endpoints
@app.get("/dashboard/")
async def serve_desktop_dashboard():
    """Serve desktop dashboard"""
    template_path = project_root / "src" / "dashboard" / "templates" / "dashboard.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Desktop dashboard not found"}

@app.get("/dashboard/mobile")
async def serve_mobile_dashboard():
    """Serve mobile dashboard"""
    template_path = project_root / "src" / "dashboard" / "templates" / "dashboard_mobile_v1.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Mobile dashboard not found"}

# Basic API endpoints for dashboard functionality
@app.get("/dashboard/api/market/overview")
async def market_overview():
    """Basic market overview endpoint"""
    return {
        "timestamp": datetime.now().isoformat(),
        "market_regime": "Bullish",
        "total_symbols": 50,
        "active_signals": 12,
        "btc_price": 65000,
        "btc_change": 2.5,
        "total_volume": 1250000000,
        "fear_greed_index": 75
    }

@app.get("/dashboard/api/signals/top")
async def top_signals():
    """Top trading signals"""
    return {
        "signals": [
            {
                "symbol": "BTCUSDT",
                "signal": "BUY",
                "confidence": 0.85,
                "price": 65000,
                "change": 2.5,
                "timestamp": datetime.now().isoformat()
            },
            {
                "symbol": "ETHUSDT",
                "signal": "BUY",
                "confidence": 0.78,
                "price": 2800,
                "change": 3.2,
                "timestamp": datetime.now().isoformat()
            },
            {
                "symbol": "SOLUSDT",
                "signal": "HOLD",
                "confidence": 0.65,
                "price": 180,
                "change": -1.5,
                "timestamp": datetime.now().isoformat()
            }
        ]
    }

@app.get("/dashboard/api/data")
async def dashboard_data():
    """Dashboard data for the web interface"""
    return {
        "market_overview": {
            "market_regime": "Bullish",
            "btc_price": 65000,
            "btc_change": 2.5,
            "total_volume": 1250000000,
            "active_symbols": 50
        },
        "top_movers": [
            {"symbol": "BTCUSDT", "change": 2.5, "price": 65000},
            {"symbol": "ETHUSDT", "change": 3.2, "price": 2800},
            {"symbol": "SOLUSDT", "change": -1.5, "price": 180}
        ],
        "alerts": [
            {
                "type": "SIGNAL",
                "message": "Strong bullish signal detected for BTCUSDT",
                "priority": "high",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "system_status": {
            "status": "online",
            "last_update": datetime.now().isoformat(),
            "uptime": "24h 30m"
        }
    }

@app.get("/dashboard/api/cache-status")
async def cache_status():
    """Cache status for dashboard"""
    return {
        "cache_hit_rate": 85.7,
        "cache_size": 1024,
        "cached_items": 156,
        "last_refresh": datetime.now().isoformat(),
        "status": "healthy"
    }

@app.get("/dashboard/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "dashboard_web_server",
        "mode": "dashboard_only"
    }

# Additional API endpoints that dashboards expect
@app.get("/api/health")
async def api_health():
    """API health check"""
    return {
        "status": "healthy",
        "service": "dashboard_api",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def root_health():
    """Root health check"""
    return {
        "status": "healthy",
        "service": "virtuoso_dashboard",
        "timestamp": datetime.now().isoformat()
    }

# Mobile dashboard API endpoints
@app.get("/api/dashboard-cached/overview")
async def cached_overview():
    """Cached dashboard overview for mobile"""
    return {
        "market_status": "active",
        "total_symbols": 50,
        "active_signals": 12,
        "btc_price": 65000,
        "btc_change": 2.5,
        "eth_price": 2800,
        "eth_change": 3.2,
        "timestamp": datetime.now().isoformat(),
        "cache_timestamp": datetime.now().isoformat()
    }

@app.get("/api/dashboard-cached/symbols")
async def cached_symbols():
    """Cached symbols data for mobile"""
    return {
        "symbols": [
            {"symbol": "BTCUSDT", "price": 65000, "change": 2.5, "volume": 1000000},
            {"symbol": "ETHUSDT", "price": 2800, "change": 3.2, "volume": 800000},
            {"symbol": "SOLUSDT", "price": 180, "change": -1.5, "volume": 400000},
            {"symbol": "ADAUSDT", "price": 0.45, "change": 1.8, "volume": 200000},
            {"symbol": "DOTUSDT", "price": 8.5, "change": -0.5, "volume": 150000}
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/dashboard-cached/market-overview")
async def cached_market_overview():
    """Cached market overview for mobile"""
    return {
        "market_regime": "Bullish",
        "fear_greed_index": 75,
        "total_market_cap": 2500000000000,
        "btc_dominance": 42.5,
        "active_pairs": 50,
        "volume_24h": 1250000000,
        "trending": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/dashboard-cached/mobile-data")
async def cached_mobile_data():
    """Mobile-specific cached data"""
    return {
        "quick_stats": {
            "portfolio_value": 10000,
            "daily_pnl": 250,
            "daily_pnl_pct": 2.5,
            "open_positions": 3
        },
        "alerts": [
            {
                "type": "signal",
                "message": "Strong buy signal for BTC",
                "timestamp": datetime.now().isoformat(),
                "priority": "high"
            }
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/dashboard-cached/signals")
async def cached_signals():
    """Cached signals for mobile"""
    return {
        "signals": [
            {
                "symbol": "BTCUSDT",
                "signal": "BUY",
                "confidence": 0.85,
                "price": 65000,
                "target": 67000,
                "stop_loss": 63000,
                "timestamp": datetime.now().isoformat()
            },
            {
                "symbol": "ETHUSDT",
                "signal": "BUY",
                "confidence": 0.78,
                "price": 2800,
                "target": 2900,
                "stop_loss": 2700,
                "timestamp": datetime.now().isoformat()
            }
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/dashboard-cached/opportunities")
async def cached_opportunities():
    """Cached opportunities for mobile"""
    return {
        "opportunities": [
            {
                "symbol": "BTCUSDT",
                "type": "momentum",
                "score": 85,
                "description": "Strong bullish momentum detected",
                "timeframe": "1h"
            },
            {
                "symbol": "ETHUSDT",
                "type": "reversal",
                "score": 78,
                "description": "Potential reversal pattern forming",
                "timeframe": "4h"
            }
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/dashboard-cached/alerts")
async def cached_alerts():
    """Cached alerts for mobile"""
    return {
        "alerts": [
            {
                "id": 1,
                "type": "SIGNAL",
                "symbol": "BTCUSDT",
                "message": "Strong bullish signal detected",
                "priority": "high",
                "timestamp": datetime.now().isoformat()
            },
            {
                "id": 2,
                "type": "PRICE",
                "symbol": "ETHUSDT",
                "message": "Price crossed resistance level",
                "priority": "medium",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "timestamp": datetime.now().isoformat()
    }

# Bitcoin Beta API endpoints
@app.get("/api/bitcoin-beta/realtime")
async def bitcoin_realtime():
    """Bitcoin beta realtime data"""
    return {
        "price": 65000,
        "change": 2.5,
        "change_pct": 2.5,
        "volume": 1000000,
        "high_24h": 66000,
        "low_24h": 63000,
        "market_cap": 1280000000000,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/bitcoin-beta/history/{symbol}")
async def bitcoin_history(symbol: str):
    """Bitcoin beta historical data"""
    return {
        "symbol": symbol,
        "timeframe": "1h",
        "data": [
            {"timestamp": datetime.now().isoformat(), "price": 65000, "volume": 1000000},
            {"timestamp": datetime.now().isoformat(), "price": 64800, "volume": 950000},
            {"timestamp": datetime.now().isoformat(), "price": 64600, "volume": 900000}
        ]
    }

# Cache metrics API endpoints
@app.get("/api/cache-metrics/overview")
async def cache_metrics_overview():
    """Cache metrics overview"""
    return {
        "hit_rate": 85.7,
        "miss_rate": 14.3,
        "total_requests": 10000,
        "cache_size_mb": 256,
        "evictions": 12,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/cache-metrics/hit-rates")
async def cache_hit_rates():
    """Cache hit rates"""
    return {
        "overall": 85.7,
        "by_endpoint": {
            "/api/market/overview": 92.1,
            "/api/signals/top": 87.3,
            "/api/dashboard/data": 83.5
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/cache-metrics/health")
async def cache_health():
    """Cache health metrics"""
    return {
        "status": "healthy",
        "memory_usage": 65.2,
        "cpu_usage": 12.3,
        "disk_usage": 45.1,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/cache-metrics/performance")
async def cache_performance():
    """Cache performance metrics"""
    return {
        "avg_response_time": 125.5,
        "p95_response_time": 250.0,
        "p99_response_time": 500.0,
        "throughput": 1000,
        "timestamp": datetime.now().isoformat()
    }

# Additional endpoints referenced in dashboards
@app.get("/api/dashboard/overview")
async def dashboard_overview():
    """Dashboard overview data"""
    return {
        "market_status": "active",
        "btc_price": 65000,
        "btc_change": 2.5,
        "total_volume": 1250000000,
        "active_signals": 12,
        "alerts_count": 3,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/signals")
async def api_signals():
    """API signals endpoint"""
    return {
        "signals": [
            {
                "symbol": "BTCUSDT",
                "signal": "BUY",
                "confidence": 0.85,
                "timestamp": datetime.now().isoformat()
            }
        ]
    }

@app.get("/api/alerts/recent")
async def recent_alerts():
    """Recent alerts"""
    return {
        "alerts": [
            {
                "id": 1,
                "type": "SIGNAL",
                "message": "Strong buy signal detected for BTCUSDT",
                "timestamp": datetime.now().isoformat(),
                "priority": "high"
            }
        ]
    }

@app.get("/api/alpha-opportunities")
async def alpha_opportunities():
    """Alpha opportunities"""
    return {
        "opportunities": [
            {
                "symbol": "BTCUSDT",
                "alpha_score": 0.85,
                "opportunity": "momentum",
                "description": "Strong momentum detected"
            }
        ]
    }

@app.get("/api/market-overview")
async def api_market_overview():
    """API market overview"""
    return {
        "market_regime": "Bullish",
        "btc_price": 65000,
        "btc_change": 2.5,
        "fear_greed": 75,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/confluence-analysis/{symbol}")
async def confluence_analysis(symbol: str):
    """Confluence analysis for symbol"""
    return {
        "symbol": symbol,
        "confluence_score": 0.78,
        "signals": ["technical", "momentum", "volume"],
        "analysis": f"Bullish confluence detected for {symbol}",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/symbols")
async def api_symbols():
    """API symbols list"""
    return {
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOTUSDT"],
        "count": 5,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/performance")
async def api_performance():
    """API performance metrics"""
    return {
        "uptime": "24h 30m",
        "requests_per_second": 125,
        "avg_response_time": 85,
        "error_rate": 0.1,
        "timestamp": datetime.now().isoformat()
    }

# Cache endpoints
@app.get("/api/cache/dashboard")
async def cache_dashboard():
    """Cache dashboard data"""
    return {
        "cache_status": "healthy",
        "hit_rate": 85.7,
        "size": 256,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/cache/health")
async def cache_health_alt():
    """Alternative cache health endpoint"""
    return {
        "status": "healthy",
        "cache_operational": True,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/cache/test")
async def cache_test():
    """Cache test endpoint"""
    return {
        "test": "passed",
        "cache_responding": True,
        "timestamp": datetime.now().isoformat()
    }

# Dashboard navigation endpoints
@app.get("/api/dashboard/mobile/beta-dashboard")
async def mobile_beta_fallback():
    """Mobile beta dashboard fallback"""
    return {
        "status": "beta",
        "features": ["realtime", "signals", "alerts"],
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/dashboard/confluence-analysis-page")
async def confluence_page(symbol: str = "BTCUSDT"):
    """Confluence analysis page redirect"""
    return {
        "redirect": f"/dashboard/confluence/{symbol}",
        "symbol": symbol,
        "timestamp": datetime.now().isoformat()
    }

def main():
    """Run the simple web server"""
    print("🚀 Starting Virtuoso Dashboard Web Server")
    print("=" * 40)
    print(f"📁 Project root: {project_root}")
    print(f"🌐 Dashboard URL: http://0.0.0.0:8004/dashboard/")
    print(f"📱 Mobile URL: http://0.0.0.0:8004/dashboard/mobile")
    print(f"📊 Dashboard API endpoints available at /dashboard/api/*")
    print("=" * 40)

    # Run uvicorn on port 8004
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8004,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()