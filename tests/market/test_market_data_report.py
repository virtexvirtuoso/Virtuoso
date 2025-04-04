#!/usr/bin/env python3
"""
Comprehensive test script for market data retrieval and report generation.
This script will:
1. Test the Bybit API connection
2. Fetch market data for top trading pairs
3. Generate a complete market report
4. Send the report via the alert manager

Use this to diagnose issues with empty or zero values in market reports.
"""

import sys
import os
import asyncio
import logging
import json
import yaml
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
import traceback

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("test_market_data_report.log")
    ]
)
logger = logging.getLogger("MarketDataTest")

# Load .env file for API credentials
load_dotenv()

def load_config() -> dict:
    """Load configuration from YAML file just like the main application."""
    try:
        # Try loading from config/config.yaml first
        config_path = Path("config/config.yaml")
        if not config_path.exists():
            # Fallback to src/config/config.yaml
            config_path = Path("src/config/config.yaml")
            
        if not config_path.exists():
            raise FileNotFoundError("Config file not found in config/ or src/config/")
            
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

# Import necessary components
try:
    from src.config.manager import ConfigManager
    from src.core.market.top_symbols import TopSymbolsManager
    from src.monitoring.alert_manager import AlertManager
    from src.monitoring.market_reporter import MarketReporter
    from src.core.exchanges.manager import ExchangeManager
    from src.core.exchanges.bybit import BybitExchange
    from src.core.validation.service import AsyncValidationService
    from src.core.market.market_data_manager import MarketDataManager
    logger.info("Successfully imported all required modules")
