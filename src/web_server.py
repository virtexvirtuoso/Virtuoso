"""Standalone web server for the Virtuoso Trading Dashboard."""

import os
import re
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import asyncio
import time
from datetime import datetime
from typing import Dict, Any

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
env_path = Path(__file__).parent.parent / "config" / "env" / ".env"
load_dotenv(dotenv_path=env_path)

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Resolve paths relative to the project root  
PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "src" / "dashboard" / "templates"

# Import dashboard integration service
from src.dashboard.dashboard_integration import DashboardIntegrationService, get_dashboard_integration

# Import API routes
from src.dashboard.dashboard_proxy import get_dashboard_integration
from src.api import init_api_routes

# Create FastAPI app
app = FastAPI(
    title="Virtuoso Trading Dashboard",
    description="Real-time trading intelligence dashboard",
    version="1.0.0"
)

# Initialize API routes
init_api_routes(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="src/static"), name="static")

@app.get("/")
async def root():
    """Root endpoint - redirect to dashboard"""
    return {"message": "Virtuoso Trading System", "dashboard": "/dashboard", "health": "/health"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Virtuoso Trading Dashboard"
    }

@app.get("/version")
async def version():
    """Get application version"""
    return {"version": "1.0.0", "service": "Virtuoso Trading Dashboard", "dashboard_fix": "2025-07-26-15:50"}

@app.get("/test-dashboard-path")
async def test_dashboard_path():
    """Test dashboard path resolution"""
    file_path = TEMPLATE_DIR / "dashboard_desktop_v1.html"
    return {
        "template_dir": str(TEMPLATE_DIR),
        "file_path": str(file_path),
        "file_exists": file_path.exists(),
        "project_root": str(PROJECT_ROOT)
    }

@app.get("/ui")
async def frontend():
    """Serve the frontend UI"""
    return FileResponse("src/static/index.html")

@app.get("/dashboard")
async def dashboard_ui():
    """Serve the dashboard selector page"""
    # Add debug logging
    file_path = TEMPLATE_DIR / "dashboard_selector.html"
    logger.info(f"Dashboard route: serving {file_path}")
    return FileResponse(file_path)

@app.get("/resilience-monitor")
async def resilience_monitor():
    """Serve the resilience monitoring dashboard"""
    file_path = TEMPLATE_DIR / "resilience_monitor.html"
    if file_path.exists():
        return FileResponse(file_path)
    else:
        # Try alternative path
        alt_path = TEMPLATE_DIR_ALT / "resilience_monitor.html"
        if alt_path.exists():
            return FileResponse(alt_path)
        else:
            raise HTTPException(status_code=404, detail="Resilience monitor not found")

@app.get("/dashboard/v1")
async def dashboard_v1_ui():
    """Serve the original dashboard"""
    return FileResponse(TEMPLATE_DIR / "dashboard.html")

@app.get("/dashboard/mobile")
async def dashboard_mobile_ui():
    """Serve the mobile dashboard"""
    return FileResponse(TEMPLATE_DIR / "dashboard_mobile_v1.html")

@app.get("/dashboard/desktop")
async def dashboard_desktop_ui():
    """Serve the desktop dashboard"""
    return FileResponse(TEMPLATE_DIR / "dashboard_desktop_v1.html")

@app.get("/dashboard/v10")
async def dashboard_v10_ui():
    """Serve the v10 Signal Confluence Matrix dashboard"""
    return FileResponse(TEMPLATE_DIR / "dashboard_v10.html")

@app.get("/dashboard/phase1")
async def dashboard_phase1_ui():
    """Serve the Phase 1 Direct Pipeline dashboard"""
    return FileResponse(TEMPLATE_DIR / "dashboard_phase1.html")

@app.get("/dashboard/phase2")
async def dashboard_phase2_ui():
    """Serve the Phase 2 Cache-Based dashboard"""
    return FileResponse(TEMPLATE_DIR / "dashboard_phase2_cache.html")

@app.get("/beta-analysis")
async def beta_analysis_ui():
    """Serve the Beta Analysis dashboard"""
    return FileResponse(TEMPLATE_DIR / "dashboard_beta_analysis.html")

@app.get("/market-analysis")
async def market_analysis_ui():
    """Serve the Market Analysis dashboard"""
    return FileResponse(TEMPLATE_DIR / "dashboard_market_analysis.html")

@app.get("/learn")
async def educational_guide():
    """Serve the educational guide for crypto beginners"""
    return FileResponse(TEMPLATE_DIR / "educational_guide.html")

