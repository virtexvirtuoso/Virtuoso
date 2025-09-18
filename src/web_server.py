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

# Set environment to avoid conflicts
os.environ['WEB_SERVER_ONLY'] = 'true'
os.environ['DISABLE_INTEGRATED_WEB_SERVER'] = 'false'

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Import full API initialization
from src.api import init_api_routes

# Create FastAPI app
app = FastAPI(
    title="Virtuoso Trading System - Web Server",
    description="Standalone web server with full API and dashboards",
    version="2.0.0"
)

# Initialize ALL API routes (includes dashboard and all trading APIs)
init_api_routes(app)

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

# Add CORS middleware for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files if they exist
static_dir = project_root / "src" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

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
    """Serve mobile dashboard"""
    template_path = project_root / "src" / "dashboard" / "templates" / "dashboard_mobile_v1.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Mobile dashboard not found"}

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
    """Serve Virtuoso education page"""
    template_path = project_root / "src" / "dashboard" / "templates" / "virtuoso_education.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    # Fallback to education_financial_independence.html
    alt_path = project_root / "src" / "dashboard" / "templates" / "education_financial_independence.html"
    if alt_path.exists():
        return FileResponse(str(alt_path))

@app.get("/cache-metrics")
async def serve_cache_metrics_dashboard():
    """Serve cache metrics dashboard"""
    template_path = project_root / "src" / "dashboard" / "templates" / "cache_metrics_dashboard.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "Cache metrics dashboard not found"}

@app.get("/api/docs")
async def serve_api_docs():
    """Serve API documentation page"""
    template_path = project_root / "src" / "dashboard" / "templates" / "api_docs.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return {"message": "API docs not found"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "web_server",
        "mode": "standalone"
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