#!/usr/bin/env python3
"""
Simple test server for the correlation API endpoints.
Run this to test the correlation API independently.
"""

from fastapi import FastAPI
from src.api.routes.correlation import router
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Correlation API Test Server", version="1.0.0")

# Include correlation routes
app.include_router(router, prefix="/api/correlation", tags=["correlation"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Correlation API Test Server",
        "endpoints": {
            "matrix": "/api/correlation/matrix",
            "signal_correlations": "/api/correlation/signal-correlations",
            "asset_correlations": "/api/correlation/asset-correlations", 
            "heatmap_data": "/api/correlation/heatmap-data",
            "live_matrix": "/api/correlation/live-matrix"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "correlation-api"}

if __name__ == "__main__":
    logger.info("🚀 Starting Correlation API Test Server")
    logger.info("📊 Available at: http://localhost:8001")
    logger.info("📖 Docs at: http://localhost:8001/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    ) 