@app.get("/api/top-symbols")
async def get_top_symbols():
    """Get top symbols with their current data using dynamic selection."""
    try:
        # Try to get real data from integration service using TopSymbolsManager
        integration = get_dashboard_integration()
        if integration:
            symbols_data = await integration.get_top_symbols(limit=10)
            if symbols_data and len(symbols_data) > 0:
                # Convert to expected format and add confluence scores
                top_symbols = []
                
                # Get confluence scores from the dashboard data
                symbol_data = integration.get_symbol_data()
                
                for symbol_info in symbols_data:
                    symbol = symbol_info['symbol']
                    
                    # Get confluence score if available
                    confluence_score = 0
                    if symbol_data and symbol in symbol_data:
                        confluence_score = symbol_data[symbol].get('confluence_score', 0)
                    
                    # Determine status based on confluence score
                    if confluence_score >= 70:
                        status = "strong_bullish"
                    elif confluence_score >= 55:
                        status = "bullish"
                    elif confluence_score >= 45:
                        status = "neutral"
                    elif confluence_score >= 30:
                        status = "bearish"
                    else:
                        status = "strong_bearish"
                    
                    # If no confluence score, use change_24h for status
                    if confluence_score == 0:
                        change_24h = symbol_info.get('change_24h', 0)
                        if change_24h > 3:
                            status = "strong_bullish"
                        elif change_24h > 0:
                            status = "bullish"
                        elif change_24h > -3:
                            status = "neutral"
                        else:
                            status = "bearish"
                    
                    top_symbols.append({
                        "symbol": symbol,
                        "price": symbol_info.get('price', 0),
                        "change_24h": symbol_info.get('change_24h', 0),
                        "volume_24h": symbol_info.get('volume_24h', 0),
                        "status": status,
                        "confluence_score": confluence_score,
                        "turnover_24h": symbol_info.get('turnover_24h', 0),
                        "data_source": symbol_info.get('status', 'active')
                    })
                
                logger.info(f"Returning {len(top_symbols)} dynamic symbols from TopSymbolsManager")
                return {
                    "symbols": top_symbols,
                    "timestamp": int(time.time() * 1000),
                    "source": "dynamic_selection"
                }
        
        # Fallback to mock data if integration not available
        logger.info("Using mock data for top symbols")
        mock_symbols = [
            {
                "symbol": "BTCUSDT",
                "price": 103250.50,
                "change_24h": 2.45,
                "volume_24h": 28500000000,
                "status": "bullish",
                "confluence_score": 72.5,
                "turnover_24h": 2850000000000,
                "data_source": "mock"
            },
            {
                "symbol": "ETHUSDT", 
                "price": 3845.30,
                "change_24h": 1.85,
                "volume_24h": 15200000000,
                "status": "bullish",
                "confluence_score": 68.2,
                "turnover_24h": 584672560000,
                "data_source": "mock"
            },
            {
                "symbol": "SOLUSDT",
                "price": 149.75,
                "change_24h": 4.20,
                "volume_24h": 2100000000,
                "status": "strong_bullish",
                "confluence_score": 78.9,
                "turnover_24h": 314475000000,
                "data_source": "mock"
            },
            {
                "symbol": "AVAXUSDT",
                "price": 42.18,
                "change_24h": -1.25,
                "volume_24h": 850000000,
                "status": "bearish",
                "confluence_score": 32.1,
                "turnover_24h": 35853000000,
                "data_source": "mock"
            },
            {
                "symbol": "XRPUSDT",
                "price": 2.18,
                "change_24h": 0.75,
                "volume_24h": 1800000000,
                "status": "neutral",
                "confluence_score": 48.7,
                "turnover_24h": 3924000000,
                "data_source": "mock"
            }
        ]
        
        return {
            "symbols": mock_symbols,
            "timestamp": int(time.time() * 1000),
            "source": "mock_data"
        }
        
    except Exception as e:
        logger.error(f"Error getting top symbols: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market-report")
