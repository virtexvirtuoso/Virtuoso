#!/usr/bin/env python3
"""
CCXT Integration Demo Script

This script demonstrates how to use the CCXT integration in Virtuoso
to fetch market data from various cryptocurrency exchanges.
"""

import asyncio
import logging
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any

# Add src to the path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.core.exchanges.factory import ExchangeFactory
from src.core.exchanges.ccxt_exchange import CCXTExchange
from src.utils.logging_config import configure_logging

# Configure logging
configure_logging()
logger = logging.getLogger("ccxt_demo")

async def demo_exchange(exchange_id: str, symbol: str = "BTC/USDT") -> None:
    """
    Demonstrate basic exchange functionality using CCXT integration
    
    Args:
        exchange_id: Exchange identifier (e.g., 'binance', 'bybit', 'kucoin')
        symbol: Trading pair to fetch data for
    """
    logger.info(f"Starting CCXT demo for {exchange_id} exchange with symbol {symbol}")
    
    # Create exchange configuration
    config = {
        "use_ccxt": True,  # Use CCXT integration
        "exchange_id": exchange_id,  # The actual exchange to connect to via CCXT
        "ccxt_options": {
            "enableRateLimit": True,
            "timeout": 30000
        }
    }
    
    # Create and initialize exchange
    exchange = await ExchangeFactory.create_exchange("ccxt", config)
    
    if not exchange:
        logger.error(f"Failed to create exchange instance for {exchange_id}")
        return
    
    try:
        # Fetch and display ticker data
        logger.info(f"Fetching ticker for {symbol}...")
        ticker = await exchange.fetch_ticker(symbol)
        logger.info(f"Ticker: {json.dumps(ticker, indent=2)}")
        
        # Fetch and display order book
        logger.info(f"Fetching order book for {symbol}...")
        orderbook = await exchange.fetch_order_book(symbol, 5)
        logger.info(f"Order Book: {json.dumps(orderbook, indent=2)}")
        
        # Fetch and display recent trades
        logger.info(f"Fetching recent trades for {symbol}...")
        trades = await exchange.fetch_trades(symbol, limit=3)
        logger.info(f"Recent Trades: {json.dumps(trades[:3], indent=2)}")
        
        # Fetch and display OHLCV data
        logger.info(f"Fetching OHLCV data for {symbol}...")
        ohlcv = await exchange.fetch_historical_klines(
            symbol, 
            "1h",  # 1 hour timeframe
            limit=3
        )
        logger.info(f"OHLCV Data: {json.dumps(ohlcv[:3], indent=2)}")
        
        # Try to fetch funding rate (for futures exchanges)
        try:
            logger.info(f"Fetching funding rate for {symbol}...")
            funding = await exchange.fetch_funding_rate(symbol)
            logger.info(f"Funding Rate: {json.dumps(funding, indent=2)}")
        except Exception as e:
            logger.warning(f"Failed to fetch funding rate: {str(e)}")
        
        # Try to fetch open interest (for futures exchanges)
        try:
            logger.info(f"Fetching open interest for {symbol}...")
            open_interest = await exchange.fetch_open_interest(symbol)
            logger.info(f"Open Interest: {json.dumps(open_interest, indent=2)}")
        except Exception as e:
            logger.warning(f"Failed to fetch open interest: {str(e)}")
        
        # Fetch comprehensive market data
        logger.info(f"Fetching comprehensive market data for {symbol}...")
        market_data = await exchange.fetch_market_data(symbol)
        
        # Display market data summary
        logger.info(f"Market Data Summary for {symbol} on {exchange_id}:")
        logger.info(f"  Last Price: {market_data['ticker']['last']}")
        logger.info(f"  24h Volume: {market_data['ticker']['quoteVolume']} USDT")
        logger.info(f"  Bid/Ask Spread: {market_data['ticker']['ask'] - market_data['ticker']['bid']}")
        
        # Display markets
        logger.info(f"Available markets on {exchange_id}:")
        markets = await exchange.get_markets()
        logger.info(f"Total markets: {len(markets)}")
        
        # Show a few sample markets
        sample_markets = list(markets)[:3]
        for market in sample_markets:
            logger.info(f"  {market['symbol']} (type: {market.get('type', 'spot')})")
        
    except Exception as e:
        logger.error(f"Error during demo: {str(e)}")
    finally:
        # Clean up
        await exchange.close()
        logger.info(f"Closed connection to {exchange_id}")

async def main():
    """Main demo function"""
    # List of exchanges to demonstrate
    exchanges = [
        ("binance", "BTC/USDT"),
        ("bybit", "BTC/USDT"),
        ("kraken", "BTC/USD"),
        ("kucoin", "BTC/USDT"),
    ]
    
    # Run demos sequentially
    for exchange_id, symbol in exchanges:
        logger.info(f"=" * 80)
        logger.info(f"TESTING EXCHANGE: {exchange_id}")
        logger.info(f"=" * 80)
        
        await demo_exchange(exchange_id, symbol)
        
        # Add a small delay between exchange tests
        await asyncio.sleep(1)

if __name__ == "__main__":
    # Parse command line arguments if provided
    import argparse
    
    parser = argparse.ArgumentParser(description="CCXT Integration Demo")
    parser.add_argument("--exchange", "-e", default="binance", 
                        help="Exchange to test (default: binance)")
    parser.add_argument("--symbol", "-s", default="BTC/USDT", 
                        help="Symbol to fetch data for (default: BTC/USDT)")
    
    args = parser.parse_args()
    
    if len(sys.argv) > 1:
        # Run demo for a single specified exchange
        asyncio.run(demo_exchange(args.exchange, args.symbol))
    else:
        # Run demo for multiple exchanges
        asyncio.run(main()) 