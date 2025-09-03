"""
Virtuoso CCXT API Package

This package provides the REST API layer for the Virtuoso CCXT trading system,
implementing FastAPI-based endpoints for market data, signal generation, trading
operations, and dashboard interfaces.

API Architecture:
    - FastAPI framework with automatic OpenAPI documentation
    - Modular route organization by functional area
    - Multi-tier caching with performance optimization
    - Rate limiting and request throttling
    - CORS support for web dashboard integration

Main API Endpoints:
    Market Data:
        /api/market/* - Real-time market data and analysis
        /api/signals/* - Trading signals and confluence scores
        /api/bitcoin-beta/* - Bitcoin correlation analysis
        /api/liquidation/* - Liquidation intelligence data
        
    Trading Operations:
        /api/trading/* - Trade execution and management
        /api/alpha/* - Alpha opportunity scanning
        /api/whale-activity/* - Large order detection
        
    System Monitoring:
        /api/system/* - System health and performance
        /api/cache/* - Cache status and monitoring
        /api/health/* - Service health checks
        
    Dashboard Interfaces:
        /api/dashboard/* - Standard dashboard data
        /api/dashboard-cached/* - Cached dashboard (optimized)
        /api/fast/* - Ultra-fast dashboard (<50ms)
        /api/direct/* - Direct cache bypass routes

Performance Features:
    - Multi-tier caching architecture
    - Response time optimization (<50ms for cached routes)
    - Automatic cache invalidation and refresh
    - Connection pooling and rate limiting
    - Background task processing

Route Registration:
    The init_api_routes() function dynamically registers all available
    route modules with conditional loading for optional features.
    
Cache Optimization Levels:
    1. Standard routes - No caching
    2. Cached routes - 30-60s TTL
    3. Fast routes - <50ms response time
    4. Direct routes - Bypass adapter layer

Author: Virtuoso CCXT Development Team
Version: 2.5.0
"""

from fastapi import FastAPI
from .routes import signals, market, system, trading, dashboard, alpha, liquidation, correlation, bitcoin_beta, manipulation, top_symbols, whale_activity, sentiment, admin, debug_test, core_api, alerts
from .routes import dashboard_optimized


# Priority 2 Gateway Implementation
try:
    from .routes import gateway_routes
    gateway_available = True
except ImportError:
    gateway_available = False
# Cache dashboard routes archived
# try:
#     from .routes import cache_dashboard
#     cache_dashboard_available = True
# except ImportError:
cache_dashboard_available = False

try:
    from .routes import dashboard_cached
    dashboard_cached_available = True
except ImportError:
    dashboard_cached_available = False

try:
    from .routes import dashboard_fast
    dashboard_fast_available = True
except ImportError:
    dashboard_fast_available = False

# Direct cache routes archived
# try:
#     from .routes import direct_cache
#     direct_cache_available = True
# except ImportError:
direct_cache_available = False