async def get_market_report():
    """Get the latest market report (mock data for now)"""
    try:
        # Return mock market data
        return {
            "status": "success",
            "timestamp": int(time.time() * 1000),
            "market_summary": {
                "total_volume": 1234567890,
                "active_symbols": 5,
                "trending_up": 3,
                "trending_down": 2
            },
            "top_performers": [
                {"symbol": "BTCUSDT", "change": "+2.5%", "volume": 500000000},
                {"symbol": "ETHUSDT", "change": "+1.8%", "volume": 300000000},
                {"symbol": "SOLUSDT", "change": "+3.2%", "volume": 150000000}
            ]
        }
    except Exception as e:
        logger.error(f"Error generating market report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# REMOVED: @app.get("/api/dashboard/overview") - conflicts with dashboard.py router
# The dashboard.py router provides the real implementation with live data

@app.get("/api/confluence/breakdown/{symbol}")
async def get_confluence_breakdown(symbol: str):
    """Get detailed confluence breakdown for a symbol"""
    try:
        import aiomcache
        import json
        
        client = aiomcache.Client('localhost', 11211, pool_size=2)
        
        # Try to get full breakdown
        data = await client.get(f'confluence:breakdown:{symbol}'.encode())
        
        if data:
            breakdown = json.loads(data.decode())
            await client.close()
            return {
                'status': 'success',
                'data': breakdown
            }
        
        await client.close()
        raise HTTPException(status_code=404, detail=f"No confluence data for {symbol}")
        
    except Exception as e:
        logger.error(f"Error getting confluence breakdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/confluence/latest")
async def get_latest_confluence():
    """Get the latest confluence breakdown available"""
    try:
        import aiomcache
        import json
        
        client = aiomcache.Client('localhost', 11211, pool_size=2)
        
        # Get latest breakdown
        data = await client.get(b'dashboard:latest_breakdown')
        
        if data:
            breakdown = json.loads(data.decode())
            await client.close()
            return {
                'status': 'success',
                'data': breakdown
            }
        
        await client.close()
        return {
            'status': 'error',
            'message': 'No confluence data available'
        }
        
    except Exception as e:
        logger.error(f"Error getting latest confluence: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# COMMENTED OUT: Conflicts with dashboard.py router route at /api/dashboard/confluence-analysis/{symbol}
# @app.get("/api/dashboard/confluence-analysis/{symbol}")
# async def get_confluence_analysis_terminal(symbol: str):
    """Get terminal-formatted confluence analysis for a symbol"""
    try:
        import aiomcache
        import json
        
        logger.info(f"Getting confluence analysis for {symbol}")
        
        # Create fresh client
        client = aiomcache.Client('localhost', 11211, pool_size=1)
        
        # Get detailed breakdown
        cache_key = f'confluence:breakdown:{symbol}'
        logger.info(f"Looking for cache key: {cache_key}")
        
        try:
            data = await client.get(cache_key.encode())
        except Exception as cache_error:
            logger.warning(f"Cache error for {symbol}: {cache_error}")
            await client.close()
            return {
                'analysis': f'Cache error for {symbol}: {str(cache_error)}',
                'symbol': symbol,
                'timestamp': int(time.time()),
                'score': 50
            }
        
        if not data:
            logger.warning(f"No cache data found for {cache_key}")
            await client.close()
            return {
                'analysis': f'No confluence analysis found for {symbol}',
                'symbol': symbol,
                'timestamp': int(time.time()),
                'score': 50
            }
        
        try:
            breakdown = json.loads(data.decode())
            logger.info(f"Successfully loaded breakdown for {symbol}: score={breakdown.get('overall_score')}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {symbol}: {e}")
            await client.close()
            return {
                'analysis': f'Data format error for {symbol}',
                'symbol': symbol,
                'timestamp': int(time.time()),
                'score': 50
            }
        
        await client.close()
        
        # Format analysis
        try:
            terminal_text = format_simple_analysis(breakdown)
            logger.info(f"Successfully formatted analysis for {symbol}")
        except Exception as format_error:
            logger.error(f"Format error for {symbol}: {format_error}")
            terminal_text = f"Raw analysis for {symbol}:\nScore: {breakdown.get('overall_score', 'N/A')}\nSentiment: {breakdown.get('sentiment', 'N/A')}\nComponents: {len(breakdown.get('components', {}))}"
        
        return {
            'analysis': terminal_text,
            'symbol': symbol,
            'timestamp': breakdown.get('timestamp', int(time.time())),
            'score': breakdown.get('overall_score', 50)
        }
        
    except Exception as e:
        logger.error(f"Error getting confluence analysis for {symbol}: {e}")
        return {
            'analysis': f'Error: {str(e)}',
            'symbol': symbol,
            'timestamp': int(time.time()),
            'score': 50
        }

# COMMENTED OUT: Conflicts with dashboard.py router route at /api/dashboard/confluence-analysis-page
# @app.get("/api/dashboard/confluence-analysis-page")
# async def confluence_analysis_page(symbol: str = "BTCUSDT"):
    """Serve the confluence analysis page"""
    try:
        from fastapi.responses import HTMLResponse
        
        # Read the template
        template_path = "src/dashboard/templates/confluence_analysis.html"
        with open(template_path, 'r') as f:
            html_content = f.read()
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error serving confluence analysis page: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def format_simple_analysis(breakdown: dict) -> str:
    """Simple analysis format to avoid formatting errors"""
    symbol = breakdown.get('symbol', 'UNKNOWN')
    score = breakdown.get('overall_score', 0)
    sentiment = breakdown.get('sentiment', 'NEUTRAL')
    reliability = breakdown.get('reliability', 0)
    components = breakdown.get('components', {})
    interpretations = breakdown.get('interpretations', {})
    
    output = []
    output.append(f"=== {symbol} CONFLUENCE ANALYSIS ===")
    output.append(f"Overall Score: {score:.2f} ({sentiment})")
    output.append(f"Reliability: {reliability}%")
    output.append("")
    
    if components:
        output.append("Component Breakdown:")
        for comp_name, comp_data in components.items():
            comp_score = comp_data.get('score', 0)
            comp_impact = comp_data.get('impact', 0)
            output.append(f"  {comp_name.title()}: {comp_score:.2f} ({comp_impact:.1f}% impact)")
        output.append("")
    
    if interpretations:
        output.append("Market Interpretations:")
        for comp_name, interp in interpretations.items():
            output.append(f"  {comp_name.title()}: {interp[:100]}...")
        output.append("")
    
    return '\n'.join(output)

def format_confluence_terminal(breakdown: dict) -> str:
    """Format confluence breakdown as terminal output"""
    symbol = breakdown.get('symbol', 'UNKNOWN')
    score = breakdown.get('overall_score', 0)
    sentiment = breakdown.get('sentiment', 'NEUTRAL')
    reliability = breakdown.get('reliability', 0)
    components = breakdown.get('components', {})
    sub_components = breakdown.get('sub_components', {})
    interpretations = breakdown.get('interpretations', {})
    
    # Build terminal output
    output = []
    
    # Header
    output.append(f"╔══ {symbol} CONFLUENCE ANALYSIS ══╗")
    output.append("════════════════════════════════════════")
    output.append(f"Overall Score: {score:.2f} ({sentiment})")
    output.append(f"Reliability: {reliability}% ({'HIGH' if reliability >= 80 else 'MEDIUM' if reliability >= 60 else 'LOW'})")
    output.append("")
    
    # Component breakdown table
    if components:
        output.append("Component Breakdown")
        output.append("╔═════════════════╦═══════╦════════╦════════════════════════════════╗")
        output.append("║ Component       ║ Score ║ Impact ║ Gauge                          ║")
        output.append("╠═════════════════╬═══════╬════════╬════════════════════════════════╣")
        
        for comp_name, comp_data in components.items():
            comp_score = comp_data.get('score', 0)
            comp_impact = comp_data.get('impact', 0)
            
            # Create gauge (30 chars)
            gauge_chars = int((comp_score / 100) * 30)
            if comp_score >= 70:
                gauge = "█" * gauge_chars + "·" * (30 - gauge_chars)
            elif comp_score >= 50:
                gauge = "▓" * gauge_chars + "·" * (30 - gauge_chars)
            else:
                gauge = "░" * gauge_chars + "·" * (30 - gauge_chars)
            
            comp_display = comp_name.replace('_', ' ').title()[:15]
            output.append(f"║ {comp_display:<15} ║ {comp_score:5.2f} ║ {comp_impact:6.1f} ║ {gauge} ║")
        
        output.append("╚═════════════════╩═══════╩════════╩════════════════════════════════╝")
        output.append("")
    
    # Sub-components table
    if sub_components:
        output.append("Top Influential Individual Components")
        output.append("╔═════════════════╦═══════════╦════════╦═══════╦══════════════════════╗")
        output.append("║ Component       ║ Parent    ║  Score ║ Trend ║ Gauge                ║")
        output.append("╠═════════════════╬═══════════╬════════╬═══════╬══════════════════════╣")
        
        # Sort by score
        sorted_subs = sorted(sub_components.items(), key=lambda x: x[1].get('score', 0), reverse=True)[:5]
        
        for sub_name, sub_data in sorted_subs:
            sub_score = sub_data.get('score', 0)
            parent = sub_data.get('parent', '').replace('_', ' ').title()
            trend = sub_data.get('trend', '→')
            
            # Create gauge (20 chars)
            gauge_chars = int((sub_score / 100) * 20)
            gauge = "█" * gauge_chars + "·" * (20 - gauge_chars)
            
            sub_display = sub_name.replace('_', ' ')[:15]
            output.append(f"║ {sub_display:<15} ║ {parent:<9} ║ {sub_score:6.2f} ║   {trend}   ║ {gauge} ║")
        
        output.append("╚═════════════════╩═══════════╩════════╩═══════╩══════════════════════╝")
        output.append("")
    
    # Market interpretations
    if interpretations:
        output.append("Market Interpretations")
        output.append("╔═════════════════╦═════════════════════════════════════════════════════════╗")
        output.append("║ Component       ║ Interpretation                                          ║")
        output.append("╠═════════════════╬═════════════════════════════════════════════════════════╣")
        
        for interp_name, interp_text in interpretations.items():
            comp_display = interp_name.replace('_', ' ').title()[:15]
            
            # Wrap text to fit in table (57 chars)
            words = interp_text.split()
            lines = []
            current_line = []
            current_length = 0
            
            for word in words:
                if current_length + len(word) + 1 <= 57:
                    current_line.append(word)
                    current_length += len(word) + 1
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = len(word)
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Output first line with component name
            if lines:
                output.append(f"║ {comp_display:<15} ║ {lines[0]:<55} ║")
                # Output continuation lines
                for line in lines[1:]:
                    output.append(f"║                 ║ {line:<55} ║")
        
        output.append("╚═════════════════╩═════════════════════════════════════════════════════════╝")
    
    return '\n'.join(output)

async def initialize_app_state():
    """Initialize app state with required components"""
    try:
        from src.config.manager import ConfigManager
        from src.core.exchanges.manager import ExchangeManager
        from src.core.monitoring.connection_pool_monitor import get_monitor
        
        logger.info("Initializing app components...")
        
        # Initialize config manager
        config_manager = ConfigManager()
        
        # Initialize exchange manager
        exchange_manager = ExchangeManager(config_manager)
        await exchange_manager.initialize()
        
        # Store in app state
        app.state.config_manager = config_manager
        app.state.exchange_manager = exchange_manager
        
        logger.info("✅ App components initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize app components: {e}")
        # Continue anyway - some endpoints don't need exchange manager

@app.on_event("startup")
async def startup_event():
    """Run on app startup"""
    await initialize_app_state()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    integration = get_dashboard_integration()
    if integration:
        await integration.close()
    logger.info("Dashboard proxy closed")

def main():
    """Run the web server"""
    logger.info("🚀 Starting Virtuoso Trading Dashboard Web Server")
    
    # Initialize config manager to read from config.yaml
    from src.config.manager import ConfigManager
    config_manager = ConfigManager()
    
    # Get web server configuration from config manager
    web_config = config_manager.config.get('web_server', {})
    
    # Get host and port from config with fallbacks
    host = web_config.get('host', '0.0.0.0')
    port = web_config.get('port', 8000)
    log_level = web_config.get('log_level', 'info')
    access_log = web_config.get('access_log', True)
    auto_fallback = web_config.get('auto_fallback', True)
    fallback_ports = web_config.get('fallback_ports', [8001, 8002, 8080, 3000, 5000])
    
    logger.info(f"Starting web server on {host}:{port}")
    
    # Try primary port first, then fallback ports if enabled
    ports_to_try = [port] + (fallback_ports if auto_fallback else [])
    
    for attempt_port in ports_to_try:
        try:
            if attempt_port != port:
                logger.info(f"Primary port {port} unavailable, trying fallback port {attempt_port}")
            
            # Run the server
            uvicorn.run(
                app,
                host=host,
                port=attempt_port,
                log_level=log_level,
                access_log=access_log
            )
            return  # Success, exit function
            
        except OSError as e:
            if e.errno == 48:  # Address already in use
                if attempt_port == ports_to_try[-1]:  # Last port to try
                    logger.error(f"All ports exhausted. Tried: {ports_to_try}")
                    logger.error("Solutions:")
                    logger.error("1. Kill existing processes: python scripts/port_manager.py --kill 8000")
                    logger.error("2. Find available port: python scripts/port_manager.py --find-available")
                    logger.error("3. Update config.yaml web_server.port to use different port")
                    raise
                else:
                    logger.warning(f"Port {attempt_port} is in use, trying next port...")
                    continue
            else:
                logger.error(f"Failed to start web server on {host}:{attempt_port}: {e}")
                raise

if __name__ == "__main__":
    main() 