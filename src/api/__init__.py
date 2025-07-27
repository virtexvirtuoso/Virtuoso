"""API initialization and route registration module."""

from fastapi import FastAPI
from .routes import signals, market, system, trading, dashboard, alpha, liquidation, correlation, bitcoin_beta, manipulation, top_symbols, whale_activity, sentiment, admin

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
    
    # Log registered routes
    import logging
    logger = logging.getLogger(__name__)
    logger.info("API routes initialized")
