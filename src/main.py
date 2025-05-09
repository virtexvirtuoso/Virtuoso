"""Main application entry point."""

import os
import sys
import logging
import logging.config
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import time
from datetime import datetime
from typing import Dict, Any
import pandas as pd
import ta
import signal
import traceback
import yaml
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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

# Load environment variables from specific path
env_path = Path(__file__).parent.parent / "config" / "env" / ".env"
load_dotenv(dotenv_path=env_path)
logger = logging.getLogger(__name__)
logger.info(f"Loading environment variables from: {env_path}")

# Initialize root logger with enhanced configuration
configure_logging()

# Get the root logger
logger = logging.getLogger(__name__)

logger.info("🚀 Starting Virtuoso Trading System with enhanced logging")
logger.debug("Debug logging enabled with color support")

# Initialize components
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

def display_banner():
    """Display the Virtuoso ASCII art banner"""
    banner = """
██    ██ ██ ██████  ████████ ██    ██  ██████  ███████  ██████  
██    ██ ██ ██   ██    ██    ██    ██ ██    ██ ██      ██    ██ 
██    ██ ██ ██████     ██    ██    ██ ██    ██ ███████ ██    ██ 
 ██  ██  ██ ██   ██    ██    ██    ██ ██    ██      ██ ██    ██ 
  ████   ██ ██   ██    ██     ██████   ██████  ███████  ██████  
                    ╔═══════════════════╗                    
                    ║   CRYPTO SIGNALS  ║                    
                    ╚═══════════════════╝
"""
    print(banner)
    logger.info("Starting Virtuoso Trading System")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global config_manager, exchange_manager, portfolio_analyzer, database_client
    global confluence_analyzer, top_symbols_manager, market_monitor
    global metrics_manager, alert_manager, market_reporter, health_monitor, validation_service

    try:
        # Initialize config manager
        config_manager = ConfigManager()
        config_manager.config = load_config()
        
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
        
        logger.info(f"Primary exchange initialized: {primary_exchange.exchange_id}")
        
        # Initialize database client
        database_client = DatabaseClient(config_manager.config)
        
        # Initialize portfolio analyzer
        portfolio_analyzer = PortfolioAnalyzer(config_manager.config)
        
        # Initialize confluence analyzer
        confluence_analyzer = ConfluenceAnalyzer(config_manager.config)
        
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
        
        # Initialize metrics manager with alert_manager
        metrics_manager = MetricsManager(config_manager.config, alert_manager)
        
        # Initialize validation service first
        validation_service = AsyncValidationService()
        
        # Initialize signal generator
        signal_generator = SignalGenerator(config_manager.config, alert_manager)
        
        # Initialize top symbols manager
        logger.info("Initializing top symbols manager...")
        top_symbols_manager = TopSymbolsManager(
            exchange_manager=exchange_manager,
            config=config_manager.config,
            validation_service=validation_service
        )
        
        # Initialize market data manager
        logger.info("Initializing market data manager...")
        market_data_manager = MarketDataManager(config_manager.config, exchange_manager, alert_manager)
        
        # Initialize market reporter
        logger.info("Initializing market reporter...")
        market_reporter = MarketReporter(
            top_symbols_manager=top_symbols_manager,
            alert_manager=alert_manager,
            exchange=await exchange_manager.get_primary_exchange(),
            logger=logger
        )
        
        # Initialize market monitor
        logger.info("Initializing market monitor...")
        market_monitor = MarketMonitor(
            logger=logger,
            metrics_manager=metrics_manager
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
        market_monitor.market_reporter = market_reporter
        market_monitor.config = config_manager.config
        
        # Start monitoring system
        logger.info("Starting monitoring system...")
        await market_monitor.start()
        
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
        
        logger.info("Application startup complete - monitoring system active")
        
        yield
        
        # Cleanup on shutdown
        logger.info("Shutting down application...")
        await market_monitor.stop()
        await exchange_manager.cleanup()
        await database_client.close()
        await alert_manager.cleanup()
        
    except Exception as e:
        logger.error(f"Error during application startup: {str(e)}")
        logger.debug(traceback.format_exc())
        raise

# Initialize FastAPI app
# Display banner when app is initialized

app = FastAPI(
    title="Virtuoso Trading System",
    description="High-frequency cryptocurrency trading system",
    version="1.0.0",
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

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

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
                    status["components"]["market_monitor"]["details"]["is_running"] = market_monitor._running
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
        if metrics_manager:
            metrics = await metrics_manager.get_current_metrics()
            
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
        formatted_table = LogFormatter.format_confluence_score_table(
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
                formatted_table = LogFormatter.format_confluence_score_table(
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
        
        # Initialize market data structure
        market_data = {
            'symbol': symbol,
            'ticker': None,
            'orderbook': None,
            'trades': None,
            'ohlcv': {},
            'sentiment': {}
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
                    market_data['ohlcv'][tf_name] = formatted_klines
                    logger.debug(f"Fetched {len(formatted_klines)} klines for {symbol} {tf_name} ({interval})")
                else:
                    logger.warning(f"No klines data for {symbol} {tf_name} ({interval})")
            except Exception as e:
                logger.error(f"Error fetching klines for {symbol} {tf_name}: {str(e)}")
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
        formatted_data = {
            'symbol': market_data['symbol'],
            'ohlcv': {},  # Changed from price_data to ohlcv
            'orderbook': market_data.get('orderbook', {}),
            'trades': market_data.get('trades', []),
            'sentiment': market_data.get('sentiment', {})
        }
        
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
    try:
        # ALERT PIPELINE DEBUG: Verify AlertManager state before market analysis
        if alert_manager:
            logger.info(f"ALERT DEBUG: Before analyze_market, AlertManager handlers: {alert_manager.handlers}")
            if not alert_manager.handlers:
                logger.critical(f"ALERT DEBUG: No handlers registered in AlertManager during analyze_market for {symbol}")
                
        # Get market data
        market_data = await exchange_manager.fetch_market_data(symbol)
        if not market_data:
            logger.error(f"Failed to get market data for {symbol}")
            return None
            
        # Process market data
        formatted_data = await process_market_data(market_data)
        if not formatted_data:
            logger.error(f"Failed to process market data for {symbol}")
            return None
            
        # Run analysis
        logger.info(f"ALERT DEBUG: Running market analysis for {symbol}...")
        analysis = market_monitor.analyze_market(formatted_data)
        
        # ALERT PIPELINE DEBUG: Check analysis results
        if isinstance(analysis, dict):
            if 'confluence_score' in analysis:
                logger.info(f"ALERT DEBUG: Analysis produced confluence score: {analysis['confluence_score']:.2f} for {symbol}")
            else:
                logger.warning(f"ALERT DEBUG: Analysis missing confluence_score for {symbol}")
                
            # Verify component scores
            component_scores = {k: v for k, v in analysis.items() if k.endswith('_score') and k != 'confluence_score'}
            logger.info(f"ALERT DEBUG: Component scores: {component_scores}")
        else:
            logger.error(f"ALERT DEBUG: Invalid analysis result type: {type(analysis)} for {symbol}")
        
        # DIRECT DISCORD ALERT: Add a direct hook here to bypass normal signal flow
        try:
            if isinstance(analysis, dict) and 'confluence_score' in analysis:
                score = analysis['confluence_score']
                buy_threshold = 55.0  # Ensure this matches your config
                
                logger.info(f"DIRECT CHECK: Checking if score {score} exceeds threshold {buy_threshold}")
                
                if score >= buy_threshold:
                    logger.info(f"DIRECT ALERT: Score {score} exceeds buy threshold {buy_threshold} - Sending direct alert")
                    
                    # Directly send a Discord webhook without using the AlertManager
                    if alert_manager and hasattr(alert_manager, 'discord_webhook_url') and alert_manager.discord_webhook_url:
                        webhook_url = alert_manager.discord_webhook_url.strip()
                        logger.info(f"DIRECT ALERT: Using webhook URL: {webhook_url[:20]}...{webhook_url[-10:]}")
                        
                        # Create a simple message
                        webhook_message = {
                            "content": f"🚨 DIRECT ALERT: {symbol} BUY SIGNAL with score {score:.2f}/100 (threshold: {buy_threshold})",
                            "username": "Virtuoso Alerts",
                            "avatar_url": "https://i.imgur.com/4M34hi2.png"
                        }
                        
                        # ALERT PIPELINE DEBUG: Verify webhook details before sending
                        logger.info(f"ALERT DEBUG: Direct alert webhook message: {webhook_message}")
                        logger.info(f"ALERT DEBUG: Direct alert webhook URL valid: {bool(webhook_url and webhook_url.startswith('https://discord.com/api/webhooks/'))}")
                        
                        # Send using both methods for redundancy
                        try:
                            # Method 1: Using aiohttp (standard method)
                            import aiohttp
                            async with aiohttp.ClientSession() as session:
                                headers = {'Content-Type': 'application/json'}
                                logger.info("DIRECT ALERT: Sending webhook via aiohttp")
                                async with session.post(webhook_url, json=webhook_message, headers=headers) as response:
                                    response_status = response.status
                                    response_text = await response.text()
                                    logger.info(f"ALERT DEBUG: Direct alert aiohttp response: status={response_status}, text={response_text[:100]}")
                                    if response.status in (200, 204):
                                        logger.info(f"DIRECT ALERT: Successfully sent Discord alert via aiohttp")
                                    else:
                                        logger.error(f"DIRECT ALERT: Failed to send Discord alert via aiohttp: {response.status}")
                                        logger.error(f"ALERT DEBUG: Response details: {response_text}")
                        except Exception as e:
                            logger.error(f"DIRECT ALERT: Error sending Discord alert via aiohttp: {str(e)}")
                            logger.error(f"ALERT DEBUG: Exception details: {traceback.format_exc()}")
                            
                        try:
                            # Method 2: Using curl subprocess (fallback method)
                            import subprocess
                            import json
                            logger.info("DIRECT ALERT: Sending webhook via curl")
                            curl_cmd = [
                                'curl', '-X', 'POST',
                                '-H', 'Content-Type: application/json',
                                '-d', json.dumps(webhook_message),
                                webhook_url
                            ]
                            result = subprocess.run(curl_cmd, capture_output=True, text=True)
                            if result.returncode == 0:
                                logger.info(f"DIRECT ALERT: Successfully sent Discord alert via curl")
                            else:
                                logger.error(f"DIRECT ALERT: Failed to send Discord alert via curl: {result.stderr}")
                        except Exception as e:
                            logger.error(f"DIRECT ALERT: Error sending Discord alert via curl: {str(e)}")
                    else:
                        logger.error("DIRECT ALERT: No webhook URL available")
        except Exception as e:
            logger.error(f"DIRECT ALERT: Error in direct alert processing: {str(e)}")
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing market for {symbol}: {str(e)}")
        return None

def load_config() -> dict:
    """Load configuration from YAML file."""
    try:
        # Try loading from ../config/config.yaml first
        config_path = Path("../config/config.yaml")
        if not config_path.exists():
            # Fallback to config/config.yaml
            config_path = Path("config/config.yaml")
            
        if not config_path.exists():
            raise FileNotFoundError("Config file not found in ../config/ or config/")
            
        logger.info(f"Loading config from {config_path}")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Validate required config sections
        required_sections = ['monitoring', 'exchanges', 'analysis']
        missing_sections = [s for s in required_sections if s not in config]
        if missing_sections:
            raise ValueError(f"Missing required config sections: {missing_sections}")
            
        return config
        
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        raise

@app.get("/ui")
async def frontend():
    """Serve the frontend UI"""
    return FileResponse("src/static/index.html")

@app.get("/api/top-symbols")
async def get_top_symbols():
    """Get the top trading symbols."""
    try:
        if top_symbols_manager:
            symbols = await top_symbols_manager.get_symbols()
            return {"symbols": list(symbols)[:10]}
        else:
            # Fallback to default symbols
            return {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]}
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

async def main():
    # Display banner at startup
    display_banner()
    
    monitor = None
    try:
        # Initialize config manager
        config_manager = ConfigManager()
        config_manager.config = load_config()
        
        # Initialize exchange manager with config manager
        exchange_manager = ExchangeManager(config_manager)
        await exchange_manager.initialize()
        
        # Initialize database client
        database_client = DatabaseClient(config_manager.config)
        
        # Initialize portfolio analyzer
        portfolio_analyzer = PortfolioAnalyzer(config_manager.config)
        
        # Initialize confluence analyzer
        confluence_analyzer = ConfluenceAnalyzer(config_manager.config)
        
        # Initialize alert manager
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
        
        # Test the Discord webhook with a startup message
        # if 'discord' in alert_manager.handlers:
        #     logger.info("ALERT DEBUG: Sending test alert to Discord to verify connectivity")
        #     await alert_manager.send_alert(
        #         level="INFO", 
        #         message="🔄 System startup: AlertManager initialized and webhook test",
        #         details={"test": True, "timestamp": int(time.time())}
        #     )
        
        # Initialize metrics manager
        metrics_manager = MetricsManager(config_manager.config, alert_manager)
        
        # Initialize signal generator
        signal_generator = SignalGenerator(config_manager.config, alert_manager)
        
        # Initialize validation service
        validation_service = AsyncValidationService()
        
        # Initialize top symbols manager
        logger.info("Initializing top symbols manager...")
        top_symbols_manager = TopSymbolsManager(
            exchange_manager=exchange_manager,
            config=config_manager.config,
            validation_service=validation_service
        )
        
        # Initialize market data manager
        logger.info("Initializing market data manager...")
        market_data_manager = MarketDataManager(config_manager.config, exchange_manager, alert_manager)
        
        # Initialize market reporter
        logger.info("Initializing market reporter...")
        market_reporter = MarketReporter(
            top_symbols_manager=top_symbols_manager,
            alert_manager=alert_manager,
            exchange=await exchange_manager.get_primary_exchange(),
            logger=logger
        )
        
        # Initialize market monitor with all required components
        monitor = MarketMonitor(
            logger=logger,
            metrics_manager=metrics_manager
        )
        
        # Store important components in market_monitor for use
        monitor.exchange_manager = exchange_manager
        monitor.database_client = database_client
        monitor.portfolio_analyzer = portfolio_analyzer
        monitor.confluence_analyzer = confluence_analyzer
        monitor.alert_manager = alert_manager
        monitor.signal_generator = signal_generator
        monitor.top_symbols_manager = top_symbols_manager
        monitor.market_data_manager = market_data_manager
        monitor.market_reporter = market_reporter  # Add the market reporter to the monitor
        monitor.config = config_manager.config
        
        # Handle shutdown signals
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(monitor.stop()))
        
        # Start monitoring
        await monitor.start()
        
        # Keep the application running until interrupted
        # This prevents immediate exit after start() completes
        logger.info("Monitoring system running. Press Ctrl+C to stop.")
        try:
            # Run indefinitely until interrupted
            while True:
                await asyncio.sleep(60)  # Check every 60 seconds
                # Verify monitor is still running
                if not monitor.running:
                    logger.info("Monitor is no longer running. Exiting.")
                    break
        except asyncio.CancelledError:
            logger.info("Main loop cancelled.")
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        logger.debug(traceback.format_exc())
    finally:
        if monitor and monitor.running:
            logger.info("Stopping the monitor...")
            await monitor.stop()
        logger.info("Shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