except ImportError as e:
    logger.error(f"Failed to import required modules: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

async def test_api_connection(exchange):
    """Test the API connection and credentials."""
    logger.info("=== Testing API Connection ===")
    try:
        # Test if exchange is healthy
        is_healthy = await exchange.is_healthy()
        logger.info(f"Exchange health check: {'Passed' if is_healthy else 'Failed'}")
        
        # Test market tickers fetch
        tickers = await exchange.fetch_market_tickers()
        logger.info(f"Successfully fetched {len(tickers)} market tickers")
        
        # Test ticker fetch for BTCUSDT
        ticker = await exchange.get_ticker("BTCUSDT")
        logger.info(f"Successfully fetched ticker for BTCUSDT: {ticker.get('lastPrice', 'N/A')}")
        
        logger.info("API connection tests passed successfully!")
        return True
    except Exception as e:
        logger.error(f"API connection test failed: {str(e)}")
        traceback.print_exc()
        return False

async def direct_fetch_ohlcv(exchange, symbol='BTCUSDT', timeframe='1h', limit=100):
    """Directly fetch OHLCV data to test if it's working."""
    logger.info(f"=== Fetching OHLCV data for {symbol}, {timeframe} ===")
    try:
        start_time = time.time()
        ohlcv_data = await exchange.fetch_ohlcv(symbol, timeframe, limit)
        elapsed = time.time() - start_time
        
        if ohlcv_data and len(ohlcv_data) > 0:
            logger.info(f"Successfully fetched {len(ohlcv_data)} OHLCV candles in {elapsed:.2f}s")
            logger.info(f"First candle: {ohlcv_data[0] if isinstance(ohlcv_data[0], list) else 'Not a list format'}")
            logger.info(f"Last candle: {ohlcv_data[-1] if isinstance(ohlcv_data[-1], list) else 'Not a list format'}")
            return ohlcv_data
        else:
            logger.error(f"Fetched OHLCV data is empty for {symbol}")
            return None
    except Exception as e:
        logger.error(f"Failed to fetch OHLCV data: {str(e)}")
        traceback.print_exc()
        return None

async def direct_fetch_orderbook(exchange, symbol='BTCUSDT'):
    """Directly fetch orderbook data to test if it's working."""
    logger.info(f"=== Fetching orderbook data for {symbol} ===")
    try:
        start_time = time.time()
        orderbook = await exchange.get_orderbook(symbol)
        elapsed = time.time() - start_time
        
        if orderbook:
            # Log first few ask and bid orders if available
            asks = None
            bids = None
            
            if isinstance(orderbook, dict):
                if 'a' in orderbook:
                    asks = orderbook['a']
                elif 'asks' in orderbook:
                    asks = orderbook['asks']
                
                if 'b' in orderbook:
                    bids = orderbook['b']
                elif 'bids' in orderbook:
                    bids = orderbook['bids']
            
            logger.info(f"Successfully fetched orderbook in {elapsed:.2f}s")
            if asks and bids:
                logger.info(f"Orderbook: {len(asks)} asks, {len(bids)} bids")
            return orderbook
        else:
            logger.error(f"Fetched orderbook is invalid: {orderbook}")
            return None
    except Exception as e:
        logger.error(f"Failed to fetch orderbook: {str(e)}")
        traceback.print_exc()
        return None

async def direct_fetch_trades(exchange, symbol='BTCUSDT', limit=100):
    """Directly fetch recent trades to test if it's working."""
    logger.info(f"=== Fetching trades for {symbol} ===")
    try:
        start_time = time.time()
        trades = await exchange.fetch_trades(symbol, limit=limit)
        elapsed = time.time() - start_time
        
        if trades and len(trades) > 0:
            logger.info(f"Successfully fetched {len(trades)} trades in {elapsed:.2f}s")
            return trades
        else:
            logger.error("Fetched trades list is empty")
            return None
    except Exception as e:
        logger.error(f"Failed to fetch trades: {str(e)}")
        traceback.print_exc()
        return None

async def test_data_retrieval(exchange):
    """Test all necessary data retrieval functions."""
    logger.info("=== Testing Data Retrieval Functions ===")
    
    # Test OHLCV for different timeframes
    test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    results = {
        "ohlcv": {},
        "orderbook": {},
        "trades": {}
    }
    
    for symbol in test_symbols:
        # Test OHLCV for different timeframes
        for timeframe in ['1h', '1d']:  # Reduced timeframes for faster testing
            results["ohlcv"].setdefault(symbol, {})[timeframe] = await direct_fetch_ohlcv(exchange, symbol, timeframe)
        
        # Test orderbook
        results["orderbook"][symbol] = await direct_fetch_orderbook(exchange, symbol)
        
        # Test trades
        results["trades"][symbol] = await direct_fetch_trades(exchange, symbol)
    
    # Calculate success rate
    total_tests = len(test_symbols) * (2 + 1 + 1)  # 2 timeframes + orderbook + trades
    success_count = 0
    
    for symbol in test_symbols:
        # Count successful OHLCV requests
        for timeframe in ['1h', '1d']:
            if results["ohlcv"].get(symbol, {}).get(timeframe):
                success_count += 1
        
        # Count successful orderbook requests
        if results["orderbook"].get(symbol):
            success_count += 1
            
        # Count successful trades requests
        if results["trades"].get(symbol):
            success_count += 1
    
    success_rate = success_count / total_tests if total_tests > 0 else 0
    
    logger.info(f"Data retrieval test completed with {success_rate:.2%} success rate ({total_tests - success_count} failures out of {total_tests} requests)")
    
    return results, success_rate

async def test_market_reporter_integration(market_reporter, alert_manager):
    """Test full market reporter integration with alert sending."""
    logger.info("=== Testing Market Reporter Integration ===")
    
    try:
        # Generate market summary
        logger.info("Generating market summary...")
        report = await market_reporter.generate_market_summary()
        
        if not report:
            logger.error("Failed to generate market report")
            return False
        
        logger.info("Market report generated successfully")
        logger.info(f"Report keys: {list(report.keys() if isinstance(report, dict) else [])}")
        
        # Try to extract some data from the report to verify it has content
        report_has_data = False
        if isinstance(report, dict):
            if 'embeds' in report and isinstance(report['embeds'], list) and len(report['embeds']) > 0:
                embed_titles = [e.get('title', 'No title') for e in report['embeds']]
                logger.info(f"Report embeds: {embed_titles}")
                report_has_data = True
        
        if not report_has_data:
            logger.warning("Report may be empty or in an unexpected format")
        
        # Send the report via alert manager
        if alert_manager:
            logger.info("Sending report via alert manager...")
            if hasattr(alert_manager, 'send_discord_webhook_message'):
                await alert_manager.send_discord_webhook_message(report)
                logger.info("Report sent via Discord webhook")
            else:
                # Fall back to regular alert
                await alert_manager.send_alert(
                    level='INFO',
                    message='Market Summary Report',
                    details={
                        'type': 'market_summary',
                        'webhook_message': report,
                        'timestamp': int(time.time() * 1000)
                    }
                )
                logger.info("Report sent via regular alert")
        else:
            logger.warning("Alert manager not available - report not sent")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in market reporter integration test: {str(e)}")
        traceback.print_exc()
        return False

async def test_market_data_report():
    """Run a comprehensive test of market data retrieval and reporting."""
    logger.info("Starting comprehensive market data retrieval and reporting test")
    
    try:
        # Initialize config manager exactly as in the main application
        logger.info("Initializing config manager...")
        config_manager = ConfigManager()
        config_manager.config = load_config()
        logger.info("Config manager initialized")
        
        # Print API key info for debugging (show just first/last few characters)
        api_key = os.getenv("BYBIT_API_KEY", "")
        api_secret = os.getenv("BYBIT_API_SECRET", "")
        
        if api_key and api_secret:
            logger.info(f"API key found: {api_key[:4]}...{api_key[-4:]} (length: {len(api_key)})")
            logger.info(f"API secret found: {api_secret[:4]}...{api_secret[-4:]} (length: {len(api_secret)})")
        else:
            logger.error("API credentials not found in environment variables!")
            return
        
        # Initialize exchange manager just like in the application
        logger.info("Initializing exchange manager...")
        exchange_manager = ExchangeManager(config_manager)
        if not await exchange_manager.initialize():
            logger.error("Failed to initialize exchange manager")
            return
        
        # Get primary exchange and verify it's available
        primary_exchange = await exchange_manager.get_primary_exchange()
        if not primary_exchange:
            logger.error("No primary exchange available")
            return
        
        logger.info(f"Primary exchange initialized: {primary_exchange.exchange_id}")
        
        # Test API connection
        if not await test_api_connection(primary_exchange):
            logger.error("API connection test failed. Check credentials and network connection.")
            return
        
        # Test data retrieval
        logger.info("Testing data retrieval functions...")
        data_results, success_rate = await test_data_retrieval(primary_exchange)
        
        if success_rate < 0.5:
            logger.error(f"Data retrieval test had too many failures (success rate: {success_rate:.2%})")
            logger.error("Check API credentials, rate limits, and network connection")
            return
        
        # Initialize validation service
        logger.info("Initializing validation service...")
        validation_service = AsyncValidationService()
        
        # Initialize alert manager
        logger.info("Initializing alert manager...")
        alert_manager = AlertManager(config_manager.config)
        
        # Register Discord handler 
        alert_manager.register_discord_handler()
        
        # ALERT PIPELINE DEBUG: Verify AlertManager initialization state
        logger.info("ALERT DEBUG: Verifying AlertManager initialization state")
        logger.info(f"ALERT DEBUG: AlertManager handlers: {alert_manager.handlers}")
        logger.info(f"ALERT DEBUG: AlertManager alert_handlers: {list(alert_manager.alert_handlers.keys()) if hasattr(alert_manager, 'alert_handlers') else []}")
        logger.info(f"ALERT DEBUG: Discord webhook URL configured: {bool(alert_manager.discord_webhook_url) if hasattr(alert_manager, 'discord_webhook_url') else False}")
        
        # Initialize top symbols manager
        logger.info("Initializing top symbols manager...")
        top_symbols_manager = TopSymbolsManager(
            exchange_manager=exchange_manager,
            config=config_manager.config,
            validation_service=validation_service
        )
        
        # Update top symbols
        logger.info("Updating top symbols...")
        await top_symbols_manager.update_top_symbols()
        
        # Get top symbols
        top_symbols = await top_symbols_manager.get_top_traded_symbols(limit=15)
        logger.info(f"Top traded symbols: {top_symbols}")
        
        # Initialize market data manager
        logger.info("Initializing market data manager...")
        market_data_manager = MarketDataManager(config_manager.config, exchange_manager, alert_manager)
        
        # Initialize market reporter
        logger.info("Initializing market reporter...")
        market_reporter = MarketReporter(
            top_symbols_manager=top_symbols_manager,
            alert_manager=alert_manager,
            exchange=primary_exchange,
            logger=logger
        )
        
        # Test market reporter integration
        logger.info("Testing market reporter integration...")
        reporter_result = await test_market_reporter_integration(market_reporter, alert_manager)
        
        if reporter_result:
            logger.info("Market reporter integration test passed!")
        else:
            logger.error("Market reporter integration test failed.")
        
        # Clean up
        await exchange_manager.close()
        if hasattr(alert_manager, 'cleanup'):
            await alert_manager.cleanup()
        
        logger.info("Test completed")
        
    except Exception as e:
        logger.error(f"Error in test_market_data_report: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(test_market_data_report())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled error in main: {str(e)}")
        traceback.print_exc() 