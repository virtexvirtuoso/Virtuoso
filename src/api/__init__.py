"""API initialization and route registration module."""

from fastapi import FastAPI
from .routes import signals, market, system, trading

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
    
    # Log registered routes
    import logging
    logger = logging.getLogger(__name__)
    logger.info("API routes initialized")
