#!/usr/bin/env python3
"""
Enhanced Market Report script that shows how to properly extract and display market data.
This script uses direct Bybit exchange methods for more comprehensive data.
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
logger = logging.getLogger("EnhancedMarketReport")

# Import necessary components
from src.core.market.top_symbols import TopSymbolsManager
from src.monitoring.alert_manager import AlertManager
from src.monitoring.market_reporter import MarketReporter
from src.core.exchanges.manager import ExchangeManager
from src.core.exchanges.bybit import BybitExchange
from src.core.validation.service import AsyncValidationService
from src.config.manager import ConfigManager


class EnhancedMarketReporter(MarketReporter):
    """Enhanced market reporter that properly extracts and formats market data"""
    
    def _extract_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize market data from various sources in the data structure.
        
        This handles different data formats and ensures consistent access to key metrics.
        """
        result = {
            # Default values
            'price': 0.0,
            'change_24h': 0.0,
            'volume': 0.0,
            'turnover': 0.0,
            'open_interest': 0.0,
            'high': 0.0,
            'low': 0.0,
            'timestamp': int(time.time() * 1000)
        }
        
        if not market_data:
            return result
            
        # Extract from price structure (the most direct source)
        if 'price' in market_data and isinstance(market_data['price'], dict):
            price_data = market_data['price']
            result['price'] = float(price_data.get('last', 0.0))
            result['change_24h'] = float(price_data.get('change_24h', 0.0))
            result['volume'] = float(price_data.get('volume', 0.0))
            result['turnover'] = float(price_data.get('turnover', 0.0))
            result['high'] = float(price_data.get('high', 0.0))
            result['low'] = float(price_data.get('low', 0.0))
        
        # Extract from ticker (fallback)
        ticker = market_data.get('ticker', {})
        if not result['price'] and ticker:
            result['price'] = float(ticker.get('last', 0.0))
            result['change_24h'] = float(ticker.get('change24h', ticker.get('change', 0.0)))
            result['volume'] = float(ticker.get('volume', 0.0))
            result['turnover'] = float(ticker.get('turnover24h', ticker.get('turnover', 0.0)))
            result['high'] = float(ticker.get('high', 0.0))
            result['low'] = float(ticker.get('low', 0.0))
            
        # Extract open interest data (can be in different places)
        if 'open_interest' in market_data and isinstance(market_data['open_interest'], dict):
            oi_data = market_data['open_interest']
            result['open_interest'] = float(oi_data.get('current', 0.0))
        elif ticker and 'openInterest' in ticker:
            result['open_interest'] = float(ticker.get('openInterest', 0.0))
        
        # Extract timestamp
        result['timestamp'] = market_data.get('timestamp', int(time.time() * 1000))
        
        return result
    
    async def _calculate_market_overview(self) -> Dict[str, Any]:
        """Calculate market overview metrics with proper data extraction."""
        try:
            total_turnover = 0
            total_oi = 0
            
            # Get all symbols and their market data
            symbols = await self.top_symbols_manager.get_symbols()
            for symbol in symbols:
                symbol_data = await self.top_symbols_manager.get_market_data(symbol)
                if not symbol_data:
                    continue
                
                # Use the extraction helper
                market_metrics = self._extract_market_data(symbol_data)
                
                # Add to totals
                total_turnover += market_metrics['turnover']
                total_oi += market_metrics['open_interest']
            
            return {
                'total_volume': total_turnover,
                'total_oi': total_oi,
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating market overview: {str(e)}")
            return {
                'total_volume': 0,
                'total_oi': 0,
                'timestamp': int(time.time() * 1000)
            }
    
    async def format_market_report(self, overview, top_pairs, market_regime=None, smart_money=None, whale_activity=None):
        """Override format_market_report to handle enhanced market data."""
        # Use the original implementation but with better data extraction
        result = await super().format_market_report(
            overview=overview,
            top_pairs=top_pairs,
            market_regime=market_regime,
            smart_money=smart_money,
            whale_activity=whale_activity
        )
        
        # Return the enhanced report
        return result
    
    async def _get_performance_data(self, top_pairs: List[str]) -> tuple:
        """Get performance data with proper extraction."""
        winners = []
        losers = []
        
        for symbol in top_pairs:
            data = await self.top_symbols_manager.get_market_data(symbol)
            if not data:
                continue
                
            # Use our helper to extract market data properly
            market_metrics = self._extract_market_data(data)
            
            # Get key metrics
            price = market_metrics['price']
            change = market_metrics['change_24h']
            turnover = market_metrics['turnover']
            oi = market_metrics['open_interest']
            
            # Format entry
            entry = f"{symbol} {change:+.2f}% | Vol: {self._format_number(turnover)} | OI: {self._format_number(oi)}"
            
            if change > 0:
                winners.append((change, entry, symbol, price))
            else:
                losers.append((change, entry, symbol, price))
        
        # Sort entries
        winners.sort(reverse=True)
        losers.sort()
        
        return winners, losers


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
                    # Defensive programming: Use .get() to safely access history
                    history_data = oi_history.get('history', [])
                    if len(history_data) > 0:
                        # Use the most recent value
                        current_oi = float(history_data[0].get('value', 0))
                        # And the second most recent if available
                        previous_oi = float(history_data[1].get('value', 0)) if len(history_data) > 1 else 0
                        
                        # Update or create the open_interest field
                        if 'open_interest' not in market_data:
                            market_data['open_interest'] = {}
                        
                        market_data['open_interest']['current'] = current_oi
                        market_data['open_interest']['previous'] = previous_oi
                        market_data['open_interest']['timestamp'] = int(time.time() * 1000)
                        market_data['open_interest']['history'] = history_data
                        
                        # Add direct reference to history for easier access
                        market_data['open_interest_history'] = history_data
            
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

async def test_enhanced_market_report():
    """
    Test the enhanced market reporter with proper data extraction.
    """
    logger.info("Starting enhanced market report test")
    
    # Load environment variables
    load_dotenv()
    
    # Check if Discord webhook is configured
    discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if not discord_webhook_url:
        logger.error("DISCORD_WEBHOOK_URL is not configured in your .env file")
        logger.error("Please add a valid Discord webhook URL to your .env file")
        return
    
    try:
        # Initialize components using centralized function
        logger.info("Initializing components...")
        
        # Use centralized initialization from main.py
        from src.main import initialize_components
        components = await initialize_components()
        
        # Extract components
        config_manager = components['config_manager']
        exchange_manager = components['exchange_manager']
        alert_manager = components['alert_manager']
        top_symbols_manager = components['top_symbols_manager']
        
        logger.info("All components initialized using centralized function")
        
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
        
        # Initialize our ENHANCED MarketReporter (important change!)
        market_reporter = EnhancedMarketReporter(
            top_symbols_manager=top_symbols_manager,
            alert_manager=alert_manager,
            logger=logger
        )
        logger.info("Enhanced market reporter initialized")
        
        # Generate market report
        logger.info("Generating enhanced market report...")
        report_result = await market_reporter.generate_market_summary()
        
        if report_result:
            logger.info("Enhanced market report generated and sent successfully!")
        else:
            logger.warning("Enhanced market report generation or sending failed")
            
    except Exception as e:
        logger.error(f"Error in enhanced market report test: {str(e)}", exc_info=True)
    finally:
        # Cleanup
        if 'alert_manager' in locals():
            await alert_manager.stop()
        
        if 'exchange_manager' in locals():
            await exchange_manager.close()
            
        logger.info("Enhanced test completed")

if __name__ == "__main__":
    asyncio.run(test_enhanced_market_report()) 