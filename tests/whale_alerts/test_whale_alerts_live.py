#!/usr/bin/env python3
"""
Live testing script for the enhanced whale activity monitoring.

This script fetches real market data from exchanges and tests the whale monitoring
functionality with actual orderbook and trades data.
"""

import asyncio
import logging
import sys
import os
import time
from typing import Dict, Any, List
import numpy as np
import traceback

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import required modules
from src.monitoring.alert_manager import AlertManager
from src.monitoring.monitor import MarketMonitor
from src.monitoring.metrics_manager import MetricsManager
import ccxt.async_support as ccxt

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("whale_test_live")

class MockAlertManager:
    """Mock implementation of AlertManager for testing."""
    
    def __init__(self):
        self.alerts = []
        self.handlers = {"default": print}
        
    async def send_alert(self, level="info", message="", details=None):
        """Record and display the alert."""
        alert = {
            "level": level,
            "message": message,
            "details": details or {},
            "timestamp": time.time()
        }
        self.alerts.append(alert)
        print("\n" + "="*80)
        print(f"ALERT ({level}):")
        print(message)
        print("="*80 + "\n")
        return True

    async def send_signal_alert(self, signal_data):
        """Record and display the signal alert."""
        return await self.send_alert(
            level="info", 
            message=f"Signal alert for {signal_data.get('symbol')}", 
            details=signal_data
        )

    async def start(self):
        """Start the alert manager."""
        return True