def init_api_routes(app: FastAPI):
    """Initialize all API routes for the application."""
    # Create API prefix
    api_prefix = "/api"
    
    # Include signal routes
    app.include_router(
        signals.router,
        prefix=f"{api_prefix}/signals",
        tags=["signals"]
    )
    
    # Include market routes
    app.include_router(
        market.router,
        prefix=f"{api_prefix}/market",
        tags=["market"]
    )
    
    # Include system routes
    app.include_router(
        system.router,
        prefix=f"{api_prefix}/system",
        tags=["system"]
    )
    
    # Include monitoring alias routes for compatibility
    app.include_router(
        system.router,
        prefix=f"{api_prefix}/monitoring",
        tags=["monitoring"]
    )
    
    # Include config alias routes for compatibility
    app.include_router(
        system.router,
        prefix=f"{api_prefix}/config",
        tags=["config"]
    )
    
    # Include trading routes
    app.include_router(
        trading.router,
        prefix=f"{api_prefix}/trading",
        tags=["trading"]
    )
    
    # Include dashboard routes
    app.include_router(
        dashboard.router,
        prefix=f"{api_prefix}/dashboard",
        tags=["dashboard"]
    )
    
    # Include alpha scanner routes
    app.include_router(
        alpha.router,
        prefix=f"{api_prefix}/alpha",
        tags=["alpha"]
    )
    
    # Include liquidation intelligence routes
    app.include_router(
        liquidation.router,
        prefix=f"{api_prefix}/liquidation",
        tags=["liquidation"]
    )
    
    # Include correlation analysis routes
    app.include_router(
        correlation.router,
        prefix=f"{api_prefix}/correlation",
        tags=["correlation"]
    )
    
    # Include Bitcoin Beta routes
    app.include_router(
        bitcoin_beta.router,
        prefix=f"{api_prefix}/bitcoin-beta",
        tags=["bitcoin-beta"]
    )
    
    # Include market manipulation routes
    app.include_router(
        manipulation.router,
        prefix=f"{api_prefix}/manipulation",
        tags=["manipulation"]
    )
    
    # Include top symbols routes
    app.include_router(
        top_symbols.router,
        prefix=f"{api_prefix}/top-symbols",
        tags=["top-symbols"]
    )
    
    # Include whale activity routes
    app.include_router(
        whale_activity.router,
        prefix=f"{api_prefix}/whale-activity",
        tags=["whale-activity"]
    )
    
    # Include sentiment analysis routes
    app.include_router(
        sentiment.router,
        prefix=f"{api_prefix}/sentiment",
        tags=["sentiment"]
    )
    
    # Include alerts routes
    app.include_router(
        alerts.router,
        prefix=f"{api_prefix}/alerts",
        tags=["alerts"]
    )
    
    # Include admin dashboard routes at /admin
    app.include_router(
        admin.router,
        prefix="/admin",
        tags=["admin"]
    )
    
    # Cache monitoring routes archived
    # app.include_router(
    #     cache.router,
    #     prefix=f"{api_prefix}",
    #     tags=["cache"]
    # )
    
    # Include debug routes
    app.include_router(
        debug_test.router,
        prefix=f"{api_prefix}/debug",
        tags=["debug"]
    )
    
    # Include core API routes (standard endpoints)
    app.include_router(
        core_api.router,
        prefix=f"{api_prefix}",
        tags=["core"]
    )
    
    # Include Phase 2 cache dashboard routes if available
    if cache_dashboard_available:
        app.include_router(
            cache_dashboard.router,
            prefix=f"{api_prefix}/cache",
            tags=["cache-dashboard"]
        )
    
    # Include cached dashboard routes for existing dashboards
    if dashboard_cached_available:
        app.include_router(
            dashboard_cached.router,
            prefix=f"{api_prefix}/dashboard-cached",
            tags=["dashboard-cached"]
        )
        import logging
        cache_logger = logging.getLogger(__name__)
        cache_logger.info("✅ Cached dashboard routes enabled for ultra-fast response")
    
    # Include Phase 3 ultra-fast dashboard routes
    if dashboard_fast_available:
        app.include_router(
            dashboard_fast.router,
            prefix=f"{api_prefix}/fast",
            tags=["fast-dashboard"]
        )
        import logging
        fast_logger = logging.getLogger(__name__)
        fast_logger.info("🚀 Phase 3 ultra-fast routes enabled (<50ms response)")
    
    # Include direct cache routes (bypass adapter issues)
    if direct_cache_available:
        app.include_router(
            direct_cache.router,
            prefix=f"{api_prefix}/direct",
            tags=["direct-cache"]
        )
        import logging
        direct_logger = logging.getLogger(__name__)
        direct_logger.info("✅ Direct cache routes enabled (adapter bypass)")
    
    # Health and resilience monitoring
    try:
        from .routes import health
        app.include_router(health.router, prefix="/api/health", tags=["health"])
    except ImportError:
        pass
    
    # Include Priority 2 Gateway Routes
    if gateway_available:
        app.include_router(
            gateway_routes.router,
            prefix="",
            tags=["gateway"]
        )
    
    # Include Phase 3 WebSocket Mobile Routes
    try:
        from .routes import websocket_mobile
        app.include_router(
            websocket_mobile.router,
            prefix="",
            tags=["phase3-websocket"]
        )
        import logging
        phase3_logger = logging.getLogger(__name__)
        phase3_logger.info("✅ Phase 3 WebSocket mobile routes enabled")
    except ImportError as e:
        import logging
        phase3_logger = logging.getLogger(__name__)
        phase3_logger.debug(f"Phase 3 WebSocket mobile routes not available: {e}")
        
    import logging
    gateway_logger = logging.getLogger(__name__)
    gateway_logger.info("🚀 Priority 2 API Gateway enabled with multi-tier cache and rate limiting")
    
    # Log registered routes
    import logging
    logger = logging.getLogger(__name__)
    logger.info("API routes initialized with cache monitoring")
