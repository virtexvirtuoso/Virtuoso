"""Main application entry point."""

# HARD DISABLE ALPHA ALERTS - REQUESTED BY USER
ALPHA_ALERTS_DISABLED = True
print("🔴 ALPHA ALERTS HARD DISABLED - NO ALPHA PROCESSING WILL OCCUR")

import os
import sys
import logging
import logging.config
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import time
import gc
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
import ta
import signal
import traceback
import yaml
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import importlib
import uuid
import uvicorn

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.manager import ConfigManager
from src.utils.logging_config import configure_logging
from src.core.exchanges.manager import ExchangeManager
from src.core.analysis.portfolio import PortfolioAnalyzer
from src.core.analysis.confluence import ConfluenceAnalyzer
from src.data_storage.database import DatabaseClient
from src.core.market.top_symbols import TopSymbolsManager
from src.monitoring.monitor import MarketMonitor
from src.monitoring.metrics_manager import MetricsManager
from src.monitoring.alert_manager import AlertManager
from src.monitoring.market_reporter import MarketReporter
from src.signal_generation.signal_generator import SignalGenerator
from src.core.validation.service import AsyncValidationService
from src.core.market.market_data_manager import MarketDataManager
from src.monitoring.health_monitor import HealthMonitor

# Import API routes initialization
from src.api import init_api_routes
from src.api.routes.signal_tracking import router as signal_tracking_router

# Load environment variables from specific path
env_path = Path(__file__).parent.parent / "config" / "env" / ".env"
load_dotenv(dotenv_path=env_path)
logger = logging.getLogger(__name__)
logger.info(f"Loading environment variables from: {env_path}")

# Initialize root logger with optimized configuration
try:
    # Try optimized logging first
    from src.utils.optimized_logging import configure_optimized_logging
    configure_optimized_logging(
        log_level="DEBUG",  # Enable DEBUG mode for detailed logging
        enable_async=True,
        enable_structured=False,
        enable_compression=True,
        enable_intelligent_filtering=True
    )
except ImportError:
    # Fallback to standard logging
    configure_logging()

# Get the root logger
logger = logging.getLogger(__name__)

logger.info("🚀 Starting Virtuoso Trading System with enhanced logging")
logger.info("🔍 DEBUG MODE ENABLED - Detailed logging active")
logger.debug("Debug logging enabled with color support")

# Global variables for application components
config_manager = None
exchange_manager = None
portfolio_analyzer = None
database_client = None
confluence_analyzer = None
top_symbols_manager = None
market_monitor = None
metrics_manager = None
alert_manager = None
market_reporter = None
health_monitor = None
validation_service = None
market_data_manager = None

# Resolve paths relative to the project root  
PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "src" / "dashboard" / "templates"
# Also create a direct path from src directory
TEMPLATE_DIR_ALT = Path(__file__).parent / "dashboard" / "templates"

def display_banner():
    """Display the Virtuoso ASCII art banner"""
    banner = """
    ██╗   ██╗██╗██████╗ ████████╗██╗   ██╗ ██████╗ ███████╗ ██████╗ 
    ██║   ██║██║██╔══██╗╚══██╔══╝██║   ██║██╔═══██╗██╔════╝██╔═══██╗
    ██║   ██║██║██████╔╝   ██║   ██║   ██║██║   ██║███████╗██║   ██║
    ╚██╗ ██╔╝██║██╔══██╗   ██║   ██║   ██║██║   ██║╚════██║██║   ██║
     ╚████╔╝ ██║██║  ██║   ██║   ╚██████╔╝╚██████╔╝███████║╚██████╔╝
      ╚═══╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝ ╚═════╝ 
                                                                     
     ██████╗██████╗ ██╗   ██╗██████╗ ████████╗ ██████╗              
    ██╔════╝██╔══██╗╚██╗ ██╔╝██╔══██╗╚══██╔══╝██╔═══██╗             
    ██║     ██████╔╝ ╚████╔╝ ██████╔╝   ██║   ██║   ██║             
    ██║     ██╔══██╗  ╚██╔╝  ██╔═══╝    ██║   ██║   ██║             
    ╚██████╗██║  ██║   ██║   ██║        ██║   ╚██████╔╝             
     ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝        ╚═╝    ╚═════╝              
                                                                     
                      🚀 Advanced Signal Analytics 🚀               
"""
    print(banner)
    logger.info("Starting Virtuoso Trading System")

async def _sync_cleanup():
    """Synchronous cleanup for when event loop is not available."""
    logger.info("Performing synchronous cleanup...")
    
    global market_monitor, exchange_manager, database_client, alert_manager, market_data_manager
    
    # Basic synchronous cleanup
    try:
        if database_client and hasattr(database_client, 'close'):
            if not asyncio.iscoroutinefunction(database_client.close):
                database_client.close()
                logger.info("Database client closed synchronously")
        
        if alert_manager and hasattr(alert_manager, 'cleanup'):
            if not asyncio.iscoroutinefunction(alert_manager.cleanup):
                alert_manager.cleanup()
                logger.info("Alert manager cleanup completed synchronously")
        
        # Force cleanup of any remaining resources
        import gc
        gc.collect()
        logger.info("Synchronous cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during synchronous cleanup: {str(e)}")

async def cleanup_all_components():
    """Centralized cleanup of all system components."""
    logger.info("Starting comprehensive application cleanup...")
    
    global market_monitor, exchange_manager, database_client, alert_manager, market_data_manager
    
    # Check if event loop is still running
    try:
        loop = asyncio.get_running_loop()
        if loop.is_closed():
            logger.warning("Event loop is closed, performing synchronous cleanup only")
            await _sync_cleanup()
            return
    except RuntimeError:
        logger.warning("No running event loop, performing synchronous cleanup only")
        await _sync_cleanup()
        return
    
    # Stop monitor first
    if market_monitor and hasattr(market_monitor, 'running') and market_monitor.running:
        try:
            logger.info("Stopping market monitor...")
            await asyncio.wait_for(market_monitor.stop(), timeout=5.0)
            logger.info("Market monitor stopped successfully")
        except asyncio.TimeoutError:
            logger.warning("Market monitor stop timed out")
        except Exception as e:
            logger.error(f"Error stopping monitor: {str(e)}")
    
    # Stop market data manager
    if market_data_manager and hasattr(market_data_manager, 'stop'):
        try:
            logger.info("Stopping market data manager...")
            await asyncio.wait_for(market_data_manager.stop(), timeout=5.0)
            logger.info("Market data manager stopped successfully")
        except asyncio.TimeoutError:
            logger.warning("Market data manager stop timed out")
        except Exception as e:
            logger.error(f"Error stopping market data manager: {str(e)}")
    
    # Cleanup exchange manager
    if exchange_manager:
        try:
            logger.info("Cleaning up exchange manager...")
            await asyncio.wait_for(exchange_manager.cleanup(), timeout=10.0)
            logger.info("Exchange manager cleanup completed")
        except asyncio.TimeoutError:
            logger.warning("Exchange manager cleanup timed out")
        except Exception as e:
            logger.error(f"Error cleaning up exchange manager: {str(e)}")
    
    # Close database client
    if database_client:
        try:
            logger.info("Closing database client...")
            if hasattr(database_client, 'close'):
                if asyncio.iscoroutinefunction(database_client.close):
                    await asyncio.wait_for(database_client.close(), timeout=5.0)
                else:
                    database_client.close()
            logger.info("Database client closed successfully")
        except asyncio.TimeoutError:
            logger.warning("Database client close timed out")
        except Exception as e:
            logger.error(f"Error closing database client: {str(e)}")
    
    # Cleanup alert manager
    if alert_manager:
        try:
            logger.info("Cleaning up alert manager...")
            if hasattr(alert_manager, 'cleanup'):
                if asyncio.iscoroutinefunction(alert_manager.cleanup):
                    await asyncio.wait_for(alert_manager.cleanup(), timeout=5.0)
                else:
                    alert_manager.cleanup()
            logger.info("Alert manager cleanup completed")
        except asyncio.TimeoutError:
            logger.warning("Alert manager cleanup timed out")
        except Exception as e:
            logger.error(f"Error cleaning up alert manager: {str(e)}")
    
    # Clean up any remaining aiohttp sessions, connectors, and CCXT instances
    try:
        import gc
        import aiohttp
        
        # Clean up CCXT instances first
        ccxt_instances_closed = 0
        for obj in gc.get_objects():
            # Look for CCXT exchange instances
            if hasattr(obj, '__class__') and hasattr(obj.__class__, '__module__'):
                if 'ccxt' in str(obj.__class__.__module__) and hasattr(obj, 'close'):
                    try:
                        if not getattr(obj, 'closed', True):  # If not already closed
                            await obj.close()
                            ccxt_instances_closed += 1
                    except Exception as e:
                        logger.debug(f"Error closing CCXT instance: {e}")
        
        if ccxt_instances_closed > 0:
            logger.info(f"Closed {ccxt_instances_closed} remaining CCXT instances")
        
        # Clean up aiohttp sessions and connectors
        sessions_closed = 0
        connectors_closed = 0
        
        for obj in gc.get_objects():
            if isinstance(obj, aiohttp.ClientSession):
                if not obj.closed:
                    try:
                        await obj.close()
                        sessions_closed += 1
                    except Exception as e:
                        logger.debug(f"Error closing aiohttp session: {e}")
            elif isinstance(obj, aiohttp.TCPConnector):
                if not obj.closed:
                    try:
                        await obj.close()
                        connectors_closed += 1
                    except Exception as e:
                        logger.debug(f"Error closing aiohttp connector: {e}")
        
        if sessions_closed > 0 or connectors_closed > 0:
            logger.info(f"Closed {sessions_closed} aiohttp sessions and {connectors_closed} connectors")
        
        # Cancel all remaining tasks with better error handling
        current_task = asyncio.current_task()
        tasks = [task for task in asyncio.all_tasks() if not task.done() and task != current_task]
        
        if tasks:
            logger.info(f"Cancelling {len(tasks)} remaining tasks...")
            
            # Cancel all tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete cancellation with timeout
            try:
                # Give tasks a chance to handle their cancellation
                done, pending = await asyncio.wait(
                    tasks, 
                    timeout=3.0,
                    return_when=asyncio.ALL_COMPLETED
                )
                
                if pending:
                    logger.warning(f"{len(pending)} tasks did not complete cancellation within timeout")
                    # Force cancel any remaining tasks
                    for task in pending:
                        if not task.done():
                            task.cancel()
                            
                logger.info(f"Successfully cancelled {len(tasks)} tasks")
                
            except Exception as e:
                logger.warning(f"Error during task cancellation: {e}")
        else:
            logger.info("No remaining tasks to cancel")
        
        # Force garbage collection to clean up any remaining references
        gc.collect()
        
        logger.info("All sessions, connectors, and CCXT instances successfully cleaned up")
    except Exception as e:
        logger.error(f"Error during session cleanup: {str(e)}")
    
    logger.info("Comprehensive application cleanup completed")