class LiveWhaleTest:
    """Test class for whale activity monitoring with live data."""
    
    def __init__(self):
        """Initialize the test class with live exchange connection."""
        self.alert_manager = MockAlertManager()
        
        # Create a minimal config for metrics manager
        config = {
            'metrics': {
                'enabled': True,
                'interval': 60
            }
        }
        
        # Set logging level to DEBUG for more detailed insights
        # We need to override the root logger level to see debug logs
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        
        # Initialize metrics manager with required parameters
        self.metrics_manager = MetricsManager(
            config=config,
            alert_manager=self.alert_manager
        )
        
        # Initialize exchanges
        self.exchanges = {
            'bybit': ccxt.bybit({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap',  # Use perpetual futures
                }
            }),
            'binance': ccxt.binance({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # Use perpetual futures
                }
            }),
        }
        
        # Create a minimal MarketMonitor instance
        self.monitor = MarketMonitor(
            exchange=None,
            exchange_manager=None,
            database_client=None,
            portfolio_analyzer=None,
            confluence_analyzer=None,
            alert_manager=self.alert_manager,
            metrics_manager=self.metrics_manager,
            market_data_manager=None
        )
        
        # Configure whale activity monitoring with lower thresholds for testing
        self.monitor.whale_activity_config = {
            'enabled': True,
            'accumulation_threshold': 500000,  # $500k for BTC, ETH
            'distribution_threshold': 500000,  # $500k for BTC, ETH
            'cooldown': 0,                     # No cooldown for testing
            'imbalance_threshold': 0.2,        # 20% order book imbalance threshold
            'min_order_count': 3,              # Minimum number of whale orders
            'market_percentage': 0.02,         # 2% of market to be considered significant
        }
        
        # Initialize tracking dict
        self.monitor._last_whale_alert = {}
        self.monitor._last_whale_activity = {}
        
        # Define symbols to monitor
        self.symbols = {
            'bybit': ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT'],
            'binance': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],
        }
        
    async def get_current_price(self, exchange, symbol):
        """Get the current price for a symbol."""
        try:
            ticker = await exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {str(e)}")
            # Fallback to using the trade data if available
            return 0
            
    async def fetch_market_data(self, exchange_id, symbol):
        """Fetch live market data for a symbol."""
        logger.info(f"Fetching market data for {symbol} from {exchange_id}")
        exchange = self.exchanges[exchange_id]
        
        try:
            # Fetch orderbook (depth=100 for better analysis)
            orderbook = await exchange.fetch_order_book(symbol, limit=100)
            
            # Fetch recent trades
            trades = await exchange.fetch_trades(symbol, limit=100)
            
            # Fetch ticker for current price
            ticker = await exchange.fetch_ticker(symbol)
            
            # Enhanced trade debugging - PRODUCTION SAMPLE DATA
            if trades and len(trades) > 0:
                logger.debug(f"=== PRODUCTION TRADE DATA SAMPLE for {symbol} ===")
                logger.debug(f"Total trades fetched: {len(trades)}")
                
                # Log the first trade's structure
                sample_trade = trades[0]
                logger.debug(f"Trade data keys: {list(sample_trade.keys())}")
                
                # Log a sample of the trade data in human-readable format
                logger.debug(f"Sample trade data: {sample_trade}")
                
                # Extract most important fields for whale detection
                sizes = [float(t.get('amount', t.get('size', 0))) for t in trades]
                sides = [t.get('side', '?') for t in trades]
                
                # Show distribution of trade sizes
                if sizes:
                    min_size = min(sizes)
                    max_size = max(sizes)
                    avg_size = sum(sizes) / len(sizes)
                    median_size = sorted(sizes)[len(sizes)//2]
                    
                    logger.debug(f"Trade size statistics:")
                    logger.debug(f"  Min: {min_size:.6f}")
                    logger.debug(f"  Max: {max_size:.6f}")
                    logger.debug(f"  Avg: {avg_size:.6f}")
                    logger.debug(f"  Median: {median_size:.6f}")
                    
                    # Count trades by side
                    buy_count = sides.count('buy')
                    sell_count = sides.count('sell')
                    logger.debug(f"Trade sides: {buy_count} buys, {sell_count} sells")
                    
                    # Create 5 size buckets for distribution analysis
                    size_range = max_size - min_size
                    if size_range > 0:
                        bucket_size = size_range / 5
                        buckets = [0, 0, 0, 0, 0]
                        
                        for size in sizes:
                            bucket_idx = min(int((size - min_size) / bucket_size), 4)
                            buckets[bucket_idx] += 1
                        
                        logger.debug(f"Trade size distribution in 5 buckets:")
                        for i, count in enumerate(buckets):
                            lower = min_size + i * bucket_size
                            upper = min_size + (i+1) * bucket_size if i < 4 else max_size
                            logger.debug(f"  Bucket {i+1} ({lower:.6f}-{upper:.6f}): {count} trades")
                    
                    # Show the largest trades (potential whales)
                    logger.debug(f"Top 5 largest trades:")
                    trade_infos = []
                    for trade in trades:
                        size = float(trade.get('amount', trade.get('size', 0)))
                        price = float(trade.get('price', 0))
                        side = trade.get('side', '?')
                        timestamp = trade.get('timestamp', 0)
                        
                        # Convert timestamp to readable time if available
                        if timestamp:
                            from datetime import datetime
                            time_str = datetime.fromtimestamp(timestamp/1000).strftime('%H:%M:%S')
                        else:
                            time_str = 'unknown'
                            
                        trade_infos.append({
                            'size': size,
                            'price': price,
                            'side': side,
                            'time': time_str,
                            'usd_value': size * price
                        })
                    
                    # Sort by size and show the top 5
                    sorted_trades = sorted(trade_infos, key=lambda x: x['size'], reverse=True)
                    for i, trade in enumerate(sorted_trades[:5]):
                        logger.debug(f"  {i+1}. {trade['side'].upper()} {trade['size']:.6f} @ {trade['price']} (${trade['usd_value']:.2f}) at {trade['time']}")
            
            # Create market data structure
            market_data = {
                'symbol': symbol,
                'orderbook': orderbook,
                'trades': trades,
                'ticker': ticker
            }
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error fetching market data: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    async def run_live_test(self):
        """Run live monitoring for all configured symbols."""
        logger.info("Starting live whale activity monitoring")
        
        # Add a wrapper for the _monitor_whale_activity method to provide more debug information
        original_monitor_method = self.monitor._monitor_whale_activity
        
        async def enhanced_monitor_method(symbol, market_data):
            """Enhanced wrapper around _monitor_whale_activity for debugging"""
            logger.debug(f"\n=== ENHANCED DEBUGGING for {symbol} ===")
            
            # Debug orderbook and trades
            if 'orderbook' in market_data:
                ob = market_data['orderbook']
                if 'bids' in ob and 'asks' in ob:
                    # Calculate standard deviation of order sizes to understand whale threshold
                    bid_sizes = [float(bid[1]) for bid in ob['bids'][:50]]
                    ask_sizes = [float(ask[1]) for ask in ob['asks'][:50]]
                    all_sizes = bid_sizes + ask_sizes
                    
                    if all_sizes:
                        mean_size = np.mean(all_sizes)
                        std_size = np.std(all_sizes)
                        whale_threshold = mean_size + (3 * std_size)
                        
                        logger.debug(f"Trade statistics:")
                        logger.debug(f"  Mean size: {mean_size:.6f}")
                        logger.debug(f"  Std dev: {std_size:.6f}")
                        logger.debug(f"  Whale threshold (mean + 3*std): {whale_threshold:.6f}")
                        
                        # Count whales in orderbook
                        whale_bids = [b for b in ob['bids'] if float(b[1]) >= whale_threshold]
                        whale_asks = [a for a in ob['asks'] if float(a[1]) >= whale_threshold]
                        
                        logger.debug(f"  Whale orders: {len(whale_bids)} bids, {len(whale_asks)} asks")
                        
                        # Log top 3 orders for both sides for comparison
                        logger.debug(f"TOP BIDS (price, size):")
                        for i, bid in enumerate(ob['bids'][:3]):
                            logger.debug(f"  {i+1}. {bid[0]}, {bid[1]}")
                            
                        logger.debug(f"TOP ASKS (price, size):")
                        for i, ask in enumerate(ob['asks'][:3]):
                            logger.debug(f"  {i+1}. {ask[0]}, {ask[1]}")
                            
            # Debug recent trades in detail
            if 'trades' in market_data and market_data['trades']:
                trades = market_data['trades']
                
                # Here we perform the same analysis that happens in _monitor_whale_activity
                # but with more detailed logging
                recent_time_threshold = time.time() - 1800  # 30 minutes
                
                logger.debug(f"\nTRADES DETAILED ANALYSIS:")
                logger.debug(f"  Analyzing {len(trades)} recent trades")
                logger.debug(f"  Time threshold: {recent_time_threshold} ({time.strftime('%H:%M:%S', time.gmtime(recent_time_threshold))} UTC)")
                
                # Categorize trades by time
                recent_trades = []
                old_trades = []
                invalid_time_trades = []
                
                for trade in trades:
                    trade_time = float(trade.get('timestamp', 0)) / 1000 if isinstance(trade.get('timestamp'), int) else 0
                    if trade_time == 0:
                        invalid_time_trades.append(trade)
                    elif trade_time < recent_time_threshold:
                        old_trades.append(trade)
                    else:
                        recent_trades.append(trade)
                
                logger.debug(f"  Trade time breakdown:")
                logger.debug(f"    Recent trades (< 30min old): {len(recent_trades)}")
                logger.debug(f"    Old trades (> 30min old): {len(old_trades)}")
                logger.debug(f"    Invalid timestamp trades: {len(invalid_time_trades)}")
                
                # Now calculate trade-based whale threshold
                whale_threshold = 0
                if 'orderbook' in market_data and 'bids' in market_data['orderbook']:
                    # Same calculation from _monitor_whale_activity
                    ob = market_data['orderbook']
                    bid_sizes = [float(bid[1]) for bid in ob['bids'][:50]]
                    ask_sizes = [float(ask[1]) for ask in ob['asks'][:50]]
                    all_sizes = bid_sizes + ask_sizes
                    
                    if all_sizes:
                        mean_size = np.mean(all_sizes)
                        std_size = np.std(all_sizes)
                        whale_threshold = mean_size + (3 * std_size)
                
                # Analyze trade sizes relative to whale threshold
                if whale_threshold > 0 and recent_trades:
                    logger.debug(f"  Whale threshold for trades: {whale_threshold/2:.4f} (50% of orderbook threshold)")
                    
                    # Count trades by size
                    whale_buy_trades = []
                    whale_sell_trades = []
                    small_trades = []
                    
                    for trade in recent_trades:
                        # Extract trade data
                        side = trade.get('side', '').lower()
                        size = float(trade.get('amount', trade.get('size', trade.get('quantity', 0))))
                        price = float(trade.get('price', 0))
                        value = size * price
                        
                        # Analyze if it's a whale trade
                        is_whale = size >= (whale_threshold / 2)
                        
                        if is_whale:
                            if side == 'buy':
                                whale_buy_trades.append((size, price, value))
                            elif side == 'sell':
                                whale_sell_trades.append((size, price, value))
                        else:
                            small_trades.append((size, price, value))
                    
                    # Log counts and volumes
                    logger.debug(f"  Trade size classification:")
                    logger.debug(f"    Whale buy trades: {len(whale_buy_trades)}")
                    logger.debug(f"    Whale sell trades: {len(whale_sell_trades)}")
                    logger.debug(f"    Small trades: {len(small_trades)}")
                    
                    # Calculate volumes
                    buy_volume = sum(t[0] for t in whale_buy_trades)
                    sell_volume = sum(t[0] for t in whale_sell_trades)
                    small_volume = sum(t[0] for t in small_trades)
                    
                    logger.debug(f"  Trade volumes:")
                    logger.debug(f"    Whale buy volume: {buy_volume:.4f}")
                    logger.debug(f"    Whale sell volume: {sell_volume:.4f}")
                    logger.debug(f"    Small trade volume: {small_volume:.4f}")
                    
                    # Calculate net volume and imbalance
                    net_volume = buy_volume - sell_volume
                    total_whale_volume = buy_volume + sell_volume
                    
                    if total_whale_volume > 0:
                        trade_imbalance = net_volume / total_whale_volume
                        logger.debug(f"  Net volume: {net_volume:.4f}")
                        logger.debug(f"  Trade imbalance: {trade_imbalance:.2f}")
                
                # Print detailed info on the first few whale trades
                if whale_threshold > 0:
                    all_recent_trades = sorted(recent_trades, key=lambda t: float(t.get('amount', t.get('size', t.get('quantity', 0)))), reverse=True)
                    
                    logger.debug(f"\n  LARGEST RECENT TRADES:")
                    for i, trade in enumerate(all_recent_trades[:5]):
                        side = trade.get('side', 'unknown')
                        size = float(trade.get('amount', trade.get('size', trade.get('quantity', 0))))
                        price = float(trade.get('price', 0))
                        timestamp = trade.get('timestamp', 0)
                        time_str = time.strftime('%H:%M:%S', time.gmtime(timestamp/1000)) if timestamp else 'unknown'
                        
                        # Determine if it's considered a whale trade
                        is_whale = size >= (whale_threshold / 2)
                        whale_str = "WHALE" if is_whale else "regular"
                        
                        logger.debug(f"    {i+1}. {side.upper()} {size:.4f} @ {price} ({time_str}) - {whale_str}")
            
            logger.debug(f"=== END ENHANCED DEBUGGING ===\n")
            
            # Call the original method
            return await original_monitor_method(symbol, market_data)
        
        # Replace the monitor method with our enhanced version
        self.monitor._monitor_whale_activity = enhanced_monitor_method
        
        try:
            for exchange_id, symbols in self.symbols.items():
                for symbol in symbols:
                    try:
                        logger.info(f"Processing {symbol} on {exchange_id}")
                        
                        # Fetch market data
                        market_data = await self.fetch_market_data(exchange_id, symbol)
                        
                        if not market_data:
                            logger.warning(f"No market data available for {symbol} on {exchange_id}")
                            continue
                        
                        # Run whale activity monitoring (now with enhanced debugging)
                        await self.monitor._monitor_whale_activity(symbol, market_data)
                        
                        # Prevent rate limiting
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error processing {symbol} on {exchange_id}: {str(e)}")
                
            logger.info(f"Live tests completed. {len(self.alert_manager.alerts)} alerts generated.")
            
        finally:
            # Restore original method
            self.monitor._monitor_whale_activity = original_monitor_method
            
            # Clean up exchange connections
            for exchange_id, exchange in self.exchanges.items():
                await exchange.close()
    
    async def monitor_continuously(self, interval=60, duration=3600):
        """
        Monitor whale activity continuously for a specified duration.
        
        Args:
            interval: Seconds between checks
            duration: Total monitoring duration in seconds (default 1 hour)
        """
        logger.info(f"Starting continuous whale monitoring for {duration} seconds")
        
        # Add a wrapper for the _monitor_whale_activity method to provide more debug information
        original_monitor_method = self.monitor._monitor_whale_activity
        
        async def enhanced_monitor_method(symbol, market_data):
            """Enhanced wrapper around _monitor_whale_activity for debugging"""
            logger.debug(f"\n=== ENHANCED DEBUGGING for {symbol} ===")
            
            # Debug orderbook and trades
            if 'orderbook' in market_data:
                ob = market_data['orderbook']
                if 'bids' in ob and 'asks' in ob:
                    # Calculate standard deviation of order sizes to understand whale threshold
                    bid_sizes = [float(bid[1]) for bid in ob['bids'][:50]]
                    ask_sizes = [float(ask[1]) for ask in ob['asks'][:50]]
                    all_sizes = bid_sizes + ask_sizes
                    
                    if all_sizes:
                        mean_size = np.mean(all_sizes)
                        std_size = np.std(all_sizes)
                        whale_threshold = mean_size + (3 * std_size)
                        
                        logger.debug(f"Trade statistics:")
                        logger.debug(f"  Mean size: {mean_size:.6f}")
                        logger.debug(f"  Std dev: {std_size:.6f}")
                        logger.debug(f"  Whale threshold (mean + 3*std): {whale_threshold:.6f}")
                        
                        # Count whales in orderbook
                        whale_bids = [b for b in ob['bids'] if float(b[1]) >= whale_threshold]
                        whale_asks = [a for a in ob['asks'] if float(a[1]) >= whale_threshold]
                        
                        logger.debug(f"  Whale orders: {len(whale_bids)} bids, {len(whale_asks)} asks")
                        
                        # Log top 3 orders for both sides for comparison
                        logger.debug(f"TOP BIDS (price, size):")
                        for i, bid in enumerate(ob['bids'][:3]):
                            logger.debug(f"  {i+1}. {bid[0]}, {bid[1]}")
                            
                        logger.debug(f"TOP ASKS (price, size):")
                        for i, ask in enumerate(ob['asks'][:3]):
                            logger.debug(f"  {i+1}. {ask[0]}, {ask[1]}")
                            
            # Debug recent trades in detail
            if 'trades' in market_data and market_data['trades']:
                trades = market_data['trades']
                
                # Here we perform the same analysis that happens in _monitor_whale_activity
                # but with more detailed logging
                recent_time_threshold = time.time() - 1800  # 30 minutes
                
                logger.debug(f"\nTRADES DETAILED ANALYSIS:")
                logger.debug(f"  Analyzing {len(trades)} recent trades")
                logger.debug(f"  Time threshold: {recent_time_threshold} ({time.strftime('%H:%M:%S', time.gmtime(recent_time_threshold))} UTC)")
                
                # Categorize trades by time
                recent_trades = []
                old_trades = []
                invalid_time_trades = []
                
                for trade in trades:
                    trade_time = float(trade.get('timestamp', 0)) / 1000 if isinstance(trade.get('timestamp'), int) else 0
                    if trade_time == 0:
                        invalid_time_trades.append(trade)
                    elif trade_time < recent_time_threshold:
                        old_trades.append(trade)
                    else:
                        recent_trades.append(trade)
                
                logger.debug(f"  Trade time breakdown:")
                logger.debug(f"    Recent trades (< 30min old): {len(recent_trades)}")
                logger.debug(f"    Old trades (> 30min old): {len(old_trades)}")
                logger.debug(f"    Invalid timestamp trades: {len(invalid_time_trades)}")
                
                # Now calculate trade-based whale threshold
                whale_threshold = 0
                if 'orderbook' in market_data and 'bids' in market_data['orderbook']:
                    # Same calculation from _monitor_whale_activity
                    ob = market_data['orderbook']
                    bid_sizes = [float(bid[1]) for bid in ob['bids'][:50]]
                    ask_sizes = [float(ask[1]) for ask in ob['asks'][:50]]
                    all_sizes = bid_sizes + ask_sizes
                    
                    if all_sizes:
                        mean_size = np.mean(all_sizes)
                        std_size = np.std(all_sizes)
                        whale_threshold = mean_size + (3 * std_size)
                
                # Analyze trade sizes relative to whale threshold
                if whale_threshold > 0 and recent_trades:
                    logger.debug(f"  Whale threshold for trades: {whale_threshold/2:.4f} (50% of orderbook threshold)")
                    
                    # Count trades by size
                    whale_buy_trades = []
                    whale_sell_trades = []
                    small_trades = []
                    
                    for trade in recent_trades:
                        # Extract trade data
                        side = trade.get('side', '').lower()
                        size = float(trade.get('amount', trade.get('size', trade.get('quantity', 0))))
                        price = float(trade.get('price', 0))
                        value = size * price
                        
                        # Analyze if it's a whale trade
                        is_whale = size >= (whale_threshold / 2)
                        
                        if is_whale:
                            if side == 'buy':
                                whale_buy_trades.append((size, price, value))
                            elif side == 'sell':
                                whale_sell_trades.append((size, price, value))
                        else:
                            small_trades.append((size, price, value))
                    
                    # Log counts and volumes
                    logger.debug(f"  Trade size classification:")
                    logger.debug(f"    Whale buy trades: {len(whale_buy_trades)}")
                    logger.debug(f"    Whale sell trades: {len(whale_sell_trades)}")
                    logger.debug(f"    Small trades: {len(small_trades)}")
                    
                    # Calculate volumes
                    buy_volume = sum(t[0] for t in whale_buy_trades)
                    sell_volume = sum(t[0] for t in whale_sell_trades)
                    small_volume = sum(t[0] for t in small_trades)
                    
                    logger.debug(f"  Trade volumes:")
                    logger.debug(f"    Whale buy volume: {buy_volume:.4f}")
                    logger.debug(f"    Whale sell volume: {sell_volume:.4f}")
                    logger.debug(f"    Small trade volume: {small_volume:.4f}")
                    
                    # Calculate net volume and imbalance
                    net_volume = buy_volume - sell_volume
                    total_whale_volume = buy_volume + sell_volume
                    
                    if total_whale_volume > 0:
                        trade_imbalance = net_volume / total_whale_volume
                        logger.debug(f"  Net volume: {net_volume:.4f}")
                        logger.debug(f"  Trade imbalance: {trade_imbalance:.2f}")
                
                # Print detailed info on the first few whale trades
                if whale_threshold > 0:
                    all_recent_trades = sorted(recent_trades, key=lambda t: float(t.get('amount', t.get('size', t.get('quantity', 0)))), reverse=True)
                    
                    logger.debug(f"\n  LARGEST RECENT TRADES:")
                    for i, trade in enumerate(all_recent_trades[:5]):
                        side = trade.get('side', 'unknown')
                        size = float(trade.get('amount', trade.get('size', trade.get('quantity', 0))))
                        price = float(trade.get('price', 0))
                        timestamp = trade.get('timestamp', 0)
                        time_str = time.strftime('%H:%M:%S', time.gmtime(timestamp/1000)) if timestamp else 'unknown'
                        
                        # Determine if it's considered a whale trade
                        is_whale = size >= (whale_threshold / 2)
                        whale_str = "WHALE" if is_whale else "regular"
                        
                        logger.debug(f"    {i+1}. {side.upper()} {size:.4f} @ {price} ({time_str}) - {whale_str}")
            
            logger.debug(f"=== END ENHANCED DEBUGGING ===\n")
            
            # Call the original method
            return await original_monitor_method(symbol, market_data)
        
        # Replace the monitor method with our enhanced version
        self.monitor._monitor_whale_activity = enhanced_monitor_method
        
        start_time = time.time()
        try:
            while time.time() - start_time < duration:
                cycle_start = time.time()
                
                # Run one monitoring cycle
                for exchange_id, symbols in self.symbols.items():
                    for symbol in symbols:
                        try:
                            logger.info(f"Processing {symbol} on {exchange_id}")
                            
                            # Fetch market data
                            market_data = await self.fetch_market_data(exchange_id, symbol)
                            
                            if not market_data:
                                logger.warning(f"No market data available for {symbol} on {exchange_id}")
                                continue
                            
                            # Run whale activity monitoring with enhanced debugging
                            await self.monitor._monitor_whale_activity(symbol, market_data)
                            
                            # Prevent rate limiting
                            await asyncio.sleep(1)
                            
                        except Exception as e:
                            logger.error(f"Error processing {symbol} on {exchange_id}: {str(e)}")
                
                # Calculate time elapsed in this cycle
                cycle_time = time.time() - cycle_start
                
                # Sleep until next cycle, but not less than 5 seconds
                sleep_time = max(interval - cycle_time, 5)
                logger.info(f"Cycle completed in {cycle_time:.1f}s. Sleeping for {sleep_time:.1f}s")
                await asyncio.sleep(sleep_time)
                
            logger.info(f"Continuous monitoring completed. {len(self.alert_manager.alerts)} alerts generated.")
            
        finally:
            # Restore original method
            self.monitor._monitor_whale_activity = original_monitor_method
            
            # Clean up exchange connections
            for exchange_id, exchange in self.exchanges.items():
                await exchange.close()

async def main():
    """Main function to run the live tests."""
    test = LiveWhaleTest()
    
    # Choose the test mode based on command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        # Get optional duration parameter (default 1 hour)
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 3600
        await test.monitor_continuously(interval=60, duration=duration)
    else:
        # Run a single test cycle
        await test.run_live_test()

if __name__ == "__main__":
    asyncio.run(main()) 