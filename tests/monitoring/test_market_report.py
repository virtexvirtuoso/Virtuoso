import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
import math
import time
import random
import asyncio
from datetime import datetime, timedelta
import logging
import sys
import os
import traceback
import ccxt.async_support as ccxt

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir  # The current directory is the project root
src_dir = os.path.join(project_root, 'src')

# Remove any existing src paths to avoid duplicates
sys.path = [p for p in sys.path if not p.endswith('src')]
sys.path.insert(0, src_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_market_report.log')
    ]
)
logger = logging.getLogger(__name__)

try:
    from monitoring.market_reporter import MarketReporter
except ImportError as e:
    logger.error(f"Error importing MarketReporter: {str(e)}")
    logger.error(f"Current directory: {current_dir}")
    logger.error(f"Project root: {project_root}")
    logger.error(f"Src directory: {src_dir}")
    logger.error(f"Python path: {sys.path}")
    logger.error(f"Directory contents:")
    for root, dirs, files in os.walk(project_root):
        logger.error(f"\nDirectory: {root}")
        for d in dirs:
            logger.error(f"  Dir: {d}")
        for f in files:
            logger.error(f"  File: {f}")
    logger.error("\nMake sure the src directory is in your Python path")
    sys.exit(1)

class BybitLiveExchange:
    """Live Bybit exchange wrapper for market reporter testing."""
    
    def __init__(self):
        """Initialize Bybit exchange connection."""
        self.exchange = ccxt.bybit({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True
            }
        })
        self.symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'XRP/USDT:USDT']
        self.timeframes = {
            '1h': 24,    # Last 24 hours
            '4h': 42,    # Last 7 days (42 4-hour periods)
            '1d': 30     # Last 30 days
        }
        
    async def initialize(self):
        """Load markets and set up the exchange."""
        try:
            await self.exchange.load_markets()
            logger.info("Successfully initialized Bybit connection")
        except Exception as e:
            logger.error(f"Error initializing Bybit connection: {str(e)}")
            raise
    
    async def close(self):
        """Close exchange connection."""
        try:
            await self.exchange.close()
            logger.info("Successfully closed Bybit connection")
        except Exception as e:
            logger.error(f"Error closing Bybit connection: {str(e)}")
    
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch current ticker data for a symbol."""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            
            # Add funding rate and other futures-specific data
            try:
                funding_info = await self.exchange.fetch_funding_rate(symbol)
                ticker['info']['fundingRate'] = funding_info.get('fundingRate', 0)
                ticker['info']['markPrice'] = funding_info.get('markPrice', ticker['last'])
                ticker['info']['indexPrice'] = funding_info.get('indexPrice', ticker['last'])
            except Exception as e:
                logger.warning(f"Error fetching funding info for {symbol}: {str(e)}")
            
            return ticker
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {str(e)}")
            return None
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 168) -> List[List[float]]:
        """Fetch OHLCV data for a symbol."""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            return ohlcv
        except Exception as e:
            logger.error(f"Error fetching OHLCV data for {symbol}: {str(e)}")
            return []
    
    async def fetch_order_book(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Fetch order book data for a symbol."""
        try:
            order_book = await self.exchange.fetch_order_book(symbol, limit=limit)
            return order_book
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol}: {str(e)}")
            return None

async def test_market_report():
    """Test market report generation with live Bybit data."""
    exchange = None
    try:
        logger.info("Starting market report test with live Bybit data...")
        
        # Initialize Bybit exchange
        exchange = BybitLiveExchange()
        await exchange.initialize()
        
        # Initialize market reporter
        reporter = MarketReporter(exchange, logger)
        
        # Test different market conditions
        test_intervals = [
            ("Current market state", 0),
            ("Historical data - 1 hour ago", 1),
            ("Historical data - 4 hours ago", 4),
            ("Historical data - 24 hours ago", 24)
        ]
        
        for description, hours_ago in test_intervals:
            logger.info(f"\nTesting {description}...")
            
            # Generate market report
            logger.info("Generating market report...")
            report = await reporter.generate_market_summary()
            
            if not report:
                logger.error("Failed to generate market report")
                return False
            
            # Validate report
            logger.info("Validating report...")
            validation = reporter._validate_report_data(report)
            
            # Log results
            logger.info("\nMarket Report Validation:")
            logger.info(f"Valid: {validation['valid']}")
            logger.info(f"Quality Score: {validation['quality_score']}/100")
            logger.info("\nSection Coverage:")
            for section, present in validation['sections'].items():
                logger.info(f"- {section}: {'✓' if present else '✗'}")
            
            # Print the report sections
            logger.info("\nMarket Report Sections:")
            for section, content in report.items():
                if section not in ['timestamp', 'generated_at']:
                    logger.info(f"\n=== {section} ===")
                    logger.info(content)
            
            # Analyze market conditions
            if 'market_overview' in report:
                logger.info("\nMarket Analysis:")
                logger.info(f"Market Regime: {report['market_overview'].get('regime', 'Unknown')}")
                logger.info(f"Total Volume (24h): ${report['market_overview'].get('total_volume', 0):,.2f}")
                logger.info(f"Total Open Interest: ${report['market_overview'].get('total_open_interest', 0):,.2f}")
            
            # Wait between tests to respect rate limits
            await asyncio.sleep(1)
        
        logger.info("\nTest completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in test_market_report: {str(e)}")
        logger.error("Stack trace:")
        logger.error(traceback.format_exc())
        return False
    finally:
        if exchange:
            await exchange.close()

if __name__ == "__main__":
    try:
        result = asyncio.run(test_market_report())
        if result:
            logger.info("\nTest passed successfully")
            sys.exit(0)
        else:
            logger.error("\nTest failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error running test: {str(e)}")
        logger.error("Stack trace:")
        logger.error(traceback.format_exc())
        sys.exit(1) 