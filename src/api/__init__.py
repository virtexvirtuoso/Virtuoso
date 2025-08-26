"""API initialization and route registration module."""

from fastapi import FastAPI
# Phase 4 API Consolidation: Consolidated imports
from .routes import signals, market, system, trading, dashboard, alpha, liquidation, manipulation, top_symbols, core_api
# Phase 4 removed: admin, debug_test (now in system.py)
# Phase 3 removed: cache (now in dashboard.py)
# Phase 2 removed: whale_activity (now in signals.py)
# Removed: correlation, bitcoin_beta, sentiment (now in market.py)
# Phase 3 Consolidation: All dashboard cache variants now in dashboard.py
# Endpoints available at:
# /api/dashboard/cache/* (cache management)
# /api/dashboard/cached/* (cached dashboard routes)
# /api/dashboard/fast/* (ultra-fast routes)
# /api/dashboard/direct/* (direct cache access)

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
    
    # Phase 1 Consolidation: Correlation and Bitcoin Beta now in market.py
    # Endpoints available at:
    # /api/market/correlation/* (correlation analysis)
    # /api/market/bitcoin-beta/* (bitcoin beta analysis)
    
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
    
    # Phase 2 Consolidation: Whale activity now in signals.py
    # Endpoints available at:
    # /api/signals/whale/* (whale activity endpoints)
    
    # Phase 1 Consolidation: Sentiment analysis now in market.py
    # Endpoints available at:
    # /api/market/sentiment/* (sentiment analysis)
    
    # Phase 4 Consolidation: Admin and debug routes now in system.py
    # Endpoints available at:
    # /api/system/admin/* (admin authentication & config management)
    # /api/system/debug/* (cache testing & diagnostics)
    
    # Include core API routes (standard endpoints)
    app.include_router(
        core_api.router,
        prefix=f"{api_prefix}",
        tags=["core"]
    )
    
    # Phase 3 Consolidation: All cache dashboard variants now in dashboard.py
    # Unified endpoints:
    # • /api/dashboard/cache/* (cache management & monitoring)
    # • /api/dashboard/cached/* (cached dashboard routes) 
    # • /api/dashboard/fast/* (ultra-fast <50ms routes)
    # • /api/dashboard/direct/* (direct cache access, bypass adapters)
    
    # Health and resilience monitoring
    try:
        from .routes import health
        app.include_router(health.router, prefix="/api/health", tags=["health"])
    except ImportError:
        pass
    
    # Log registered routes
    import logging
    logger = logging.getLogger(__name__)
    logger.info("🚀 Phase 1-4 API Consolidation Complete")
    logger.info("✅ Phase 1: correlation, bitcoin-beta, sentiment -> market.py")
    logger.info("✅ Phase 2: alerts, whale_activity -> signals.py")
    logger.info("✅ Phase 3: cache variants, dashboard_cached, dashboard_fast -> dashboard.py")
    logger.info("✅ Phase 4: admin, debug_test -> system.py")
    logger.info("📍 Market: /api/market/{correlation,bitcoin-beta,sentiment}/*")
    logger.info("📍 Signals: /api/signals/{alerts,whale}/*")
    logger.info("📍 Dashboard: /api/dashboard/{cache,cached,fast,direct}/*")
    logger.info("📍 System: /api/system/{admin,debug}/*")
