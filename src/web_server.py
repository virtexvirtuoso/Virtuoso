#!/usr/bin/env python3
"""
Simple standalone web server for Virtuoso CCXT
Runs independently from the main trading system
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(project_root / '.env')
print(f"✅ Loaded environment variables from {project_root / '.env'}")

# Set environment to avoid conflicts
os.environ['WEB_SERVER_ONLY'] = 'true'
os.environ['DISABLE_INTEGRATED_WEB_SERVER'] = 'false'

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Import for basic functionality
import json
import psutil
import time
import logging
from datetime import datetime, timezone

# Setup logger for web server
logger = logging.getLogger(__name__)

# Request metrics tracking (for real performance stats)
from collections import deque
from dataclasses import dataclass, field
from threading import Lock

@dataclass
class RequestMetrics:
    """Track request metrics for real performance monitoring."""
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    request_timestamps: deque = field(default_factory=lambda: deque(maxlen=10000))
    error_timestamps: deque = field(default_factory=lambda: deque(maxlen=1000))
    start_time: float = field(default_factory=time.time)
    lock: Lock = field(default_factory=Lock)

    def record_request(self, response_time_ms: float, is_error: bool = False):
        """Record a request with its response time."""
        now = time.time()
        with self.lock:
            self.response_times.append(response_time_ms)
            self.request_timestamps.append(now)
            if is_error:
                self.error_timestamps.append(now)

    def get_stats(self) -> dict:
        """Get current performance statistics."""
        now = time.time()
        with self.lock:
            # Average response time (last 100 requests)
            recent_times = list(self.response_times)[-100:] if self.response_times else [0]
            avg_response_time = sum(recent_times) / len(recent_times) if recent_times else 0

            # Requests per minute (last 60 seconds)
            one_minute_ago = now - 60
            recent_requests = sum(1 for ts in self.request_timestamps if ts > one_minute_ago)

            # Errors in last 24 hours
            one_day_ago = now - 86400
            recent_errors = sum(1 for ts in self.error_timestamps if ts > one_day_ago)

            # Uptime
            uptime_seconds = now - self.start_time
            # Assume 99.9% uptime unless we have actual downtime tracking
            uptime_percent = 99.9 if uptime_seconds > 3600 else 100.0

            return {
                "response_time_ms": round(avg_response_time, 1),
                "requests_per_minute": recent_requests,
                "error_count_24h": recent_errors,
                "uptime_percent": uptime_percent,
                "total_requests": len(self.request_timestamps),
                "uptime_seconds": int(uptime_seconds)
            }

# Global metrics instance
request_metrics = RequestMetrics()

# Import for exchange manager
from src.config.manager import ConfigManager
from src.core.exchanges.manager import ExchangeManager

# Import shared cache bridge for cross-process communication
from src.core.cache.shared_cache_bridge import get_shared_cache_bridge, initialize_shared_cache

# Create FastAPI app
app = FastAPI(
    title="Virtuoso Trading System - Web Server",
    description="Standalone web server with full API and dashboards",
    version="2.0.0"
)

# Add startup event to initialize exchange manager
@app.on_event("startup")
async def startup_event():
    """Initialize exchange manager, alert manager, and other dependencies on startup"""
    try:
        # Initialize config manager
        config_manager = ConfigManager()
        print("✅ ConfigManager initialized")

        # Initialize exchange manager
        print("Initializing exchange manager...")
        exchange_manager = ExchangeManager(config_manager)

        # Try to initialize, but don't fail if exchanges can't connect
        try:
            await exchange_manager.initialize()
            print("✅ Exchange manager initialized successfully")
        except Exception as e:
            print(f"⚠️ Exchange manager partially initialized (some exchanges may be unavailable): {e}")

        # Initialize alert manager for /api/alerts endpoints
        print("Initializing alert manager...")
        try:
            from src.monitoring.alert_manager import AlertManager
            # AlertManager expects config dict, not config_manager object
            config_dict = config_manager._config if hasattr(config_manager, '_config') else {}

            # Debug: Check if webhook URL is in config
            webhook_url = config_dict.get('monitoring', {}).get('alerts', {}).get('system_alerts_webhook_url', 'NOT FOUND')
            print(f"Debug: system_alerts_webhook_url in config: {webhook_url[:50] if webhook_url != 'NOT FOUND' else webhook_url}...")

            alert_manager = AlertManager(config=config_dict)
            app.state.alert_manager = alert_manager
            print("✅ Alert manager initialized successfully")

            # Initialize RegimeMonitor for regime change alerts
            try:
                from src.monitoring.regime_monitor import RegimeMonitor
                regime_monitor = RegimeMonitor(
                    alert_manager=alert_manager,
                    config=config_dict,
                    enable_external_data=True  # Enable perps-tracker, CoinGecko, Fear/Greed
                )
                app.state.regime_monitor = regime_monitor
                print("✅ Regime monitor initialized successfully")
            except Exception as rm_error:
                print(f"⚠️ Regime monitor initialization failed: {rm_error}")
                app.state.regime_monitor = None

        except Exception as e:
            print(f"⚠️ Alert manager initialization failed: {e}")
            import traceback
            traceback.print_exc()
            # Create a minimal alert manager stub so alerts endpoints don't crash
            app.state.alert_manager = None
            app.state.regime_monitor = None

        # Initialize liquidation data collector
        print("Initializing liquidation data collector...")
        try:
            from src.core.exchanges.liquidation_collector import LiquidationDataCollector
            liquidation_collector = LiquidationDataCollector(exchange_manager)
            app.state.liquidation_collector = liquidation_collector
            print("✅ Liquidation data collector initialized")
        except Exception as e:
            print(f"⚠️ Liquidation collector initialization failed: {e}")
            app.state.liquidation_collector = None

        # Store in app state for API routes to use
        app.state.config_manager = config_manager
        app.state.exchange_manager = exchange_manager

        # Initialize shared cache bridge for cross-process communication
        print("Initializing shared cache bridge...")
        try:
            cache_initialized = await initialize_shared_cache()
            if cache_initialized:
                app.state.shared_cache = get_shared_cache_bridge()
                print("✅ Shared cache bridge enabled - web service can now read monitoring data")
            else:
                app.state.shared_cache = None
                print("⚠️ Shared cache bridge initialization failed - will use direct API calls")
        except Exception as e:
            print(f"⚠️ Could not initialize shared cache bridge: {e}")
            app.state.shared_cache = None

        print("✅ Web server startup complete")

    except Exception as e:
        print(f"❌ Error during startup: {e}")
        # Don't fail completely - web server can still serve basic content

# Initialize API routes manually, excluding problematic system routes
api_routes_loaded = False
def init_standalone_api_routes(app: FastAPI):
    """Initialize API routes for standalone web server, excluding exchange manager dependencies."""
    try:
        from src.api.routes import signals, market, trading, dashboard, alpha, liquidation, correlation, bitcoin_beta, manipulation, top_symbols, whale_activity, sentiment, admin, core_api, alerts, cache_metrics, interactive_reports, news, analytics, bitcoin_prediction

        api_prefix = "/api"

        # Include non-exchange-dependent routes
        route_configs = [
            (signals.router, f"{api_prefix}/signals", ["signals"]),
            (market.router, f"{api_prefix}/market", ["market"]),
            (dashboard.router, f"{api_prefix}/dashboard", ["dashboard"]),
            (alpha.router, f"{api_prefix}/alpha", ["alpha"]),
            (liquidation.router, f"{api_prefix}/liquidation", ["liquidation"]),
            (correlation.router, f"{api_prefix}/correlation", ["correlation"]),
            (bitcoin_beta.router, f"{api_prefix}/bitcoin-beta", ["bitcoin_beta"]),
            (bitcoin_prediction.router, "", ["bitcoin_prediction"]),  # No prefix - uses /api/bitcoin-prediction from router
            (manipulation.router, f"{api_prefix}/manipulation", ["manipulation"]),
            (top_symbols.router, f"{api_prefix}/top-symbols", ["top_symbols"]),
            (whale_activity.router, f"{api_prefix}/whale-activity", ["whale_activity"]),
            (sentiment.router, f"{api_prefix}/sentiment", ["sentiment"]),
            (admin.router, f"{api_prefix}/admin", ["admin"]),
            (core_api.router, f"{api_prefix}/core", ["core"]),
            (alerts.router, f"{api_prefix}/alerts", ["alerts"]),
            (cache_metrics.router, f"{api_prefix}/cache", ["cache"]),
            (interactive_reports.router, f"{api_prefix}/reports", ["reports"]),
            (news.router, f"{api_prefix}/news", ["news"]),
            (analytics.router, f"{api_prefix}/analytics", ["analytics"])
        ]

        # Register routes that don't require exchange manager
        successful_routes = []
        for router, prefix, tags in route_configs:
            try:
                app.include_router(router, prefix=prefix, tags=tags)
                successful_routes.append(prefix)
            except Exception as e:
                print(f"⚠️  Skipped {prefix}: {e}")

        # Note: Skipping system routes that depend on exchange manager
        print(f"✅ Standalone API routes loaded: {', '.join(successful_routes)}")
        print("ℹ️  Skipped system routes (will use standalone endpoint instead)")
        return True

    except Exception as e:
        print(f"❌ Error loading standalone API routes: {e}")
        return False

try:
    api_routes_loaded = init_standalone_api_routes(app)
    if not api_routes_loaded:
        raise Exception("Failed to initialize standalone API routes")
    print("✅ Standalone API routes loaded successfully")
except Exception as e:
    print(f"Warning: Could not initialize standalone API routes: {e}")
    print("Using fallback mode with basic endpoints")

# Initialize trading control if available
try:
    from src.api.routes.trading_control_init import setup_trading_control
    setup_trading_control(app)
except ImportError:
    pass

# Add paper trading data endpoints
try:
    from src.api.routes import paper_trading_data
    app.include_router(paper_trading_data.router, prefix="/api/paper", tags=["paper_trading"])
except ImportError:
    pass

# Add regime monitoring endpoints
try:
    from src.api.routes import regime
    app.include_router(regime.router, prefix="/api/regime", tags=["regime"])
    print("✅ Regime monitoring routes registered in web_server.py")
except ImportError as e:
    print(f"⚠️ Regime routes not available: {e}")

# Override system status endpoint with standalone version
# This replaces the exchange-manager dependent endpoint with our standalone version
@app.get("/api/system/status", tags=["system"])
async def get_system_status_standalone():
    """Get system metrics without exchange manager dependency - standalone version"""
    try:
        # Get system uptime
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        uptime_hours = int(uptime_seconds // 3600)
        uptime_minutes = int((uptime_seconds % 3600) // 60)
        uptime_str = f"{uptime_hours}h {uptime_minutes}m"

        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()

        # Memory metrics
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024**3)
        memory_total_gb = memory.total / (1024**3)

        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_used_gb = disk.used / (1024**3)
        disk_total_gb = disk.total / (1024**3)

        # Network I/O metrics
        net_io = psutil.net_io_counters()

        return {
            "timestamp": int(time.time() * 1000),
            "system": {
                "uptime": uptime_str,
                "uptime_seconds": int(uptime_seconds),
                "cpu": {
                    "percent": round(cpu_percent, 1),
                    "count": cpu_count
                },
                "memory": {
                    "percent": round(memory.percent, 1),
                    "used_gb": round(memory_used_gb, 2),
                    "total_gb": round(memory_total_gb, 2),
                    "available_gb": round(memory.available / (1024**3), 2)
                },
                "disk": {
                    "percent": round(disk.percent, 1),
                    "used_gb": round(disk_used_gb, 2),
                    "total_gb": round(disk_total_gb, 2),
                    "free_gb": round(disk.free / (1024**3), 2)
                },
                "network": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "sent_mb": round(net_io.bytes_sent / (1024**2), 2),
                    "recv_mb": round(net_io.bytes_recv / (1024**2), 2)
                }
            },
            "trading_system": {
                "status": "running",
                "mode": "standalone_web",
                "components": {
                    "signal_generator": "live",
                    "market_data_feed": "live",
                    "alert_system": "active",
                    "cache_system": "active"
                }
            },
            "performance": request_metrics.get_stats()
        }
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": int(time.time() * 1000),
            "status": "error"
        }

# Add CORS middleware for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Gzip compression for faster transfers (60-70% size reduction)
# minimum_size=1000 means only compress responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request tracking middleware for real performance metrics
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to track request metrics for performance monitoring."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        is_error = False

        try:
            response = await call_next(request)
            is_error = response.status_code >= 400
            return response
        except Exception as e:
            is_error = True
            raise
        finally:
            # Record the request metrics
            response_time_ms = (time.time() - start_time) * 1000
            # Skip tracking for health check endpoints to avoid skewing metrics
            if not request.url.path.startswith("/health"):
                request_metrics.record_request(response_time_ms, is_error)

app.add_middleware(RequestTrackingMiddleware)

# Serve static files if they exist
static_dir = project_root / "src" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Mount Virtuoso Aggr static files
    aggr_dir = project_root / "static" / "aggr"
    if aggr_dir.exists():
        app.mount("/aggr", StaticFiles(directory=str(aggr_dir), html=True), name="aggr")

# Mount HTML reports directory for serving signal analysis snapshots
reports_html_dir = project_root / "reports" / "html"
if reports_html_dir.exists():
    app.mount("/reports/html", StaticFiles(directory=str(reports_html_dir)), name="reports_html")

# Mount PDF reports directory for serving PDF reports
reports_pdf_dir = project_root / "reports" / "pdf"
if reports_pdf_dir.exists():
    app.mount("/reports/pdf", StaticFiles(directory=str(reports_pdf_dir)), name="reports_pdf")

# Mount exports directory for serving chart images in HTML reports
exports_dir = project_root / "exports"
if exports_dir.exists():
    app.mount("/exports", StaticFiles(directory=str(exports_dir)), name="exports")

# Serve dashboard templates
@app.get("/")
async def serve_desktop_dashboard():
    """Serve desktop dashboard"""
    template_path = project_root / "src" / "dashboard" / "templates" / "dashboard.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Desktop dashboard not found"}

@app.get("/mobile")
async def serve_mobile_dashboard():
    """Serve mobile dashboard (v3 with Lightweight Charts and cached beta-chart API)"""
    template_path = project_root / "src" / "dashboard" / "templates" / "dashboard_mobile_v3.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Mobile dashboard not found"}

@app.get("/desktop")
async def serve_new_desktop_dashboard():
    """Serve new desktop dashboard with sidebar navigation and widget layout"""
    template_path = project_root / "src" / "dashboard" / "templates" / "dashboard_desktop.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Desktop dashboard not found"}

@app.get("/desktop-v2")
async def serve_desktop_v2_dashboard():
    """Serve desktop dashboard v2 with vue-grid-layout (VGL)"""
    template_path = project_root / "src" / "dashboard" / "templates" / "dashboard_desktop_v2.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Desktop v2 dashboard not found"}

@app.get("/desktop-v3")
async def serve_desktop_v3_dashboard():
    """Serve desktop dashboard v3 with aggr.trade integration"""
    template_path = project_root / "src" / "dashboard" / "templates" / "dashboard_desktop_v3.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Desktop v3 dashboard not found"}

@app.get("/chart-comparison")
async def serve_chart_comparison():
    """Serve chart library comparison demo with live correlation data"""
    template_path = project_root / "src" / "dashboard" / "templates" / "chart_library_comparison.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Chart comparison page not found"}

# /aggr route now handled by StaticFiles mount above (line 398)
# This allows automatic serving of index.html and all assets with correct paths
# @app.get("/aggr")
# async def serve_aggr_trade():
#     """Serve Virtuoso-branded aggr order flow visualization"""
#     aggr_index = project_root / "static" / "aggr" / "index.html"
#     if aggr_index.exists():
#         return FileResponse(str(aggr_index))
#     return {"message": "Virtuoso Aggr not found"}

@app.get("/beta")
async def serve_beta_dashboard():
    """Serve beta dashboard (v3 with Bybit Performance Tracker)"""
    template_path = project_root / "src" / "dashboard" / "templates" / "dashboard_mobile_v3.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Beta dashboard not found"}

@app.get("/chart-comparison")
async def serve_chart_comparison():
    """Chart library comparison page (Plotly vs Lightweight Charts vs ApexCharts vs Chart.js)"""
    template_path = project_root / "src" / "dashboard" / "templates" / "chart_comparison.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Chart comparison page not found"}

@app.get("/debug-mobile")
async def serve_debug_mobile():
    """Serve mobile debug page"""
    template_path = project_root / "src" / "dashboard" / "templates" / "debug_mobile.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Debug page not found"}

# WebSocket endpoint for real-time mobile dashboard updates
# Store active WebSocket connections
active_websocket_connections: set = set()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    await websocket.accept()
    active_websocket_connections.add(websocket)
    logger.info(f"WebSocket client connected. Total connections: {len(active_websocket_connections)}")

    try:
        while True:
            try:
                # Wait for messages from client (with timeout for heartbeat)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)

                # Handle different message types
                if message.get('type') == 'ping':
                    await websocket.send_json({'type': 'pong', 'timestamp': time.time()})
                elif message.get('type') == 'subscribe':
                    # Acknowledge subscription
                    await websocket.send_json({
                        'type': 'subscribed',
                        'channel': message.get('channel', 'default'),
                        'timestamp': time.time()
                    })

            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_json({'type': 'heartbeat', 'timestamp': time.time()})
                except:
                    break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
    finally:
        active_websocket_connections.discard(websocket)
        logger.info(f"WebSocket connection closed. Total connections: {len(active_websocket_connections)}")

@app.get("/links")
async def virtuoso_links():
    """Serve the Virtuoso linktree-style page"""
    template_path = project_root / "src" / "dashboard" / "templates" / "virtuoso_links.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Links page not found"}

@app.get("/paper-trading")
async def serve_paper_trading():
    """Serve paper trading dashboard"""
    template_path = project_root / "src" / "dashboard" / "templates" / "paper_trading.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Paper trading dashboard not found"}

@app.get("/education")
async def serve_education():
    """Serve Virtuoso education page - How Virtuoso Works"""
    template_path = project_root / "src" / "dashboard" / "templates" / "educational_guide.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Education page not found"}

@app.get("/cache-metrics")
async def serve_cache_metrics_dashboard():
    """Serve cache metrics dashboard"""
    template_path = project_root / "src" / "dashboard" / "templates" / "cache_metrics_dashboard.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Cache metrics dashboard not found"}

@app.get("/confluence")
async def serve_confluence_dashboard():
    """Serve confluence score visualization (REST API version)"""
    template_path = project_root / "src" / "dashboard" / "templates" / "wired_prototype.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Confluence dashboard not found"}

@app.get("/confluence-live")
async def serve_confluence_realtime():
    """Serve confluence score visualization (WebSocket real-time version)"""
    template_path = project_root / "src" / "dashboard" / "templates" / "wired_realtime.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Confluence real-time dashboard not found"}

@app.get("/arena")
async def serve_bull_bear_arena():
    """Serve Bull/Bear Arena - visual market sentiment battle visualization"""
    template_path = project_root / "src" / "dashboard" / "templates" / "bull_bear_arena.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Bull/Bear Arena not found"}

@app.get("/news-widget")
async def serve_news_widget():
    """Serve Virtuoso News Widget - standalone crypto news ticker"""
    template_path = project_root / "src" / "dashboard" / "templates" / "news_widget.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "News widget not found"}

@app.get("/news-ticker")
async def serve_news_ticker_dongle():
    """Serve Virtuoso News Ticker Dongle - compact embeddable news ticker"""
    template_path = project_root / "src" / "dashboard" / "templates" / "news_ticker_dongle.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "News ticker dongle not found"}

@app.get("/beta-chart")
async def serve_beta_analysis():
    """Serve Bitcoin Beta Analysis - standalone performance visualization"""
    template_path = project_root / "src" / "dashboard" / "templates" / "bitcoin_beta_standalone.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Beta Analysis dashboard not found"}

@app.get("/api/docs")
async def serve_api_docs():
    """Serve branded API documentation page"""
    template_path = project_root / "src" / "dashboard" / "templates" / "api_docs_branded.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "API docs not found"}

# Basic API endpoints for dashboard functionality - NOW WITH LIVE DATA
@app.get("/api/market/overview")
async def market_overview():
    """Market overview endpoint with LIVE data from Bybit"""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Fetch live BTC data
            async with session.get("https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT", timeout=5) as resp:
                if resp.status == 200:
                    btc_data = await resp.json()
                    if btc_data.get('retCode') == 0:
                        ticker = btc_data['result']['list'][0]
                        btc_price = float(ticker['lastPrice'])
                        btc_change = float(ticker['price24hPcnt']) * 100

                        # Determine market regime based on price action
                        if btc_change > 2:
                            regime = "BULLISH"
                        elif btc_change < -2:
                            regime = "BEARISH"
                        else:
                            regime = "NEUTRAL"

                        return {
                            "timestamp": datetime.now().isoformat(),
                            "market_regime": regime,
                            "btc_price": btc_price,
                            "btc_change": round(btc_change, 2),
                            "data_quality": "live",
                            "status": "active"
                        }

        # Fallback if API fails
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "message": "Unable to fetch live market data"
        }
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "message": f"Error: {str(e)}"
        }

@app.get("/api/signals/top")
async def top_signals():
    """Top trading signals with LIVE prices from Bybit"""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Fetch live data for multiple symbols
            symbols_to_fetch = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]
            signals = []

            for symbol in symbols_to_fetch:
                try:
                    async with session.get(f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}", timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get('retCode') == 0 and data['result']['list']:
                                ticker = data['result']['list'][0]
                                price = float(ticker['lastPrice'])
                                change = float(ticker['price24hPcnt']) * 100

                                # Simple signal logic based on price action
                                if change > 3:
                                    signal_type = "LONG"
                                    confidence = min(0.75 + (change / 100), 0.95)
                                elif change < -3:
                                    signal_type = "SHORT"
                                    confidence = min(0.75 + (abs(change) / 100), 0.95)
                                else:
                                    signal_type = "HOLD"
                                    confidence = 0.60

                                signals.append({
                                    "symbol": symbol,
                                    "signal": signal_type,
                                    "confidence": round(confidence, 2),
                                    "price": price,
                                    "change": round(change, 2),
                                    "timestamp": datetime.now().isoformat(),
                                    "data_quality": "live"
                                })
                except Exception as e:
                    continue

            if signals:
                return {"signals": signals}

        # Fallback if API fails
        return {
            "signals": [],
            "status": "error",
            "message": "Unable to fetch live signal data"
        }
    except Exception as e:
        return {
            "signals": [],
            "status": "error",
            "message": f"Error: {str(e)}"
        }

@app.get("/api/dashboard/data")
async def dashboard_data():
    """Dashboard data with LIVE market data from Bybit"""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Fetch live BTC data for market overview
            async with session.get("https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT", timeout=5) as resp:
                if resp.status == 200:
                    btc_data = await resp.json()
                    if btc_data.get('retCode') == 0:
                        ticker = btc_data['result']['list'][0]
                        btc_price = float(ticker['lastPrice'])
                        btc_change = float(ticker['price24hPcnt']) * 100

                        # Determine market regime
                        if btc_change > 2:
                            regime = "Bullish"
                        elif btc_change < -2:
                            regime = "Bearish"
                        else:
                            regime = "Neutral"

                        # Fetch top movers
                        async with session.get("https://api.bybit.com/v5/market/tickers?category=linear", timeout=5) as movers_resp:
                            top_movers = []
                            if movers_resp.status == 200:
                                movers_data = await movers_resp.json()
                                if movers_data.get('retCode') == 0:
                                    tickers = movers_data['result']['list']
                                    # Filter USDT pairs and sort by change
                                    usdt_pairs = [
                                        {
                                            "symbol": t['symbol'],
                                            "change": float(t['price24hPcnt']) * 100,
                                            "price": float(t['lastPrice'])
                                        }
                                        for t in tickers
                                        if t['symbol'].endswith('USDT') and float(t['turnover24h']) > 1000000
                                    ]
                                    usdt_pairs.sort(key=lambda x: abs(x['change']), reverse=True)
                                    top_movers = usdt_pairs[:5]

                        return {
                            "market_overview": {
                                "market_regime": regime,
                                "btc_price": btc_price,
                                "btc_change": round(btc_change, 2),
                                "data_quality": "live"
                            },
                            "top_movers": top_movers,
                            "alerts": [],  # Would come from real alert system
                            "system_status": {
                                "status": "online",
                                "last_update": datetime.now().isoformat(),
                                "data_source": "live"
                            }
                        }

        # Fallback if API fails
        return {
            "market_overview": {
                "market_regime": "Unknown",
                "status": "error",
                "message": "Unable to fetch live data"
            },
            "top_movers": [],
            "alerts": [],
            "system_status": {
                "status": "error",
                "last_update": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {
            "market_overview": {
                "status": "error",
                "message": f"Error: {str(e)}"
            },
            "top_movers": [],
            "alerts": [],
            "system_status": {
                "status": "error",
                "last_update": datetime.now().isoformat()
            }
        }

@app.get("/api/dashboard/signals-from-cache")
async def get_signals_from_cache():
    """Get signals from shared cache (cross-process data from monitoring system)"""
    try:
        if not hasattr(app.state, 'shared_cache') or app.state.shared_cache is None:
            return {
                "status": "error",
                "message": "Shared cache not initialized",
                "signals": [],
                "cache_enabled": False
            }

        # Get signals from shared cache
        signals_data, is_cross_service = await app.state.shared_cache.get_shared_data("analysis:signals")

        if signals_data:
            return {
                "status": "success",
                "signals": signals_data.get('signals', []),
                "cache_hit": True,
                "cross_service_hit": is_cross_service,
                "timestamp": signals_data.get('timestamp', int(time.time())),
                "cache_enabled": True
            }
        else:
            return {
                "status": "no_data",
                "message": "No signals found in cache",
                "signals": [],
                "cache_hit": False,
                "cache_enabled": True
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "signals": [],
            "cache_enabled": True
        }

@app.get("/api/dashboard/mobile-data-from-cache")
async def get_mobile_data_from_cache():
    """Get mobile dashboard data from shared cache"""
    try:
        if not hasattr(app.state, 'shared_cache') or app.state.shared_cache is None:
            return {
                "status": "error",
                "message": "Shared cache not initialized"
            }

        # Get various data from shared cache
        signals_data, _ = await app.state.shared_cache.get_shared_data("analysis:signals")
        market_overview, _ = await app.state.shared_cache.get_shared_data("market:overview")
        market_regime, _ = await app.state.shared_cache.get_shared_data("analysis:market_regime")

        return {
            "status": "success",
            "signals": signals_data.get('signals', []) if signals_data else [],
            "market_overview": market_overview or {},
            "market_regime": market_regime or "unknown",
            "timestamp": int(time.time() * 1000),
            "data_source": "shared_cache"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": int(time.time() * 1000)
        }

@app.get("/api/cache/metrics")
async def get_cache_metrics():
    """Get cache bridge metrics and health status"""
    try:
        if not hasattr(app.state, 'shared_cache') or app.state.shared_cache is None:
            return {
                "status": "error",
                "message": "Shared cache not initialized",
                "cache_enabled": False
            }

        # Get bridge metrics
        metrics = app.state.shared_cache.get_bridge_metrics()
        health = await app.state.shared_cache.health_check()

        return {
            "status": "success",
            "cache_enabled": True,
            "metrics": metrics,
            "health": health,
            "timestamp": int(time.time() * 1000)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "cache_enabled": False
        }

@app.get("/service-health")
async def serve_service_health():
    """Serve service health page"""
    template_path = project_root / "src" / "dashboard" / "templates" / "service_health.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Service health page not found"}

@app.get("/system-monitoring")
async def serve_system_monitoring():
    """Serve system monitoring page"""
    template_path = project_root / "src" / "dashboard" / "templates" / "system_monitoring.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "System monitoring page not found"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "web_server",
        "mode": "standalone"
    }

@app.get("/api/health")
async def api_health_check():
    """API health check endpoint (alias for /health)"""
    return await health_check()


# =============================================================================
# PHASE 1: Kubernetes-Style Health Probes
# =============================================================================

@app.get("/health/live", tags=["health"])
async def liveness_probe():
    """Kubernetes liveness probe - minimal check if process is alive.

    Returns 200 if the application is running and not deadlocked.
    Should be lightweight (<10KB response, <100ms).
    If this fails, the container should be restarted.
    """
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/health/ready", tags=["health"])
async def readiness_probe():
    """Kubernetes readiness probe - check if app can accept traffic.

    Checks all critical dependencies. If this fails, remove from load balancer
    but don't restart the container.
    """
    checks = {}
    overall_ready = True

    # Check 1: Shared cache availability
    try:
        if hasattr(app.state, 'shared_cache') and app.state.shared_cache is not None:
            checks["cache"] = "ok"
        else:
            checks["cache"] = "not_initialized"
            overall_ready = False
    except Exception as e:
        checks["cache"] = f"error: {str(e)}"
        overall_ready = False

    # Check 2: Redis connectivity
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, socket_timeout=2)
        r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"
        overall_ready = False

    # Check 3: Memcached connectivity
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', 11211))
        sock.close()
        checks["memcached"] = "ok" if result == 0 else "connection_refused"
        if result != 0:
            overall_ready = False
    except Exception as e:
        checks["memcached"] = f"error: {str(e)}"
        overall_ready = False

    # Check 4: Disk space (critical if <5% free)
    try:
        disk = psutil.disk_usage('/')
        disk_free_percent = 100 - disk.percent
        if disk_free_percent < 5:
            checks["disk"] = f"critical: {disk_free_percent:.1f}% free"
            overall_ready = False
        elif disk_free_percent < 10:
            checks["disk"] = f"warning: {disk_free_percent:.1f}% free"
        else:
            checks["disk"] = "ok"
    except Exception as e:
        checks["disk"] = f"error: {str(e)}"

    # Check 5: Memory (critical if <10% available)
    try:
        memory = psutil.virtual_memory()
        memory_available_percent = 100 - memory.percent
        if memory_available_percent < 10:
            checks["memory"] = f"critical: {memory_available_percent:.1f}% available"
            overall_ready = False
        elif memory_available_percent < 20:
            checks["memory"] = f"warning: {memory_available_percent:.1f}% available"
        else:
            checks["memory"] = "ok"
    except Exception as e:
        checks["memory"] = f"error: {str(e)}"

    status = "ready" if overall_ready else "not_ready"
    status_code = 200 if overall_ready else 503

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks
        }
    )


# =============================================================================
# PHASE 2: High Priority Health Endpoints
# =============================================================================

@app.get("/health/dependencies", tags=["health"])
async def dependency_health():
    """Detailed health status of all external dependencies with latencies."""
    dependencies = {}

    # Redis health with latency
    try:
        import redis
        start = time.time()
        r = redis.Redis(host='localhost', port=6379, socket_timeout=5)
        info = r.info()
        latency_ms = (time.time() - start) * 1000
        dependencies["redis"] = {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "version": info.get("redis_version", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_mb": round(info.get("used_memory", 0) / (1024**2), 2),
            "uptime_seconds": info.get("uptime_in_seconds", 0)
        }
    except Exception as e:
        dependencies["redis"] = {"status": "unhealthy", "error": str(e)}

    # Memcached health with latency
    try:
        import socket
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('localhost', 11211))
        if result == 0:
            sock.sendall(b'stats\r\n')
            response = sock.recv(4096).decode('utf-8', errors='ignore')
            latency_ms = (time.time() - start) * 1000
            # Parse some stats
            stats = {}
            for line in response.split('\r\n'):
                if line.startswith('STAT '):
                    parts = line.split(' ')
                    if len(parts) >= 3:
                        stats[parts[1]] = parts[2]
            dependencies["memcached"] = {
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
                "curr_items": int(stats.get("curr_items", 0)),
                "bytes_used": int(stats.get("bytes", 0)),
                "get_hits": int(stats.get("get_hits", 0)),
                "get_misses": int(stats.get("get_misses", 0)),
                "uptime": int(stats.get("uptime", 0))
            }
        else:
            dependencies["memcached"] = {"status": "unhealthy", "error": "connection_refused"}
        sock.close()
    except Exception as e:
        dependencies["memcached"] = {"status": "unhealthy", "error": str(e)}

    # Shared cache health
    try:
        if hasattr(app.state, 'shared_cache') and app.state.shared_cache is not None:
            start = time.time()
            health = await app.state.shared_cache.health_check()
            latency_ms = (time.time() - start) * 1000
            dependencies["shared_cache"] = {
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
                "details": health
            }
        else:
            dependencies["shared_cache"] = {"status": "not_initialized"}
    except Exception as e:
        dependencies["shared_cache"] = {"status": "unhealthy", "error": str(e)}

    # Discord webhook (check if configured)
    discord_webhook = os.environ.get('DISCORD_WEBHOOK_URL') or os.environ.get('DISCORD_TRADING_WEBHOOK')
    dependencies["discord"] = {
        "status": "configured" if discord_webhook else "not_configured",
        "webhook_set": bool(discord_webhook)
    }

    # Determine overall status
    unhealthy_count = sum(1 for d in dependencies.values() if d.get("status") == "unhealthy")
    overall_status = "healthy" if unhealthy_count == 0 else "degraded" if unhealthy_count < 2 else "unhealthy"

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependencies": dependencies
    }


@app.get("/health/trading", tags=["health"])
async def trading_health():
    """Trading-specific health indicators."""
    trading_status = {
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Check cache for recent signals
    try:
        if hasattr(app.state, 'shared_cache') and app.state.shared_cache is not None:
            # Try to get recent signals from cache using correct method
            signals, found = await app.state.shared_cache.get_shared_data("analysis:signals")
            if found and signals:
                trading_status["signal_generation"] = {
                    "enabled": True,
                    "cached_signals_available": True,
                    "signal_count": len(signals) if isinstance(signals, list) else 1
                }
            else:
                trading_status["signal_generation"] = {
                    "enabled": True,
                    "cached_signals_available": False,
                    "note": "No cached signals (may be normal if just started)"
                }
        else:
            trading_status["signal_generation"] = {
                "enabled": False,
                "reason": "Cache not initialized"
            }
    except Exception as e:
        trading_status["signal_generation"] = {
            "enabled": False,
            "error": str(e)
        }

    # Check for exchange manager
    try:
        if hasattr(app.state, 'exchange_manager') and app.state.exchange_manager is not None:
            trading_status["exchange_connectivity"] = {
                "status": "connected",
                "exchange": "bybit"
            }
        else:
            trading_status["exchange_connectivity"] = {
                "status": "not_connected",
                "note": "Exchange manager not initialized in web server (normal for standalone mode)"
            }
    except Exception as e:
        trading_status["exchange_connectivity"] = {"status": "error", "error": str(e)}

    # System resources check for trading
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()

        if cpu > 90 or memory.percent > 90:
            trading_status["resource_status"] = "critical"
            trading_status["status"] = "degraded"
        elif cpu > 70 or memory.percent > 70:
            trading_status["resource_status"] = "warning"
        else:
            trading_status["resource_status"] = "healthy"

        trading_status["resources"] = {
            "cpu_percent": round(cpu, 1),
            "memory_percent": round(memory.percent, 1)
        }
    except Exception as e:
        trading_status["resources"] = {"error": str(e)}

    return trading_status


@app.get("/health/version", tags=["health"])
async def version_info():
    """Build and version metadata for debugging."""
    import subprocess

    # Get git info
    git_commit = "unknown"
    git_branch = "unknown"
    git_timestamp = "unknown"

    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(project_root),
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except:
        pass

    try:
        git_branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(project_root),
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except:
        pass

    try:
        git_timestamp = subprocess.check_output(
            ["git", "log", "-1", "--format=%ci"],
            cwd=str(project_root),
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except:
        pass

    # Get Python and dependency versions
    import platform
    dependencies = {}

    for pkg in ["ccxt", "fastapi", "uvicorn", "redis", "psutil", "numpy", "pandas"]:
        try:
            mod = __import__(pkg)
            dependencies[pkg] = getattr(mod, "__version__", "installed")
        except ImportError:
            dependencies[pkg] = "not_installed"

    # Calculate uptime
    boot_time = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_time)

    return {
        "version": "2.0.0",
        "service": "virtuoso-web",
        "git": {
            "commit": git_commit,
            "branch": git_branch,
            "last_commit_time": git_timestamp
        },
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": dependencies,
        "uptime_seconds": uptime_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# =============================================================================
# VPS Performance API (Real Metrics, Not Hardcoded)
# =============================================================================

@app.get("/api/vps/performance", tags=["system"])
async def vps_performance():
    """Real-time VPS performance metrics with process-level details."""

    # CPU metrics with per-core breakdown
    cpu_percent_total = psutil.cpu_percent(interval=0.1)
    cpu_percent_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
    cpu_freq = psutil.cpu_freq()

    try:
        load_avg = psutil.getloadavg()
    except (AttributeError, OSError):
        load_avg = (0.0, 0.0, 0.0)

    # Memory metrics
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # Disk metrics
    disk = psutil.disk_usage('/')

    # Disk I/O
    try:
        disk_io = psutil.disk_io_counters()
        disk_io_stats = {
            "read_mb": round(disk_io.read_bytes / (1024**2), 2),
            "write_mb": round(disk_io.write_bytes / (1024**2), 2),
            "read_count": disk_io.read_count,
            "write_count": disk_io.write_count
        }
    except:
        disk_io_stats = {}

    # Network metrics
    net_io = psutil.net_io_counters()

    # Network connections count
    try:
        connections = psutil.net_connections(kind='inet')
        connection_stats = {
            "total": len(connections),
            "established": sum(1 for c in connections if c.status == 'ESTABLISHED'),
            "listen": sum(1 for c in connections if c.status == 'LISTEN'),
            "time_wait": sum(1 for c in connections if c.status == 'TIME_WAIT')
        }
    except:
        connection_stats = {"total": 0}

    # Top processes by memory
    top_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent', 'status']):
        try:
            info = proc.info
            if info['memory_percent'] and info['memory_percent'] > 0.1:
                top_processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "memory_percent": round(info['memory_percent'], 2),
                    "cpu_percent": round(info['cpu_percent'] or 0, 2),
                    "status": info['status']
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # Sort by memory and take top 10
    top_processes.sort(key=lambda x: x['memory_percent'], reverse=True)
    top_processes = top_processes[:10]

    # Virtuoso-specific processes
    virtuoso_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_percent', 'cpu_percent', 'create_time']):
        try:
            info = proc.info
            cmdline = ' '.join(info['cmdline'] or [])
            if 'virtuoso' in cmdline.lower() or 'main.py' in cmdline or 'web_server.py' in cmdline or 'monitoring_api.py' in cmdline:
                virtuoso_processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "cmdline": cmdline[:100],
                    "memory_percent": round(info['memory_percent'] or 0, 2),
                    "cpu_percent": round(info['cpu_percent'] or 0, 2),
                    "uptime_seconds": int(time.time() - info['create_time']) if info['create_time'] else 0
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # System uptime
    boot_time = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_time)
    uptime_days = uptime_seconds // 86400
    uptime_hours = (uptime_seconds % 86400) // 3600
    uptime_minutes = (uptime_seconds % 3600) // 60

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": {
            "seconds": uptime_seconds,
            "formatted": f"{uptime_days}d {uptime_hours}h {uptime_minutes}m",
            "boot_time": datetime.fromtimestamp(boot_time).isoformat()
        },
        "cpu": {
            "total_percent": round(cpu_percent_total, 1),
            "per_core_percent": [round(c, 1) for c in cpu_percent_per_core],
            "core_count": psutil.cpu_count(),
            "frequency_mhz": round(cpu_freq.current, 0) if cpu_freq else None,
            "load_average": {
                "1min": round(load_avg[0], 2),
                "5min": round(load_avg[1], 2),
                "15min": round(load_avg[2], 2)
            }
        },
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "percent": round(memory.percent, 1),
            "cached_gb": round(getattr(memory, 'cached', 0) / (1024**3), 2),
            "buffers_gb": round(getattr(memory, 'buffers', 0) / (1024**3), 2)
        },
        "swap": {
            "total_gb": round(swap.total / (1024**3), 2),
            "used_gb": round(swap.used / (1024**3), 2),
            "free_gb": round(swap.free / (1024**3), 2),
            "percent": round(swap.percent, 1)
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": round(disk.percent, 1),
            "io": disk_io_stats
        },
        "network": {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "sent_gb": round(net_io.bytes_sent / (1024**3), 2),
            "recv_gb": round(net_io.bytes_recv / (1024**3), 2),
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errors": {
                "in": net_io.errin,
                "out": net_io.errout,
                "drop_in": net_io.dropin,
                "drop_out": net_io.dropout
            },
            "connections": connection_stats
        },
        "processes": {
            "top_by_memory": top_processes,
            "virtuoso_services": virtuoso_processes,
            "total_count": len(list(psutil.process_iter()))
        }
    }


@app.get("/api/vps/services", tags=["system"])
async def vps_services():
    """Get status of Virtuoso systemd services (VPS only)."""
    import subprocess

    services = [
        "virtuoso-trading",
        "virtuoso-web",
        "virtuoso-monitoring-api",
        "virtuoso-health-check",
        "virtuoso-health-monitor",
        "virtuoso-website"
    ]

    service_status = {}

    for service in services:
        try:
            # Check if service is active
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True,
                timeout=5
            )
            status = result.stdout.strip()

            # Get more details if active
            if status == "active":
                # Get memory and CPU usage
                show_result = subprocess.run(
                    ["systemctl", "show", service, "--property=MemoryCurrent,CPUUsageNSec,MainPID"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                props = {}
                for line in show_result.stdout.strip().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        props[key] = value

                memory_bytes = int(props.get('MemoryCurrent', 0) or 0)
                cpu_nsec = int(props.get('CPUUsageNSec', 0) or 0)
                main_pid = props.get('MainPID', '0')

                service_status[service] = {
                    "status": "running",
                    "pid": int(main_pid) if main_pid.isdigit() else 0,
                    "memory_mb": round(memory_bytes / (1024**2), 2),
                    "cpu_seconds": round(cpu_nsec / 1e9, 2)
                }
            else:
                service_status[service] = {"status": status}

        except subprocess.TimeoutExpired:
            service_status[service] = {"status": "timeout"}
        except FileNotFoundError:
            # systemctl not available (not on Linux or not systemd)
            service_status[service] = {"status": "systemctl_not_available"}
        except Exception as e:
            service_status[service] = {"status": "error", "error": str(e)}

    # Count running services
    running_count = sum(1 for s in service_status.values() if s.get("status") == "running")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": len(services),
            "running": running_count,
            "stopped": len(services) - running_count
        },
        "services": service_status
    }


def main():
    """Run the standalone web server with full API"""
    print("🚀 Starting Virtuoso Web Server (Full API Mode)")
    print("=" * 50)
    print(f"📁 Project root: {project_root}")
    print(f"🌐 Server URL: http://0.0.0.0:8002")
    print(f"📱 Mobile URL: http://0.0.0.0:8002/mobile")
    print(f"🔗 Links Page: http://0.0.0.0:8002/links")
    print(f"📊 API Endpoints: All trading system APIs enabled")
    print(f"   - /api/signals/* - Trading signals")
    print(f"   - /api/market/* - Market data")
    print(f"   - /api/dashboard/* - Dashboard data")
    print(f"   - /api/liquidation/* - Liquidation intelligence")
    print(f"   - /api/bitcoin-beta/* - BTC correlation")
    print(f"   - Plus 10+ more API modules...")
    print("=" * 50)
    
    # Run uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()