async def initialize_components():
    """
    Centralized initialization of all system components.
    
    Returns:
        Dict containing all initialized components
    """
    logger.info("Starting centralized component initialization...")
    
    # Initialize config manager
    config_manager = ConfigManager()
    logger.info("✅ ConfigManager initialized")
    
    # Initialize exchange manager with proper config
    logger.info("Initializing exchange manager...")
    exchange_manager = ExchangeManager(config_manager)
    if not await exchange_manager.initialize():
        logger.error("Failed to initialize exchange manager")
        raise RuntimeError("Exchange manager initialization failed")
    
    # Get primary exchange and verify it's available
    primary_exchange = await exchange_manager.get_primary_exchange()
    if not primary_exchange:
        logger.error("No primary exchange available")
        raise RuntimeError("No primary exchange available")
    
    logger.info(f"✅ Primary exchange initialized: {primary_exchange.exchange_id}")
    
    # Initialize database client
    database_client = DatabaseClient(config_manager.config)
    logger.info("✅ DatabaseClient initialized")
    
    # Initialize portfolio analyzer
    portfolio_analyzer = PortfolioAnalyzer(config_manager.config)
    logger.info("✅ PortfolioAnalyzer initialized")
    
    # Initialize confluence analyzer
    confluence_analyzer = ConfluenceAnalyzer(config_manager.config)
    logger.info("✅ ConfluenceAnalyzer initialized")
    
    # Initialize alert manager first
    alert_manager = AlertManager(config_manager.config)
    
    # Register Discord handler 
    alert_manager.register_discord_handler()
    
    # ALERT PIPELINE DEBUG: Verify AlertManager initialization state
    logger.info("ALERT DEBUG: Verifying AlertManager initialization state")
    logger.info(f"ALERT DEBUG: AlertManager handlers: {alert_manager.handlers}")
    logger.info(f"ALERT DEBUG: AlertManager alert_handlers: {list(alert_manager.alert_handlers.keys())}")
    logger.info(f"ALERT DEBUG: Discord webhook URL configured: {bool(alert_manager.discord_webhook_url)}")
    
    # Perform direct validation of AlertManager
    if not alert_manager.handlers:
        logger.critical("ALERT DEBUG: No handlers registered in AlertManager! Attempting to force register Discord...")
        if alert_manager.discord_webhook_url:
            logger.info(f"ALERT DEBUG: Discord webhook URL exists, trying to register: {alert_manager.discord_webhook_url[:20]}...{alert_manager.discord_webhook_url[-10:]}")
            alert_manager.register_handler('discord')
            logger.info(f"ALERT DEBUG: After forced registration, handlers: {alert_manager.handlers}")
        else:
            logger.critical("ALERT DEBUG: No Discord webhook URL configured! Alerts won't work!")
    
    logger.info("✅ AlertManager initialized")
    
    # Initialize metrics manager with alert_manager
    metrics_manager = MetricsManager(config_manager.config, alert_manager)
    logger.info("✅ MetricsManager initialized")
    
    # Initialize validation service first
    validation_service = AsyncValidationService()
    logger.info("✅ AsyncValidationService initialized")
    
    # Initialize signal generator
    signal_generator = SignalGenerator(config_manager.config, alert_manager)
    logger.info("✅ SignalGenerator initialized")
    
    # Initialize top symbols manager
    logger.info("Initializing top symbols manager...")
    top_symbols_manager = TopSymbolsManager(
        exchange_manager=exchange_manager,
        config=config_manager.config,
        validation_service=validation_service
    )
    logger.info("✅ TopSymbolsManager initialized")
    
    # Initialize market data manager
    logger.info("Initializing market data manager...")
    market_data_manager = MarketDataManager(config_manager.config, exchange_manager, alert_manager)
    logger.info("✅ MarketDataManager initialized")
    
    # Initialize market reporter
    logger.info("Initializing market reporter...")
    market_reporter = MarketReporter(
        top_symbols_manager=top_symbols_manager,
        alert_manager=alert_manager,
        exchange=primary_exchange,
        logger=logger
    )
    logger.info("✅ MarketReporter initialized")
    
    # Initialize liquidation detection engine
    logger.info("Initializing liquidation detection engine...")
    liquidation_detector = None
    try:
        from src.core.analysis.liquidation_detector import LiquidationDetectionEngine
        database_url = config_manager.config.get('database', {}).get('url')
        liquidation_detector = LiquidationDetectionEngine(
            exchange_manager=exchange_manager,
            database_url=database_url
        )
        logger.info("✅ LiquidationDetectionEngine initialized")
    except Exception as e:
        logger.error(f"Failed to initialize liquidation detection engine: {e}")
        logger.warning("⚠️ Continuing without liquidation detection engine")
        liquidation_detector = None
    
    # Initialize market monitor with all required components (CENTRALIZED)
    logger.info("Initializing market monitor...")
    market_monitor = MarketMonitor(
        logger=logger,
        metrics_manager=metrics_manager,
        exchange=primary_exchange,
        top_symbols_manager=top_symbols_manager,
        alert_manager=alert_manager,
        config=config_manager.config,
        market_reporter=market_reporter
    )
    
    # Store important components in market_monitor for use
    market_monitor.exchange_manager = exchange_manager
    market_monitor.database_client = database_client
    market_monitor.portfolio_analyzer = portfolio_analyzer
    market_monitor.confluence_analyzer = confluence_analyzer
    market_monitor.alert_manager = alert_manager
    market_monitor.signal_generator = signal_generator
    market_monitor.top_symbols_manager = top_symbols_manager
    market_monitor.market_data_manager = market_data_manager
    market_monitor.liquidation_detector = liquidation_detector
    market_monitor.config = config_manager.config
    logger.info("✅ MarketMonitor initialized")
    
    # Initialize alpha opportunity detection (CENTRALIZED)
    alpha_integration = None
    if ALPHA_ALERTS_DISABLED:
        logger.info("🔴 ALPHA OPPORTUNITY DETECTION DISABLED BY USER REQUEST")
    else:
        logger.info("Initializing alpha opportunity detection...")
        try:
            from src.monitoring.alpha_integration import setup_alpha_integration
            alpha_integration = await setup_alpha_integration(
                monitor=market_monitor,
                alert_manager=alert_manager,
                config=config_manager.config
            )
            logger.info("✅ Alpha opportunity detection enabled - real-time alerts active")
        except Exception as e:
            logger.error(f"Failed to initialize alpha integration: {e}")
            alpha_integration = None
    
    # Initialize dashboard integration service
    logger.info("Initializing dashboard integration...")
    dashboard_integration = None
    try:
        from src.dashboard.dashboard_integration import DashboardIntegrationService, set_dashboard_integration
        dashboard_integration = DashboardIntegrationService(market_monitor)
        
        # Initialize with detailed error handling
        init_success = await dashboard_integration.initialize()
        if init_success:
            await dashboard_integration.start()
            set_dashboard_integration(dashboard_integration)
            logger.info("✅ Dashboard integration service initialized and started successfully")
        else:
            logger.warning("⚠️ Dashboard integration initialization failed")
            dashboard_integration = None
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize dashboard integration service: {e}")
        logger.debug(f"Dashboard integration error details: {traceback.format_exc()}")
        dashboard_integration = None
        logger.warning("⚠️ Continuing startup without dashboard integration")
    
    logger.info("🎉 All components initialized successfully!")
    
    return {
        'config_manager': config_manager,
        'exchange_manager': exchange_manager,
        'primary_exchange': primary_exchange,
        'database_client': database_client,
        'portfolio_analyzer': portfolio_analyzer,
        'confluence_analyzer': confluence_analyzer,
        'alert_manager': alert_manager,
        'metrics_manager': metrics_manager,
        'validation_service': validation_service,
        'signal_generator': signal_generator,
        'top_symbols_manager': top_symbols_manager,
        'market_data_manager': market_data_manager,
        'market_reporter': market_reporter,
        'liquidation_detector': liquidation_detector,
        'market_monitor': market_monitor,
        'alpha_integration': alpha_integration,
        'dashboard_integration': dashboard_integration
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global config_manager, exchange_manager, portfolio_analyzer, database_client
    global confluence_analyzer, top_symbols_manager, market_monitor
    global metrics_manager, alert_manager, market_reporter, health_monitor, validation_service

    try:
        # Check if components are already initialized (from run_application)
        if config_manager is None:
            logger.info("Components not yet initialized, initializing now...")
            # Use centralized initialization
            components = await initialize_components()
            
            # Extract components for global access
            config_manager = components['config_manager']
            exchange_manager = components['exchange_manager']
            database_client = components['database_client']
            portfolio_analyzer = components['portfolio_analyzer']
            confluence_analyzer = components['confluence_analyzer']
            alert_manager = components['alert_manager']
            metrics_manager = components['metrics_manager']
            validation_service = components['validation_service']
            top_symbols_manager = components['top_symbols_manager']
            market_reporter = components['market_reporter']
            market_monitor = components['market_monitor']  # Already initialized in initialize_components()
            
            # Start monitoring system
            logger.info("Starting monitoring system...")
            await market_monitor.start()
            
            # Real-time liquidation data collection is now integrated into MarketMonitor
            # Liquidation events are automatically processed via WebSocket feeds and fed to the detection engine
            if hasattr(market_monitor, 'liquidation_detector') and market_monitor.liquidation_detector:
                logger.info("✅ Real-time liquidation data collection integrated - events will be processed automatically from WebSocket feeds")
        else:
            logger.info("Components already initialized, using existing instances...")
            # Wait for market_monitor to be available if it's being initialized by monitoring task
            max_wait = 30  # 30 seconds timeout
            wait_count = 0
            while market_monitor is None and wait_count < max_wait:
                await asyncio.sleep(1)
                wait_count += 1
            
            if market_monitor is None:
                raise RuntimeError("Market monitor not available after waiting")
            
            logger.info("Using existing market monitor instance")
        
        # Store components in app state
        app.state.config_manager = config_manager
        app.state.exchange_manager = exchange_manager
        app.state.database_client = database_client
        app.state.portfolio_analyzer = portfolio_analyzer
        app.state.confluence_analyzer = confluence_analyzer
        app.state.alert_manager = alert_manager
        app.state.metrics_manager = metrics_manager
        app.state.validation_service = validation_service
        app.state.top_symbols_manager = top_symbols_manager
        app.state.market_reporter = market_reporter
        app.state.market_monitor = market_monitor
        app.state.liquidation_detector = getattr(market_monitor, 'liquidation_detector', None)
        
        logger.info("FastAPI lifespan startup complete - web server ready")
        
        yield
        
        # Cleanup on shutdown - only if we're the ones who initialized
        logger.info("FastAPI lifespan shutdown starting...")
        
        # Note: In concurrent mode, cleanup is handled by the monitoring task
        # We only do minimal cleanup here to avoid double-cleanup
        logger.info("FastAPI lifespan shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during FastAPI lifespan: {str(e)}")
        logger.debug(traceback.format_exc())
        raise

# Initialize FastAPI app
# Display banner when app is initialized

app = FastAPI(
    title="Virtuoso Trading System",
    description="High-frequency cryptocurrency trading system",
    version="1.0.0",
    debug=True,  # Enable FastAPI debug mode
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize API routes
init_api_routes(app)

# Register signal tracking routes
app.include_router(
    signal_tracking_router,
    prefix="/api/signal-tracking",
    tags=["signal-tracking"]
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/dashboard-static", StaticFiles(directory="static"), name="dashboard-static")

@app.get("/")
async def root():
    """Root endpoint with system status"""
    try:
        logger.debug("Root endpoint called - getting system status")
        
        # Initialize status variables
        status = {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "exchange_manager": {
                    "status": "inactive",
                    "error": None,
                    "details": {}
                },
                "database": {
                    "status": "disconnected",
                    "error": None,
                    "details": {}
                },
                "market_monitor": {
                    "status": "inactive",
                    "error": None,
                    "last_update": None,
                    "details": {}
                },
                "top_symbols": {
                    "count": 0,
                    "symbols": [],
                    "error": None,
                    "details": {}
                }
            }
        }
        logger.debug("Initialized status structure")
        
        # Check exchange manager health
        try:
            if exchange_manager:
                logger.debug("Exchange manager exists, checking health...")
                try:
                    is_healthy = await exchange_manager.is_healthy()
                    logger.debug(f"Exchange manager health check result: {is_healthy}")
                    status["components"]["exchange_manager"]["status"] = "active" if is_healthy else "inactive"
                    status["components"]["exchange_manager"]["details"]["initialized"] = bool(exchange_manager)
                    status["components"]["exchange_manager"]["details"]["exchanges"] = list(exchange_manager.exchanges.keys())
                    logger.debug(f"Exchange manager details: {status['components']['exchange_manager']}")
                except Exception as e:
                    error_msg = f"Error during exchange health check: {str(e)}"
                    logger.error(error_msg)
                    status["components"]["exchange_manager"]["error"] = error_msg
            else:
                logger.warning("Exchange manager is not initialized")
                status["components"]["exchange_manager"]["error"] = "Not initialized"
        except Exception as e:
            error_msg = f"Error checking exchange manager: {str(e)}"
            logger.error(error_msg)
            status["components"]["exchange_manager"]["error"] = error_msg
            
        # Check database health
        try:
            if database_client:
                logger.debug("Database client exists, checking health...")
                try:
                    is_healthy = await database_client.is_healthy()
                    logger.debug(f"Database health check result: {is_healthy}")
                    status["components"]["database"]["status"] = "connected" if is_healthy else "disconnected"
                    status["components"]["database"]["details"]["initialized"] = bool(database_client)
                    logger.debug(f"Database details: {status['components']['database']}")
                except Exception as e:
                    error_msg = f"Error during database health check: {str(e)}"
                    logger.error(error_msg)
                    status["components"]["database"]["error"] = error_msg
            else:
                logger.warning("Database client is not initialized")
                status["components"]["database"]["error"] = "Not initialized"
        except Exception as e:
            error_msg = f"Error checking database: {str(e)}"
            logger.error(error_msg)
            status["components"]["database"]["error"] = error_msg
            
        # Check market monitor health
        try:
            if market_monitor:
                logger.debug("Market monitor exists, checking health...")
                try:
                    is_healthy = await market_monitor.is_healthy()
                    logger.debug(f"Market monitor health check result: {is_healthy}")
                    status["components"]["market_monitor"]["status"] = "active" if is_healthy else "inactive"
                    status["components"]["market_monitor"]["last_update"] = market_monitor._last_update_time
                    status["components"]["market_monitor"]["details"]["initialized"] = bool(market_monitor)
                    status["components"]["market_monitor"]["details"]["is_running"] = market_monitor.running
                    logger.debug(f"Market monitor details: {status['components']['market_monitor']}")
                except Exception as e:
                    error_msg = f"Error during market monitor health check: {str(e)}"
                    logger.error(error_msg)
                    status["components"]["market_monitor"]["error"] = error_msg
            else:
                logger.warning("Market monitor is not initialized")
                status["components"]["market_monitor"]["error"] = "Not initialized"
        except Exception as e:
            error_msg = f"Error checking market monitor: {str(e)}"
            logger.error(error_msg)
            status["components"]["market_monitor"]["error"] = error_msg
            
        # Check top symbols manager
        if top_symbols_manager:
            try:
                symbols = await top_symbols_manager.get_symbols()
                status["components"]["top_symbols"]["count"] = len(symbols) if symbols else 0
                status["components"]["top_symbols"]["symbols"] = list(symbols) if symbols else []
                status["components"]["top_symbols"]["details"]["initialized"] = bool(top_symbols_manager)
                logger.debug(f"Top symbols details: {status['components']['top_symbols']}")
            except Exception as e:
                error_msg = f"Error getting top symbols: {str(e)}"
                logger.error(error_msg)
                status["components"]["top_symbols"]["error"] = error_msg
        else:
            status["components"]["top_symbols"]["error"] = "Not initialized"

        # Check overall status
        has_errors = any(
            component.get("error") is not None 
            for component in status["components"].values()
        )
        all_inactive = all(
            component.get("status") in ["inactive", "disconnected"]
            for component in status["components"].values()
        )
        
        if has_errors or all_inactive:
            status["status"] = "error"
            logger.debug(f"System status set to error. Has errors: {has_errors}, All inactive: {all_inactive}")
        else:
            logger.debug("System status check completed successfully")
            
        return status
        
    except Exception as e:
        error_msg = f"Error getting system status: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "error": error_msg,
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check all required components
        required_components = {
            "config_manager": bool(config_manager),
            "exchange_manager": bool(exchange_manager and await exchange_manager.is_healthy()),
            "portfolio_analyzer": bool(portfolio_analyzer),
            "database_client": bool(database_client and await database_client.is_healthy()),
            "market_monitor": bool(market_monitor and market_monitor.is_running()),
            "market_reporter": bool(market_reporter),
            "top_symbols_manager": bool(top_symbols_manager)
        }
        
        # Check if any component is unhealthy
        unhealthy_components = [
            component for component, status in required_components.items() 
            if not status
        ]
        
        if unhealthy_components:
            raise HTTPException(
                status_code=503, 
                detail=f"Unhealthy components: {', '.join(unhealthy_components)}"
            )
            
        # Get system metrics if available
        metrics = {}
        if metrics_manager and hasattr(metrics_manager, 'get_current_metrics'):
            try:
                metrics = await metrics_manager.get_current_metrics()
            except Exception as e:
                logger.debug(f"Could not get metrics: {e}")
        
        return {
            "status": "healthy",
            "components": required_components,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )

@app.get("/version")
async def version():
    """Get application version."""
    return {"version": "1.0.0"}

@app.get("/analysis/{symbol}")
async def get_symbol_analysis(symbol: str):
    """Get latest analysis for a symbol"""
    try:
        # Get market data using exchange manager
        market_data = await exchange_manager.fetch_market_data(symbol)
        if not market_data:
            logger.error(f"Failed to get market data for {symbol}")
            return None
        
        # Log detailed market data structure
        logger.info("Market Data Structure:")
        if isinstance(market_data, dict):
            for exchange_id, data in market_data.items():
                logger.info(f"Exchange {exchange_id}:")
                if isinstance(data, dict):
                    for key, value in data.items():
                        logger.info(f"  {key}: {type(value)}")
                        if isinstance(value, (list, dict)):
                            logger.info(f"    Length/Size: {len(value)}")
                else:
                    logger.info(f"  Data: {type(data)}")
        
        # Format market data for analysis
        formatted_data = {
            'symbol': symbol,
            'timestamp': int(time.time() * 1000),
            'trades': [],
            'price_data': {},
            'orderbook': {},
            'positions': []
        }
        
        # Extract data from each exchange
        for exchange_id, data in market_data.items():
            if isinstance(data, dict) and 'error' not in data:
                # Add trades
                if 'recent_trades' in data:
                    formatted_data['trades'].extend(data['recent_trades'])
                
                # Add orderbook
                if 'orderbook' in data:
                    formatted_data['orderbook'][exchange_id] = data['orderbook']
                
                # Add ticker data to price data
                if 'ticker' in data:
                    ticker = data['ticker']
                    timeframe_data = {
                        'open': [float(ticker.get('open', 0))],
                        'high': [float(ticker.get('high', 0))],
                        'low': [float(ticker.get('low', 0))],
                        'close': [float(ticker.get('last', 0))],
                        'volume': [float(ticker.get('baseVolume', 0))]
                    }
                    formatted_data['price_data']['ltf'] = timeframe_data
                    formatted_data['price_data']['mtf'] = timeframe_data
                    formatted_data['price_data']['htf'] = timeframe_data
        
        logger.info(f"Formatted market data: {formatted_data}")
        
        # Run confluence analysis
        analysis = await confluence_analyzer.analyze(formatted_data)
        logger.info(f"Analysis result for {symbol}: {analysis}")
        
        # Display comprehensive confluence score table with top components and interpretations
        from src.core.formatting import LogFormatter
        formatted_table = LogFormatter.format_enhanced_confluence_score_table(
            symbol=symbol,
            confluence_score=analysis.get('confluence_score', 0),
            components=analysis.get('components', {}),
            results=analysis.get('results', {}),
            weights=analysis.get('metadata', {}).get('weights', {}),
            reliability=analysis.get('reliability', 0.0)
        )
        logger.info(formatted_table)
        
        return {
            "symbol": symbol,
            "timestamp": analysis.get('timestamp', None),
            "score": analysis.get('confluence_score', None),
            "components": analysis.get('components', {}),
            "interpretation": analysis.get('interpretation', {})
        }
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/analysis/{symbol}")
async def websocket_analysis(websocket: WebSocket, symbol: str):
    """Stream real-time analysis updates"""
    await websocket.accept()
    
    try:
        while True:
            try:
                # Get cached market data
                market_data = top_symbols_manager.get_symbol_data(symbol)
                if not market_data:
                    # Fallback to direct fetch if symbol not in top symbols
                    logger.debug(f"No cached data for {symbol}, fetching directly")
                    market_data = await exchange_manager.fetch_market_data(symbol)
                    
                if not market_data:
                    logger.warning(f"No market data available for {symbol}")
                    await asyncio.sleep(1)
                    continue
                
                # Run confluence analysis
                analysis = await confluence_analyzer.analyze(market_data)
                
                # Display comprehensive confluence score table with top components and interpretations
                from src.core.formatting import LogFormatter
                formatted_table = LogFormatter.format_enhanced_confluence_score_table(
                    symbol=symbol,
                    confluence_score=analysis.get('confluence_score', 0),
                    components=analysis.get('components', {}),
                    results=analysis.get('results', {}),
                    weights=analysis.get('metadata', {}).get('weights', {}),
                    reliability=analysis.get('reliability', 0.0)
                )
                logger.info(formatted_table)
                
                # Send analysis to client
                await websocket.send_json({
                    "symbol": symbol,
                    "timestamp": analysis.get('timestamp', None),
                    "score": analysis.get('confluence_score', None),
                    "components": analysis.get('components', {}),
                    "interpretation": analysis.get('interpretation', {})
                })
                
                # Wait before next update
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                await asyncio.sleep(1)
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed for {symbol}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {str(e)}")
        await websocket.close()

async def get_market_data(exchange_manager, symbol: str) -> Dict[str, Any]:
    """Get market data for analysis."""
    try:
        # Get exchange interface
        exchange = exchange_manager.get_primary_exchange().interface

        # Get timeframe configurations
        timeframes = {
            'base': '1',  # 1 minute
            'ltf': '5',   # 5 minutes
            'mtf': '30',  # 30 minutes
            'htf': '240'  # 4 hours
        }
        
        # Initialize market data structure with defensive programming
        market_data = {
            'symbol': symbol,
            'ticker': None,
            'orderbook': None,
            'trades': None,
            'ohlcv': {},
            'sentiment': {},
            'oi_history': [],  # Add this to prevent KeyErrors
            'metadata': {}
        }

        # Fetch OHLCV data for each timeframe
        for tf_name, interval in timeframes.items():
            try:
                klines = await exchange.fetch_historical_klines(
                    symbol=symbol,
                    interval=interval,
                    limit=200  # Get enough data for indicators
                )
                if klines:
                    # Convert klines to proper format
                    formatted_klines = []
                    for k in klines:
                        formatted_klines.append({
                            'timestamp': k[0],
                            'open': float(k[1]),
                            'high': float(k[2]),
                            'low': float(k[3]),
                            'close': float(k[4]),
                            'volume': float(k[5])
                        })
                    # Ensure ohlcv key exists before assignment (defensive programming)
                    if 'ohlcv' not in market_data:
                        market_data['ohlcv'] = {}
                    market_data['ohlcv'][tf_name] = formatted_klines
                    logger.debug(f"Fetched {len(formatted_klines)} klines for {symbol} {tf_name} ({interval})")
                else:
                    logger.warning(f"No klines data for {symbol} {tf_name} ({interval})")
            except Exception as e:
                logger.error(f"Error fetching klines for {symbol} {tf_name}: {str(e)}")
                # Ensure ohlcv key exists before assignment (defensive programming)
                if 'ohlcv' not in market_data:
                    market_data['ohlcv'] = {}
                market_data['ohlcv'][tf_name] = []

        # Fetch other market data
        try:
            ticker = await exchange.fetch_ticker(symbol)
            if ticker:
                market_data['ticker'] = ticker
        except Exception as e:
            logger.error(f"Error fetching ticker: {str(e)}")

        try:
            orderbook = await exchange.fetch_order_book(symbol)
            if orderbook:
                market_data['orderbook'] = orderbook
        except Exception as e:
            logger.error(f"Error fetching orderbook: {str(e)}")

        try:
            trades = await exchange.fetch_trades(symbol, limit=1000)
            if trades:
                market_data['trades'] = trades
        except Exception as e:
            logger.error(f"Error fetching trades: {str(e)}")

        return market_data

    except Exception as e:
        logger.error(f"Error fetching market data for {symbol}: {str(e)}")
        return None

async def process_market_data(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process market data into analysis format."""
    if not market_data:
        return None
        
    try:
        # Defensive programming: Check if required keys exist before accessing
        if 'symbol' not in market_data:
            logger.error("Missing 'symbol' key in market_data")
            return None
            
        formatted_data = {
            'symbol': market_data['symbol'],
            'ohlcv': {},  # Changed from price_data to ohlcv
            'orderbook': market_data.get('orderbook', {}),
            'trades': market_data.get('trades', []),
            'sentiment': market_data.get('sentiment', {})
        }
        
        # Defensive programming: Check if 'ohlcv' key exists before iterating
        if 'ohlcv' not in market_data:
            logger.warning("Missing 'ohlcv' key in market_data, using empty structure")
            return formatted_data
            
        if not isinstance(market_data['ohlcv'], dict):
            logger.warning(f"Invalid 'ohlcv' data type: {type(market_data['ohlcv'])}, expected dict")
            return formatted_data
        
        # Format OHLCV data for each timeframe
        for tf_name, klines in market_data['ohlcv'].items():
            if not klines:
                logger.warning(f"No klines data for timeframe {tf_name}")
                continue
                
            try:
                # Create DataFrame from klines list
                df = pd.DataFrame(klines)
                
                # Verify DataFrame structure
                if len(df.columns) != 6:
                    logger.error(f"Invalid klines data format for {tf_name}: expected 6 columns, got {len(df.columns)}")
                    continue
                    
                # Store raw data in expected format
                formatted_data['ohlcv'][tf_name] = {
                    'data': klines,  # Store raw klines data
                    'timeframe': tf_name
                }
                
                # Set column names for DataFrame processing
                df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                
                # Convert timestamp to datetime and set as index
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # Convert price and volume columns to float
                numeric_columns = ['open', 'high', 'low', 'close', 'volume']
                for col in numeric_columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Drop any rows with NaN values
                df.dropna(subset=numeric_columns, inplace=True)
                
                if len(df) >= 50:  # Ensure enough data for indicators
                    try:
                        # Calculate SMA
                        df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
                        df['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
                        
                        # Calculate RSI
                        df['rsi'] = ta.momentum.rsi(df['close'], window=14)
                        
                        # Calculate MACD
                        macd = ta.trend.MACD(df['close'])
                        df['macd'] = macd.macd_diff()
                        
                        logger.debug(f"Calculated indicators for {tf_name} timeframe with {len(df)} candles")
                    except Exception as e:
                        logger.error(f"Error calculating indicators for {tf_name}: {str(e)}")
                else:
                    logger.warning(f"Insufficient data for {tf_name} indicators: {len(df)} candles")
                
                # Store processed DataFrame
                formatted_data['ohlcv'][tf_name]['dataframe'] = df
                
            except Exception as e:
                logger.error(f"Error processing {tf_name} timeframe: {str(e)}")
                continue
                
        return formatted_data
        
    except Exception as e:
        logger.error(f"Error processing market data: {str(e)}")
        return None

async def analyze_market(symbol: str):
    """Analyze market data for a symbol."""
    # Generate a unique call ID for tracking this specific analysis request
    call_id = str(uuid.uuid4())[:8]
    call_source = "MAIN_PY_API"
    
    try:
        # CALL SOURCE TRACKING: Log the start of analysis with call source
        logger.info(f"[CALL_TRACKING][{call_source}][CALL_ID:{call_id}] Starting market analysis scheduling for {symbol}")
        logger.info(f"[CALL_TRACKING][{call_source}][CALL_ID:{call_id}] Call stack source: main.py analyze_market function")
        
        # ALERT PIPELINE DEBUG: Verify AlertManager state before market analysis
        if alert_manager:
            logger.info(f"ALERT DEBUG: Before scheduling analysis, AlertManager handlers: {alert_manager.handlers}")
            if not alert_manager.handlers:
                logger.critical(f"ALERT DEBUG: No handlers registered in AlertManager during analysis scheduling for {symbol}")
                
        # Get market data
        logger.info(f"[CALL_TRACKING][{call_source}][CALL_ID:{call_id}] Fetching market data for {symbol}")
        market_data = await exchange_manager.fetch_market_data(symbol)
        if not market_data:
            logger.error(f"[CALL_TRACKING][{call_source}][CALL_ID:{call_id}] Failed to get market data for {symbol}")
            return None
            
        # Process market data
        logger.info(f"[CALL_TRACKING][{call_source}][CALL_ID:{call_id}] Processing market data for {symbol}")
        formatted_data = await process_market_data(market_data)
        if not formatted_data:
            logger.error(f"[CALL_TRACKING][{call_source}][CALL_ID:{call_id}] Failed to process market data for {symbol}")
            return None
            
        # Add call tracking metadata to formatted_data
        formatted_data['call_source'] = call_source
        formatted_data['call_id'] = call_id
        formatted_data['call_timestamp'] = time.time()
            
        # Schedule analysis
        logger.info(f"[CALL_TRACKING][{call_source}][CALL_ID:{call_id}] Scheduling market analysis for {symbol}...")
        analysis = await market_monitor.schedule_market_analysis(formatted_data)
        
        # ALERT PIPELINE DEBUG: Check analysis results
        if isinstance(analysis, dict):
            if 'confluence_score' in analysis:
                logger.info(f"[CALL_TRACKING][{call_source}][CALL_ID:{call_id}] Analysis produced confluence score: {analysis['confluence_score']:.2f} for {symbol}")
            else:
                logger.warning(f"[CALL_TRACKING][{call_source}][CALL_ID:{call_id}] Analysis missing confluence_score for {symbol}")
                
            # Verify component scores
            component_scores = {k: v for k, v in analysis.items() if k.endswith('_score') and k != 'confluence_score'}
            logger.info(f"[CALL_TRACKING][{call_source}][CALL_ID:{call_id}] Component scores: {component_scores}")
        else:
            logger.error(f"[CALL_TRACKING][{call_source}][CALL_ID:{call_id}] Invalid analysis result type: {type(analysis)} for {symbol}")
        
        logger.info(f"[CALL_TRACKING][{call_source}][CALL_ID:{call_id}] Completed market analysis scheduling for {symbol}")
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing market for {symbol}: {str(e)}")
        return None



@app.get("/ui")
async def frontend():
    """Serve the frontend UI"""
    return FileResponse("src/static/index.html")

@app.get("/dashboard")
async def dashboard_ui():
    """Serve the main v10 Signal Confluence Matrix dashboard"""
    # Try multiple path options to handle different runtime contexts
    template_path = TEMPLATE_DIR / "dashboard_v10.html"
    if not template_path.exists():
        # Try alternative path
        template_path = TEMPLATE_DIR_ALT / "dashboard_v10.html"
    if not template_path.exists():
        # Try direct path from src
        template_path = Path(__file__).parent / "dashboard" / "templates" / "dashboard_v10.html"
    return FileResponse(template_path)

@app.get("/dashboard/v1")
async def dashboard_v1_ui():
    """Serve the original dashboard"""
    template_path = TEMPLATE_DIR / "dashboard.html"
    if not template_path.exists():
        template_path = TEMPLATE_DIR_ALT / "dashboard.html"
    if not template_path.exists():
        template_path = Path(__file__).parent / "dashboard" / "templates" / "dashboard.html"
    return FileResponse(template_path)

@app.get("/dashboard/mobile")
async def dashboard_mobile_ui():
    """Serve the mobile-optimized dashboard"""
    template_path = TEMPLATE_DIR / "dashboard_mobile_v1.html"
    if not template_path.exists():
        template_path = TEMPLATE_DIR_ALT / "dashboard_mobile_v1.html"
    if not template_path.exists():
        template_path = Path(__file__).parent / "dashboard" / "templates" / "dashboard_mobile_v1.html"
    return FileResponse(template_path)

@app.get("/beta-analysis")
async def beta_analysis_ui():
    """Serve the Beta Analysis dashboard"""
    return FileResponse(TEMPLATE_DIR / "dashboard_beta_analysis.html")

@app.get("/market-analysis")
async def market_analysis_ui():
    """Serve the Interactive Market Analysis dashboard"""
    try:
        from src.core.reporting.interactive_web_report import InteractiveWebReportGenerator
        
        # Initialize the interactive report generator
        report_generator = InteractiveWebReportGenerator(config_manager)
        
        # Generate market analysis report with dashboard integration
        report_data = {
            "title": "Virtuoso Market Analysis",
            "subtitle": "Real-Time Market Intelligence & Technical Analysis",
            "navigation": {
                "show_back_to_dashboard": True,
                "dashboard_url": "/",
                "dashboard_title": "Trading Dashboard"
            },
            "theme": {
                "primary_color": "#ffbf00",  # Terminal amber
                "secondary_color": "#0c1a2b", # Navy blue
                "accent_color": "#ff9900"
            }
        }
        
        # Generate the interactive report HTML
        html_content = await report_generator.generate_market_analysis_report(
            report_data=report_data,
            include_navigation=True
        )
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error serving market analysis page: {e}")
        # Fallback to static file if interactive report fails
        return FileResponse(TEMPLATE_DIR / "dashboard_market_analysis.html")

@app.get("/market-analysis/data")
async def market_analysis_data():
    """
    API endpoint for real-time market analysis data updates.
    Used by the interactive report for live data updates.
    """
    try:
        from src.core.reporting.interactive_web_report import InteractiveWebReportGenerator
        
        report_generator = InteractiveWebReportGenerator(config_manager)
        
        # Fetch latest market data
        market_data = await report_generator.fetch_comprehensive_market_data()
        
        return {
            "status": "success",
            "data": market_data,
            "timestamp": int(time.time() * 1000)
        }
        
    except Exception as e:
        logger.error(f"Error fetching market analysis data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch market data")

@app.get("/api/bybit-direct/top-symbols")
async def get_bybit_direct_symbols():
    """Get top symbols directly from Bybit API - guaranteed to work"""
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            # Get top symbols by turnover from Bybit
            url = "https://api.bybit.com/v5/market/tickers?category=linear"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('retCode') == 0 and 'result' in data:
                        tickers = data['result']['list']
                        
                        # Process and sort by turnover
                        symbols_data = []
                        for ticker in tickers:
                            try:
                                symbol = ticker['symbol']
                                price = float(ticker['lastPrice'])
                                change_24h = float(ticker['price24hPcnt']) * 100
                                volume_24h = float(ticker['volume24h'])
                                turnover_24h = float(ticker['turnover24h'])
                                
                                # Skip symbols with very low turnover
                                if turnover_24h < 10000000:  # $10M minimum
                                    continue
                                
                                # Determine status based on price change
                                if change_24h > 5:
                                    status = "strong_bullish"
                                elif change_24h > 2:
                                    status = "bullish"
                                elif change_24h > -2:
                                    status = "neutral"
                                elif change_24h > -5:
                                    status = "bearish"
                                else:
                                    status = "strong_bearish"
                                
                                symbols_data.append({
                                    "symbol": symbol,
                                    "price": price,
                                    "change_24h": change_24h,
                                    "volume_24h": volume_24h,
                                    "turnover_24h": turnover_24h,
                                    "status": status,
                                    "confluence_score": max(0, min(100, 50 + (change_24h * 2))),
                                    "data_source": "bybit_direct_live"
                                })
                                
                            except (ValueError, KeyError) as e:
                                logger.debug(f"Skipping ticker {ticker.get('symbol', 'unknown')}: {e}")
                                continue
                        
                        # Sort by turnover (highest first)
                        symbols_data.sort(key=lambda x: x['turnover_24h'], reverse=True)
                        
                        # Return top 15 symbols
                        top_symbols = symbols_data[:15]
                        
                        logger.info(f"✅ BYBIT DIRECT: Retrieved {len(top_symbols)} live symbols with real prices")
                        
                        return {
                            "symbols": top_symbols,
                            "timestamp": int(time.time() * 1000),
                            "source": "bybit_direct_api",
                            "total_symbols_processed": len(symbols_data),
                            "status": "live_data_success"
                        }
                
                raise HTTPException(status_code=500, detail="Invalid Bybit API response")
                
    except Exception as e:
        logger.error(f"Error getting direct Bybit data: {e}")
        raise HTTPException(status_code=500, detail=f"Bybit API error: {str(e)}")

@app.get("/api/top-symbols")
async def get_top_symbols():
    """Get top symbols with their current data using dynamic selection."""
    try:
        # Try to get real data from top symbols manager
        if top_symbols_manager:
            try:
                symbols_data = await top_symbols_manager.get_top_symbols(limit=10)
                if symbols_data and len(symbols_data) > 0:
                    # Convert to expected format and add confluence scores
                    top_symbols = []
                    
                    for symbol_info in symbols_data:
                        symbol = symbol_info['symbol']
                        
                        # Get confluence score if available (from confluence analyzer)
                        confluence_score = 0
                        try:
                            if confluence_analyzer:
                                # Get market data for confluence analysis
                                market_data = await exchange_manager.fetch_market_data(symbol)
                                if market_data:
                                    analysis = await confluence_analyzer.analyze(market_data)
                                    confluence_score = analysis.get('confluence_score', 0)
                        except Exception as e:
                            logger.debug(f"Could not get confluence score for {symbol}: {e}")
                        
                        # Determine status based on confluence score or price change
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
                    
                    logger.info(f"Returning {len(top_symbols)} symbols from live data")
                    return {
                        "symbols": top_symbols,
                        "timestamp": int(time.time() * 1000),
                        "source": "live_data"
                    }
            except Exception as e:
                logger.warning(f"Could not get live symbols data: {e}")
        
        # Fallback to mock data if live data not available
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
    """Get the latest market report."""
    try:
        if not market_reporter:
            raise HTTPException(status_code=503, detail="Market reporter not initialized")
            
        # Generate a market summary
        market_summary = await market_reporter.generate_market_summary()
        if not market_summary:
            raise HTTPException(status_code=500, detail="Failed to generate market report")
            
        # Add timestamp to the report
        market_summary["timestamp"] = int(time.time() * 1000)
        
        return market_summary
        
    except Exception as e:
        logger.error(f"Error generating market report: {str(e)}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error generating market report: {str(e)}")

@app.get("/api/dashboard/overview")
async def get_dashboard_overview():
    """Get dashboard overview data"""
    try:
        # Try to get real data from trading system components
        overview = {
            "status": "success",
            "timestamp": int(time.time() * 1000),
            "signals": [],  # Will be populated with real confluence data
            "alerts": {
                "total": 0,
                "critical": 0,
                "warning": 0
            },
            "alpha_opportunities": {
                "total": 0,
                "high_confidence": 0,
                "medium_confidence": 0
            },
            "system_status": {
                "monitoring": "inactive",
                "data_feed": "disconnected",
                "alerts": "disabled"
            }
        }
        
        # Get real confluence signals if available
        if confluence_analyzer and top_symbols_manager:
            try:
                symbols = await top_symbols_manager.get_top_symbols(limit=10)
                signals_data = []
                
                for symbol_info in symbols:
                    symbol = symbol_info['symbol']
                    try:
                        # Get market data for confluence analysis
                        market_data = await exchange_manager.fetch_market_data(symbol)
                        if market_data:
                            # Run confluence analysis
                            analysis = await confluence_analyzer.analyze(market_data)
                            
                            # Create signal data with individual components
                            signal_data = {
                                "symbol": symbol,
                                "confluence_score": analysis.get('confluence_score', 50),
                                "confluence_signals": {
                                    "technical": {
                                        "confidence": analysis.get('components', {}).get('technical', 50),
                                        "direction": "neutral",
                                        "strength": "medium"
                                    },
                                    "volume": {
                                        "confidence": analysis.get('components', {}).get('volume', 50),
                                        "direction": "neutral", 
                                        "strength": "medium"
                                    },
                                    "orderflow": {
                                        "confidence": analysis.get('components', {}).get('orderflow', 50),
                                        "direction": "neutral",
                                        "strength": "medium"
                                    },
                                    "orderbook": {
                                        "confidence": analysis.get('components', {}).get('orderbook', 50),
                                        "direction": "neutral",
                                        "strength": "medium"
                                    },
                                    "sentiment": {
                                        "confidence": analysis.get('components', {}).get('sentiment', 50),
                                        "direction": "neutral",
                                        "strength": "medium"
                                    },
                                    "priceStruct": {
                                        "confidence": analysis.get('components', {}).get('price_structure', 50),
                                        "direction": "neutral",
                                        "strength": "medium"
                                    }
                                }
                            }
                            signals_data.append(signal_data)
                    except Exception as e:
                        logger.debug(f"Could not get confluence analysis for {symbol}: {e}")
                        
                overview["signals"] = signals_data
                
            except Exception as e:
                logger.debug(f"Could not get real confluence data: {e}")
        
        # Update system status based on actual component health
        if market_monitor and hasattr(market_monitor, 'is_running') and market_monitor.is_running():
            overview["system_status"]["monitoring"] = "active"
        
        if exchange_manager and await exchange_manager.is_healthy():
            overview["system_status"]["data_feed"] = "connected"
        
        if alert_manager and hasattr(alert_manager, 'handlers') and alert_manager.handlers:
            overview["system_status"]["alerts"] = "enabled"
        
        return overview
        
    except Exception as e:
        logger.error(f"Error getting dashboard overview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/state")
async def debug_state():
    """Debug endpoint to check app state."""
    return {
        "has_top_symbols_manager": hasattr(app.state, 'top_symbols_manager') and app.state.top_symbols_manager is not None,
        "has_exchange_manager": hasattr(app.state, 'exchange_manager') and app.state.exchange_manager is not None,
        "has_confluence_analyzer": hasattr(app.state, 'confluence_analyzer') and app.state.confluence_analyzer is not None,
        "app_state_attrs": [attr for attr in dir(app.state) if not attr.startswith('_')]
    }

@app.get("/api/dashboard/symbols")
async def get_dashboard_symbols():
    """Get analyzed symbols with confluence scores and prices"""
    try:
        symbols_data = []
        
        # Hardcoded fallback symbols if manager not available
        fallback_symbols = [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "AVAXUSDT",
            "DOGEUSDT", "ADAUSDT", "MATICUSDT", "DOTUSDT", "LINKUSDT"
        ]
        
        # Get managers from app state (globals are None until initialized)
        symbols_manager = getattr(app.state, 'top_symbols_manager', None)
        exchange_mgr = getattr(app.state, 'exchange_manager', None)
        
        logger.info(f"Dashboard symbols - symbols_manager: {symbols_manager is not None}, exchange_mgr: {exchange_mgr is not None}")
        
        if symbols_manager and exchange_mgr:
            try:
                # Get top symbols
                top_symbols = await symbols_manager.get_top_symbols(limit=15)
                logger.info(f"Got {len(top_symbols)} symbols from manager: {[s.get('symbol', s) for s in top_symbols[:5]]}")
                
                for symbol_info in top_symbols:
                    symbol = symbol_info['symbol']
                    try:
                        # Get current ticker data for price
                        ticker = await exchange_mgr.fetch_ticker(symbol)
                        
                        # Try to get confluence score if available
                        confluence_score = 50  # Default score
                        confluence = getattr(app.state, 'confluence_analyzer', None) or confluence_analyzer
                        if confluence:
                            try:
                                market_data = await exchange_mgr.fetch_market_data(symbol)
                                if market_data:
                                    analysis = await confluence.analyze(market_data)
                                    confluence_score = analysis.get('confluence_score', 50)
                            except:
                                pass  # Use default score if analysis fails
                        
                        symbol_data = {
                            "symbol": symbol,
                            "price": ticker.get('last', 0),
                            "confluence_score": confluence_score,
                            "change_24h": ticker.get('percentage', 0),
                            "volume_24h": ticker.get('quoteVolume', 0),
                            "high_24h": ticker.get('high', 0),
                            "low_24h": ticker.get('low', 0)
                        }
                        symbols_data.append(symbol_data)
                        
                    except Exception as e:
                        logger.debug(f"Could not get data for {symbol}: {e}")
                        # Add symbol with minimal data
                        symbols_data.append({
                            "symbol": symbol,
                            "price": 0,
                            "confluence_score": 50,
                            "change_24h": 0
                        })
                        
            except Exception as e:
                logger.error(f"Could not get symbols data: {e}", exc_info=True)
        
        # If no symbols retrieved, use fallback with mock data
        if not symbols_data:
            # Create mock data for fallback symbols
            mock_prices = {
                "BTCUSDT": 105234.56,
                "ETHUSDT": 3456.78,
                "SOLUSDT": 234.56,
                "XRPUSDT": 2.34,
                "AVAXUSDT": 45.67,
                "DOGEUSDT": 0.345,
                "ADAUSDT": 0.89,
                "MATICUSDT": 1.23,
                "DOTUSDT": 12.34,
                "LINKUSDT": 23.45
            }
            
            import random
            for symbol in fallback_symbols[:10]:  # Limit to 10 symbols
                symbols_data.append({
                    "symbol": symbol,
                    "price": mock_prices.get(symbol, random.uniform(10, 1000)),
                    "confluence_score": random.randint(40, 80),
                    "change_24h": random.uniform(-5, 5),
                    "volume_24h": random.uniform(1000000, 100000000),
                    "high_24h": mock_prices.get(symbol, 100) * 1.02,
                    "low_24h": mock_prices.get(symbol, 100) * 0.98
                })
        
        return {
            "symbols": symbols_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard symbols: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/correlation/live-matrix")
async def get_correlation_matrix():
    """Get live correlation matrix data"""
    try:
        # This would integrate with correlation analysis
        matrix_data = {
            "live_matrix": {},
            "timeframe_analysis": {
                "1h": {"trend_direction": "bullish"},
                "4h": {"trend_direction": "neutral"},
                "1d": {"trend_direction": "bearish"}
            },
            "timestamp": int(time.time() * 1000)
        }
        
        # Get real symbols if available
        if top_symbols_manager:
            symbols = await top_symbols_manager.get_top_symbols(limit=10)
            for symbol_info in symbols:
                symbol = symbol_info['symbol']
                matrix_data["live_matrix"][symbol] = {
                    "correlation_score": 0.5,
                    "trend_strength": 50
                }
        
        return matrix_data
        
    except Exception as e:
        logger.error(f"Error getting correlation matrix: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alpha/opportunities")
async def get_alpha_opportunities():
    """Get alpha opportunities"""
    if ALPHA_ALERTS_DISABLED:
        return {"opportunities": [], "message": "Alpha alerts disabled by user request"}
    try:
        opportunities = []
        
        # Get real alpha opportunities if available
        if confluence_analyzer and top_symbols_manager:
            try:
                symbols = await top_symbols_manager.get_top_symbols(limit=5)
                for symbol_info in symbols:
                    symbol = symbol_info['symbol']
                    try:
                        market_data = await exchange_manager.fetch_market_data(symbol)
                        if market_data:
                            analysis = await confluence_analyzer.analyze(market_data)
                            confluence_score = analysis.get('confluence_score', 50)
                            
                            if confluence_score > 65:  # High alpha threshold
                                opportunities.append({
                                    "symbol": symbol,
                                    "alpha_score": confluence_score / 100,
                                    "confidence": 0.8,
                                    "direction": "bullish" if confluence_score > 50 else "bearish",
                                    "timeframe": "1h"
                                })
                    except Exception as e:
                        logger.debug(f"Could not analyze {symbol} for alpha: {e}")
            except Exception as e:
                logger.debug(f"Could not get alpha opportunities: {e}")
        
        return opportunities
        
    except Exception as e:
        logger.error(f"Error getting alpha opportunities: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/alpha/scan")
async def scan_alpha_opportunities(request: dict):
    """Scan for alpha opportunities"""
    if ALPHA_ALERTS_DISABLED:
        return {"scan_results": [], "message": "Alpha scanning disabled by user request"}
    try:
        symbols = request.get('symbols', [])
        timeframes = request.get('timeframes', ['1h'])
        min_confluence_score = request.get('min_confluence_score', 0.5)
        
        scan_results = []
        
        if confluence_analyzer and symbols:
            for symbol in symbols:
                try:
                    market_data = await exchange_manager.fetch_market_data(symbol)
                    if market_data:
                        analysis = await confluence_analyzer.analyze(market_data)
                        confluence_score = analysis.get('confluence_score', 50) / 100
                        
                        if confluence_score >= min_confluence_score:
                            scan_results.append({
                                "symbol": symbol,
                                "confluence_score": confluence_score,
                                "trend_analysis": {
                                    "strength": confluence_score * 100
                                },
                                "timeframes": timeframes
                            })
                except Exception as e:
                    logger.debug(f"Could not scan {symbol}: {e}")
        
        return scan_results
        
    except Exception as e:
        logger.error(f"Error scanning alpha opportunities: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/liquidation/alerts")
async def get_liquidation_alerts():
    """Get liquidation detection alerts"""
    try:
        alerts = []
        
        # Integrate with liquidation detector if available
        if market_monitor and hasattr(market_monitor, 'liquidation_detector'):
            try:
                # Get recent liquidation events from the detector
                symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'AVAXUSDT']
                
                # Use the liquidation detector to get real liquidation events
                liquidation_events = await market_monitor.liquidation_detector.detect_liquidation_events(
                    symbols=symbols,
                    exchanges=['bybit'],  # Focus on Bybit for real liquidation data
                    sensitivity=0.7,
                    lookback_minutes=60
                )
                
                # Convert liquidation events to alerts format
                for event in liquidation_events:
                    alert = {
                        'symbol': event.symbol,
                        'timestamp': int(event.timestamp.timestamp() * 1000),
                        'severity': event.severity.value.upper(),
                        'liquidation_type': event.liquidation_type.value,
                        'confidence_score': event.confidence_score,
                        'price_impact': event.price_impact,
                        'volume_spike_ratio': event.volume_spike_ratio,
                        'trigger_price': event.trigger_price,
                        'liquidated_amount_usd': getattr(event, 'liquidated_amount_usd', 0),
                        'cascade_probability': getattr(event, 'cascade_probability', 0),
                        'suspected_triggers': event.suspected_triggers,
                        'market_conditions': event.market_conditions,
                        'description': f"Liquidation detected: {event.liquidation_type.value} with {event.price_impact:.2f}% price impact"
                    }
                    alerts.append(alert)
                
                # Also get cascade risk alerts
                cascade_alerts = await market_monitor.liquidation_detector.detect_cascade_risk(
                    symbols=symbols,
                    exchanges=['bybit']
                )
                
                # Add cascade alerts
                for cascade in cascade_alerts:
                    alert = {
                        'symbol': cascade.initiating_symbol,
                        'timestamp': int(time.time() * 1000),
                        'severity': cascade.severity.value.upper(),
                        'liquidation_type': 'CASCADE_RISK',
                        'confidence_score': cascade.cascade_probability,
                        'price_impact': 0,
                        'volume_spike_ratio': 0,
                        'trigger_price': 0,
                        'liquidated_amount_usd': cascade.estimated_total_liquidations,
                        'cascade_probability': cascade.cascade_probability,
                        'affected_symbols': cascade.affected_symbols,
                        'suspected_triggers': ['cascade_risk'],
                        'market_conditions': {
                            'correlation_strength': cascade.correlation_strength,
                            'liquidity_adequacy': cascade.liquidity_adequacy,
                            'overall_leverage': cascade.overall_leverage
                        },
                        'description': f"Cascade risk detected: {cascade.cascade_probability:.1%} probability affecting {len(cascade.affected_symbols)} symbols"
                    }
                    alerts.append(alert)
                    
            except Exception as e:
                logger.error(f"Error getting liquidation detector alerts: {str(e)}")
                # Continue with fallback data
        
        # If no real alerts or detector unavailable, return empty list
        if not alerts:
            logger.info("No liquidation alerts detected or detector unavailable")
        
        return alerts
        
    except Exception as e:
        logger.error(f"Error getting liquidation alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/manipulation/alerts")
async def get_manipulation_alerts():
    """Get manipulation detection alerts"""
    try:
        alerts = []
        
        # Integrate with manipulation detector if available
        if market_monitor and hasattr(market_monitor, 'manipulation_detector'):
            try:
                # Get manipulation history from the detector
                manipulation_history = market_monitor.manipulation_detector.get_manipulation_history()
                
                # Convert to alerts format
                for symbol, history in manipulation_history.items():
                    if history:  # If there's manipulation history for this symbol
                        latest = history[-1] if isinstance(history, list) else history
                        alerts.append({
                            "symbol": symbol,
                            "manipulation_type": latest.get('manipulation_type', 'UNKNOWN'),
                            "confidence_score": latest.get('confidence_score', 0.5),
                            "timestamp": latest.get('timestamp', int(time.time() * 1000)),
                            "description": latest.get('description', 'Potential manipulation detected')
                        })
            except Exception as e:
                logger.debug(f"Could not get manipulation alerts: {e}")
        
        return alerts
        
    except Exception as e:
        logger.error(f"Error getting manipulation alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/manipulation/stats")
async def get_manipulation_stats():
    """Get manipulation detection statistics"""
    try:
        stats = {
            "total_analyses": 0,
            "alerts_generated": 0,
            "manipulation_detected": 0,
            "avg_confidence": 0.0
        }
        
        # Get real stats from manipulation detector if available
        if market_monitor and hasattr(market_monitor, 'manipulation_detector'):
            try:
                detector_stats = market_monitor.manipulation_detector.get_stats()
                stats.update(detector_stats)
            except Exception as e:
                logger.debug(f"Could not get manipulation stats: {e}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting manipulation stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/signals/latest")
async def get_latest_signals(limit: int = 10):
    """Get latest trading signals"""
    try:
        signals = []
        
        # Get real signals from confluence analysis if available
        if confluence_analyzer and top_symbols_manager:
            try:
                symbols = await top_symbols_manager.get_top_symbols(limit=limit)
                for symbol_info in symbols:
                    symbol = symbol_info['symbol']
                    try:
                        market_data = await exchange_manager.fetch_market_data(symbol)
                        if market_data:
                            analysis = await confluence_analyzer.analyze(market_data)
                            confluence_score = analysis.get('confluence_score', 50)
                            
                            signals.append({
                                "symbol": symbol,
                                "signal_type": "confluence",
                                "direction": "bullish" if confluence_score > 55 else "bearish" if confluence_score < 45 else "neutral",
                                "strength": confluence_score,
                                "confidence": 0.8,
                                "timestamp": int(time.time() * 1000)
                            })
                    except Exception as e:
                        logger.debug(f"Could not get signal for {symbol}: {e}")
            except Exception as e:
                logger.debug(f"Could not get latest signals: {e}")
        
        return signals
        
    except Exception as e:
        logger.error(f"Error getting latest signals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/alerts/recent")
async def get_recent_alerts(limit: int = 10):
    """Get recent dashboard alerts"""
    try:
        alerts = []
        
        # This would integrate with alert manager
        # For now, return empty or mock data
        return alerts
        
    except Exception as e:
        logger.error(f"Error getting recent alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bitcoin-beta/status")
async def get_bitcoin_beta_status():
    """Get Bitcoin Beta Report scheduler status."""
    try:
        # This would be initialized with the scheduler instance
        # For now, return basic status
        return {
            "status": "available",
            "description": "Bitcoin Beta Analysis Report Generator",
            "features": [
                "Multi-timeframe beta analysis (4H, 30M, 5M, 1M)",
                "Dynamic symbol selection",
                "Statistical measures for traders",
                "Professional PDF reports with charts",
                "Automated scheduling every 6 hours"
            ],
            "schedule": {
                "frequency": "Every 6 hours",
                "times": ["00:00 UTC", "06:00 UTC", "12:00 UTC", "18:00 UTC"]
            }
        }
    except Exception as e:
        logger.error(f"Error getting Bitcoin Beta status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bitcoin-beta/generate")
async def generate_bitcoin_beta_report():
    """Manually trigger Bitcoin Beta Report generation."""
    try:
        logger.info("Manual Bitcoin Beta Report generation requested via API")
        
        # Import here to avoid circular imports
        from src.reports.bitcoin_beta_report import BitcoinBetaReport
        
        if not exchange_manager or not top_symbols_manager:
            raise HTTPException(status_code=503, detail="Required services not available")
            
        # Create Bitcoin Beta Report generator
        beta_report = BitcoinBetaReport(
            exchange_manager=exchange_manager,
            top_symbols_manager=top_symbols_manager,
            config=config_manager.config
        )
        
        # Generate the report
        pdf_path = await beta_report.generate_report()
        
        if pdf_path:
            return {
                "status": "success",
                "message": "Bitcoin Beta Report generated successfully",
                "report_path": pdf_path,
                "timestamp": datetime.utcnow().isoformat(),
                "file_size_kb": os.path.getsize(pdf_path) / 1024 if os.path.exists(pdf_path) else 0
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to generate Bitcoin Beta Report")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating Bitcoin Beta Report via API: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

async def start_web_server():
    """Start the FastAPI web server"""
    import uvicorn
    
    # Ensure config_manager is available
    if config_manager is None:
        logger.error("Config manager not initialized. Cannot start web server.")
        raise RuntimeError("Config manager not initialized")
    
    # Get web server configuration from config manager
    web_config = config_manager.config.get('web_server', {})
    
    # Get host and port from config with fallbacks
    host = web_config.get('host', '0.0.0.0')
    port = web_config.get('port', 8000)
    log_level = web_config.get('log_level', 'info')
    access_log = web_config.get('access_log', True)
    reload = web_config.get('reload', False)
    auto_fallback = web_config.get('auto_fallback', True)
    fallback_ports = web_config.get('fallback_ports', [8001, 8002, 8080, 3000, 5000])
    
    logger.info(f"Starting web server on {host}:{port}")
    
    # Try primary port first, then fallback ports if enabled
    ports_to_try = [port] + (fallback_ports if auto_fallback else [])
    
    for attempt_port in ports_to_try:
        try:
            config = uvicorn.Config(
                app=app,
                host=host,
                port=attempt_port,
                log_level=log_level,
                access_log=access_log,
                reload=reload
            )
            server = uvicorn.Server(config)
            
            if attempt_port != port:
                logger.info(f"Primary port {port} unavailable, trying fallback port {attempt_port}")
            
            await server.serve()
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

async def main():
    """Simplified main function using centralized initialization."""
    # Display banner at startup
    display_banner()
    
    global market_monitor
    
    shutdown_event = asyncio.Event()
    
    def signal_handler():
        """Handle shutdown signals"""
        logger.info("Shutdown signal received")
        shutdown_event.set()
    
    try:
        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)
        
        # Initialize all components using centralized function
        components = await initialize_components()
        
        # Extract market monitor (already fully initialized)
        market_monitor = components['market_monitor']
        
        # Start monitoring
        await market_monitor.start()
        
        # Keep the application running until interrupted
        logger.info("Monitoring system running. Press Ctrl+C to stop.")
        try:
            # Wait for shutdown signal or monitor to stop
            while not shutdown_event.is_set() and market_monitor.running:
                await asyncio.sleep(1)  # Check every second
                
        except asyncio.CancelledError:
            logger.info("Main loop cancelled.")
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        logger.debug(traceback.format_exc())
    finally:
        # Use centralized cleanup
        await cleanup_all_components()
        logger.info("Application shutdown complete")

async def run_application():
    """Run both the monitoring system and web server concurrently"""
    global config_manager, exchange_manager, portfolio_analyzer, database_client
    global confluence_analyzer, top_symbols_manager, market_monitor
    global metrics_manager, alert_manager, market_reporter, health_monitor, validation_service
    
    logger.info("Starting application with concurrent monitoring and web server...")
    
    try:
        # Initialize all components using centralized function
        logger.info("Initializing components before starting services...")
        components = await initialize_components()
        
        # Extract components for global access
        config_manager = components['config_manager']
        exchange_manager = components['exchange_manager']
        database_client = components['database_client']
        portfolio_analyzer = components['portfolio_analyzer']
        confluence_analyzer = components['confluence_analyzer']
        alert_manager = components['alert_manager']
        metrics_manager = components['metrics_manager']
        validation_service = components['validation_service']
        top_symbols_manager = components['top_symbols_manager']
        market_reporter = components['market_reporter']
        market_monitor = components['market_monitor']  # Already fully initialized
        
        logger.info("✅ All components initialized successfully")
        
        # Simplified monitoring main function
        async def monitoring_main():
            """Simplified monitoring main using already initialized components"""
            display_banner()
            
            shutdown_event = asyncio.Event()
            
            def signal_handler():
                """Handle shutdown signals"""
                logger.info("Shutdown signal received")
                shutdown_event.set()
            
            try:
                # Set up signal handlers
                loop = asyncio.get_event_loop()
                for sig in (signal.SIGINT, signal.SIGTERM):
                    loop.add_signal_handler(sig, signal_handler)
                
                # Start monitoring with already initialized components
                await market_monitor.start()
                logger.info("Monitoring system running. Press Ctrl+C to stop.")
                
                # Wait for shutdown signal or monitor to stop
                while not shutdown_event.is_set() and market_monitor.running:
                    await asyncio.sleep(1)  # Check every second
                        
            except asyncio.CancelledError:
                logger.info("Monitoring task cancelled.")
            except Exception as e:
                logger.error(f"Error during monitoring: {str(e)}")
                logger.debug(traceback.format_exc())
            finally:
                # Use centralized cleanup
                if shutdown_event.is_set() or (market_monitor and not market_monitor.running):
                    await cleanup_all_components()
                    logger.info("Monitoring cleanup completed")
        
        # Create tasks for both the monitoring system and web server
        monitoring_task = asyncio.create_task(monitoring_main(), name="monitoring_main")
        web_server_task = asyncio.create_task(start_web_server(), name="web_server")
        
        # Run both tasks concurrently
        await asyncio.gather(monitoring_task, web_server_task)
        
    except KeyboardInterrupt:
        logger.info("Shutdown signal received")
        # Cancel tasks gracefully
        if 'monitoring_task' in locals() and not monitoring_task.done():
            monitoring_task.cancel()
        if 'web_server_task' in locals() and not web_server_task.done():
            web_server_task.cancel()
        
        # Wait for cancellation with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(monitoring_task, web_server_task, return_exceptions=True),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            logger.warning("Tasks did not complete cancellation within timeout")
        except Exception as e:
            logger.error(f"Error during task cancellation: {e}")

@app.post("/api/websocket/initialize")
async def initialize_websocket():
    """Force initialize WebSocket connections for real-time price feeds"""
    global market_data_manager
    try:
        if not market_data_manager:
            return {"error": "Market data manager not available"}
        
        # Force initialize WebSocket connections
        result = await market_data_manager.force_websocket_initialization()
        
        if result:
            return {
                "status": "success",
                "message": "WebSocket connections initialized successfully",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error", 
                "message": "Failed to initialize WebSocket connections",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error initializing WebSocket: {str(e)}")
        return {"error": f"Failed to initialize WebSocket: {str(e)}"}

@app.get("/api/websocket/status")
async def get_websocket_status():
    """Get current WebSocket connection status"""
    global market_data_manager
    try:
        if not market_data_manager:
            return {"error": "Market data manager not available"}
        
        # Get WebSocket status
        status = await market_data_manager.get_websocket_status()
        
        return {
            "websocket": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting WebSocket status: {str(e)}")
        return {"error": f"Failed to get WebSocket status: {str(e)}"}

if __name__ == "__main__":
    try:
        asyncio.run(run_application())
    except KeyboardInterrupt:
        print("\nShutdown complete")
