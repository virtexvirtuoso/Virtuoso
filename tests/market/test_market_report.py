#!/usr/bin/env python3
"""
Test script for the market reporter functionality.
This script will generate and send a market report to Discord to verify the formatting.
"""

import asyncio
import logging
import os
import yaml
import time
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("MarketReportTest")

# Import necessary components
from src.core.market.top_symbols import TopSymbolsManager
from src.monitoring.alert_manager import AlertManager
from src.monitoring.market_reporter import MarketReporter
from src.core.exchanges.manager import ExchangeManager
from src.core.exchanges.bybit import BybitExchange
from src.core.validation.service import AsyncValidationService
from src.config.manager import ConfigManager

async def get_enhanced_market_data(exchange_manager, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Get enhanced market data directly from BybitExchange to ensure we have all required data.
    
    This bypasses the regular data flow to ensure complete data is available for the report.
    """
    result = {}
    
    try:
        # Get the primary exchange (should be Bybit)
        primary_exchange = await exchange_manager.get_primary_exchange()
        if not primary_exchange:
            logger.error("No primary exchange available")
            return {}
            
        # Check if it's a BybitExchange instance
        if not isinstance(primary_exchange, BybitExchange):
            logger.warning(f"Primary exchange is not BybitExchange, but {type(primary_exchange).__name__}")
            # Fall back to using the exchange_manager's fetch methods
            for symbol in symbols:
                result[symbol] = await exchange_manager.fetch_market_data(symbol)
            return result
            
        # Use BybitExchange's comprehensive market data fetching
        for symbol in symbols:
            logger.info(f"Fetching enhanced market data for {symbol}...")
            market_data = await primary_exchange.fetch_market_data(symbol)
            
            # Ensure open interest data is available
            if 'open_interest' not in market_data or not market_data['open_interest'].get('current'):
                logger.info(f"Fetching open interest history for {symbol}...")
                oi_history = await primary_exchange.fetch_open_interest_history(symbol, '5min', 10)
                if oi_history and oi_history.get('history') and len(oi_history['history']) > 0:
                    # Use the most recent value
                    current_oi = float(oi_history['history'][0].get('value', 0))
                    # And the second most recent if available
                    previous_oi = float(oi_history['history'][1].get('value', 0)) if len(oi_history['history']) > 1 else 0
                    
                    # Update or create the open_interest field
                    if 'open_interest' not in market_data:
                        market_data['open_interest'] = {}
                    
                    market_data['open_interest']['current'] = current_oi
                    market_data['open_interest']['previous'] = previous_oi
                    market_data['open_interest']['timestamp'] = int(time.time() * 1000)
                    market_data['open_interest']['history'] = oi_history['history']
                    
                    # Add direct reference to history for easier access
                    market_data['open_interest_history'] = oi_history['history']
            
            # Add more detailed price data if needed
            if not market_data.get('price') or all(v == 0 for v in market_data.get('price', {}).values()):
                ticker = market_data.get('ticker', {})
                market_data['price'] = {
                    'last': float(ticker.get('last', 0)),
                    'high': float(ticker.get('high', 0)),
                    'low': float(ticker.get('low', 0)),
                    'change_24h': float(ticker.get('change', 0)),
                    'volume': float(ticker.get('volume', 0)),
                    'turnover': float(ticker.get('turnover', 0))
                }
            
            # Store the enhanced data
            result[symbol] = market_data
            
        return result
        
    except Exception as e:
        logger.error(f"Error fetching enhanced market data: {str(e)}", exc_info=True)
        return {}

async def test_market_report():
    """
    Test the market reporter by initializing components and generating a report
    with enhanced market data to ensure a complete report.
    """
    logger.info("Starting market report test")
    
    # Load environment variables
    load_dotenv()
    
    # Check if Discord webhook is configured
    discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if not discord_webhook_url:
        logger.error("DISCORD_WEBHOOK_URL is not configured in your .env file")
        logger.error("Please add a valid Discord webhook URL to your .env file")
        return
    
    try:
        # Initialize components
        logger.info("Initializing components...")
        
        # Initialize config manager
        config_manager = ConfigManager()
        logger.info("Config manager initialized")
        
        # Initialize exchange manager
        exchange_manager = ExchangeManager(config_manager)
        await exchange_manager.initialize()
        logger.info("Exchange manager initialized")
        
        # Initialize validation service
        validation_service = AsyncValidationService()
        
        # Initialize AlertManager
        alert_manager = AlertManager(config_manager.config)
        await alert_manager.start()
        logger.info("Alert manager initialized and started")
        
        # Initialize TopSymbolsManager
        top_symbols_manager = TopSymbolsManager(
            exchange_manager=exchange_manager,
            config=config_manager.config,
            validation_service=validation_service
        )
        await top_symbols_manager.initialize()
        logger.info("Top symbols manager initialized")
        
        # Get top trading pairs first
        top_pairs = await top_symbols_manager.get_symbols()
        if not top_pairs:
            logger.error("No top trading pairs found")
            return
            
        logger.info(f"Top trading pairs: {', '.join(top_pairs[:10])}...")
        
        # Enhance market data by directly using BybitExchange methods
        enhanced_data = await get_enhanced_market_data(exchange_manager, top_pairs)
        
        # Cache the enhanced data in top_symbols_manager for use by MarketReporter
        for symbol, data in enhanced_data.items():
            # Add the data to the cache
            if hasattr(top_symbols_manager, '_symbols_cache'):
                if symbol not in top_symbols_manager._symbols_cache:
                    top_symbols_manager._symbols_cache[symbol] = {}
                
                top_symbols_manager._symbols_cache[symbol] = {
                    'timestamp': time.time(),
                    'data': data
                }
        
        # Initialize MarketReporter
        market_reporter = MarketReporter(
            top_symbols_manager=top_symbols_manager,
            alert_manager=alert_manager,
            exchange=await exchange_manager.get_primary_exchange(),
            logger=logger
        )
        logger.info("Market reporter initialized")
        
        # Generate market report
        logger.info("Generating market report...")
        report_result = await market_reporter.generate_market_summary()
        
        if report_result:
            logger.info("Market report generated and sent successfully!")
        else:
            logger.warning("Market report generation or sending failed")
            
    except Exception as e:
        logger.error(f"Error in market report test: {str(e)}", exc_info=True)
    finally:
        # Cleanup
        if 'alert_manager' in locals():
            await alert_manager.stop()
        
        if 'exchange_manager' in locals():
            await exchange_manager.close()
            
        logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(test_market_report()) 