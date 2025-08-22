"""API initialization and route registration module."""

from fastapi import FastAPI
from .routes import signals, market, system, trading, dashboard, alpha, liquidation, correlation, bitcoin_beta, manipulation, top_symbols, whale_activity, sentiment, admin, cache, debug_test, core_api
try:
    from .routes import cache_dashboard
    cache_dashboard_available = True
except ImportError:
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

try:
    from .routes import direct_cache
    direct_cache_available = True
except ImportError:
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
    
    # Include admin dashboard routes at /admin
    app.include_router(
        admin.router,
        prefix="/admin",
        tags=["admin"]
    )
    
    # Include cache monitoring routes
    app.include_router(
        cache.router,
        prefix=f"{api_prefix}",
        tags=["cache"]
    )
    
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
    
    # Log registered routes
    import logging
    logger = logging.getLogger(__name__)
    logger.info("API routes initialized with cache monitoring")
