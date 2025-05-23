#!/usr/bin/env python3
"""
Test script for standalone trade-based whale activity monitoring.

This script demonstrates and tests a dedicated whale alert system based solely on
analyzing trade patterns, independent of orderbook data.
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
import ccxt.async_support as ccxt

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("trade_whale_test")

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

class TradeWhaleMonitor:
    """
    Standalone trade-based whale activity monitor.
    
    This class analyzes trade patterns to detect significant whale activity
    and generates alerts when large trading patterns are detected.
    """
    
    def __init__(self, alert_manager=None):
        """Initialize the trade whale monitor."""
        self.alert_manager = alert_manager or MockAlertManager()
        self.logger = logger
        
        # Configure whale activity monitoring with higher thresholds to reduce noise
        self.whale_activity_config = {
            'trade_alerts_enabled': True,
            'trade_cooldown': 900,         # ↑ Increased to 15 minutes (from 5)
            'min_whale_trades': 5,         # ↑ Increased from 3 to 5 trades
            'min_trade_volume_usd': 500000,# ↑ Increased from 100k to 500k
            'min_trade_imbalance': 0.75,   # ↑ Increased from 0.6 to 0.75 (75% imbalance)
        }
        
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
        
        # Define symbols to monitor
        self.symbols = {
            'bybit': ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT'],
            'binance': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],
        }
        
        # Initialize last alert tracking
        self._last_whale_alert = {}
        
    async def monitor_trade_whale_activity(self, symbol: str, market_data: Dict[str, Any]) -> None:
        """
        Monitor trades for significant whale activity and generate dedicated alerts.
        
        This method analyzes recent trades to detect large trade patterns
        and sends alerts when thresholds are crossed.
        
        Args:
            symbol: Trading pair symbol
            market_data: Market data dictionary containing trades information
        """
        try:
            # Skip if disabled in config or no alert manager
            if not self.whale_activity_config.get('trade_alerts_enabled', True):
                return
                
            if not self.alert_manager:
                self.logger.debug(f"Skipping trade whale activity monitoring for {symbol}: No alert manager")
                return
                
            # Check cooldown period
            current_time = time.time()
            last_alert_key = f"{symbol}_trade"
            last_alert_time = self._last_whale_alert.get(last_alert_key, 0)
            cooldown_period = self.whale_activity_config.get('trade_cooldown', 600)  # 10 min default
            
            if current_time - last_alert_time < cooldown_period:
                self.logger.debug(f"Skipping trade whale alert for {symbol}: In cooldown period")
                return
        
            # Extract trades data
            trades = market_data.get('trades', [])
            if not trades or not isinstance(trades, list):
                self.logger.debug(f"No valid trades data for {symbol}")
                return
                
            # Get ticker for price information
            ticker = market_data.get('ticker', {})
            current_price = float(ticker.get('last', 0))
            if not current_price:
                self.logger.debug(f"No price information for {symbol}")
                return
        
            # Calculate whale threshold for trades
            # We can derive this from statistical analysis of recent trades
            trade_sizes = [float(t.get('amount', t.get('size', t.get('quantity', 0)))) for t in trades]
            if not trade_sizes:
                self.logger.debug(f"No valid trade sizes for {symbol}")
                return
                
            mean_size = np.mean(trade_sizes)
            std_size = np.std(trade_sizes)
            whale_threshold = mean_size + (3 * std_size)  # ↑ Changed from 2 to 3 std deviations
            
            # Define recent trades timeframe (last 15 minutes)
            recent_time_threshold = current_time - 900
            
            # Identify and analyze whale trades
            whale_trades = []
            buy_volume = 0
            sell_volume = 0
            
            for trade in trades:
                # Skip old trades
                trade_time = float(trade.get('timestamp', 0)) / 1000 if isinstance(trade.get('timestamp'), int) else 0
                if trade_time < recent_time_threshold:
                    continue
                    
                # Extract trade data
                side = trade.get('side', '').lower()
                size = float(trade.get('amount', trade.get('size', trade.get('quantity', 0))))
                price = float(trade.get('price', 0))
                value = size * price
                
                # Check if it's a whale trade
                if size >= whale_threshold:
                    whale_trades.append({
                        'side': side,
                        'size': size,
                        'price': price,
                        'value': value,
                        'time': trade_time
                    })
                    
                    # Accumulate volumes
                    if side == 'buy':
                        buy_volume += size
                    elif side == 'sell':
                        sell_volume += size
            
            # Calculate trade metrics
            total_whale_volume = buy_volume + sell_volume
            net_volume = buy_volume - sell_volume
            
            if total_whale_volume > 0:
                trade_imbalance = net_volume / total_whale_volume
            else:
                trade_imbalance = 0
                
            # Add debug logging for monitoring metrics
            self.logger.debug(f"Trade whale activity for {symbol}: " +
                             f"Whale trades: {len(whale_trades)}, " +
                             f"Buy volume: {buy_volume:.2f}, Sell volume: {sell_volume:.2f}, " +
                             f"Net volume: {net_volume:.2f}, Imbalance: {trade_imbalance:.2f}")
                
            # Get thresholds from config
            min_whale_trades = self.whale_activity_config.get('min_whale_trades', 3)
            min_trade_volume_usd = self.whale_activity_config.get('min_trade_volume_usd', 500000)
            min_trade_imbalance = self.whale_activity_config.get('min_trade_imbalance', 0.6)
            
            # Calculate USD values
            buy_usd = buy_volume * current_price
            sell_usd = sell_volume * current_price
            net_usd = net_volume * current_price
            
            # Detect significant buying activity
            significant_buying = (
                len(whale_trades) >= min_whale_trades and
                buy_usd >= min_trade_volume_usd and
                trade_imbalance >= min_trade_imbalance
            )
            
            # Detect significant selling activity
            significant_selling = (
                len(whale_trades) >= min_whale_trades and
                sell_usd >= min_trade_volume_usd and
                trade_imbalance <= -min_trade_imbalance
            )
            
            # Print analysis details for visibility in tests
            self.logger.info(f"ANALYSIS - {symbol}: " +
                           f"{len(whale_trades)} whale trades, " +
                           f"Buy: ${buy_usd:.2f}, Sell: ${sell_usd:.2f}, " + 
                           f"Imbalance: {trade_imbalance:.2f}, " +
                           f"Threshold: {whale_threshold:.6f}")
            
            # Generate alerts for significant trade activity
            if significant_buying:
                message = (
                    f"🚨 **Whale Trade Alert - Large Buying** for {symbol}\n"
                    f"• {len(whale_trades)} large trades detected in last 15 minutes\n"
                    f"• Buy volume: {buy_volume:.2f} units (${buy_usd:,.2f})\n"
                    f"• Sell volume: {sell_volume:.2f} units (${sell_usd:,.2f})\n"
                    f"• Net buying: ${abs(net_usd):,.2f} ({trade_imbalance*100:.1f}% imbalance)\n"
                    f"• Current price: ${current_price:,.2f}"
                )
                
                await self.alert_manager.send_alert(
                    level="info",
                    message=message,
                    details={
                        "type": "whale_trades",
                        "subtype": "buying",
                        "symbol": symbol,
                        "data": {
                            "whale_trades_count": len(whale_trades),
                            "whale_buy_volume": buy_volume,
                            "whale_sell_volume": sell_volume,
                            "net_volume": net_volume,
                            "trade_imbalance": trade_imbalance,
                            "whale_threshold": whale_threshold
                        }
                    }
                )
                
                # Update last alert time
                self._last_whale_alert[last_alert_key] = current_time
                self.logger.info(f"Sent whale trade buying alert for {symbol}: ${abs(net_usd):,.2f}")
                
            elif significant_selling:
                message = (
                    f"🚨 **Whale Trade Alert - Large Selling** for {symbol}\n"
                    f"• {len(whale_trades)} large trades detected in last 15 minutes\n" 
                    f"• Sell volume: {sell_volume:.2f} units (${sell_usd:,.2f})\n"
                    f"• Buy volume: {buy_volume:.2f} units (${buy_usd:,.2f})\n"
                    f"• Net selling: ${abs(net_usd):,.2f} ({abs(trade_imbalance)*100:.1f}% imbalance)\n"
                    f"• Current price: ${current_price:,.2f}"
                )
                
                await self.alert_manager.send_alert(
                    level="info",
                    message=message,
                    details={
                        "type": "whale_trades",
                        "subtype": "selling",
                        "symbol": symbol,
                        "data": {
                            "whale_trades_count": len(whale_trades),
                            "whale_buy_volume": buy_volume,
                            "whale_sell_volume": sell_volume,
                            "net_volume": net_volume,
                            "trade_imbalance": trade_imbalance,
                            "whale_threshold": whale_threshold
                        }
                    }
                )
                
                # Update last alert time
                self._last_whale_alert[last_alert_key] = current_time
                self.logger.info(f"Sent whale trade selling alert for {symbol}: ${abs(net_usd):,.2f}")
                
        except Exception as e:
            self.logger.error(f"Error monitoring trade whale activity for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    async def fetch_market_data(self, exchange_id, symbol):
        """Fetch live market data for a symbol."""
        logger.info(f"Fetching market data for {symbol} from {exchange_id}")
        exchange = self.exchanges[exchange_id]
        
        try:
            # Fetch trades (primary data source for this monitor)
            trades = await exchange.fetch_trades(symbol, limit=100)
            
            # Fetch ticker for price information
            ticker = await exchange.fetch_ticker(symbol)
            
            # Enhanced trade debugging
            if trades and len(trades) > 0:
                logger.debug(f"=== TRADE DATA SAMPLE for {symbol} ===")
                logger.debug(f"Total trades fetched: {len(trades)}")
                
                # Print sample of first trade
                logger.debug(f"Sample trade: {trades[0]}")
                
                # Extract sizes for whale threshold calculation
                sizes = [float(t.get('amount', t.get('size', 0))) for t in trades]
                if sizes:
                    mean_size = np.mean(sizes)
                    std_size = np.std(sizes)
                    whale_threshold = mean_size + (3 * std_size)
                    
                    logger.debug(f"Trade statistics:")
                    logger.debug(f"  Mean size: {mean_size:.6f}")
                    logger.debug(f"  Std dev: {std_size:.6f}")
                    logger.debug(f"  Whale threshold (mean + 3*std): {whale_threshold:.6f}")
                    
                    # Count trades above threshold
                    whale_count = sum(1 for size in sizes if size >= whale_threshold)
                    logger.debug(f"  Trades above threshold: {whale_count}/{len(sizes)}")
            
            # Create market data structure
            market_data = {
                'symbol': symbol,
                'trades': trades,
                'ticker': ticker
            }
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error fetching market data: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    async def run_test(self, duration=60):
        """Run the trade whale monitor test for the specified duration."""
        try:
            start_time = time.time()
            logger.info(f"Starting trade whale activity test for {duration} seconds")
            
            while time.time() - start_time < duration:
                cycle_start = time.time()
                
                # Process all configured symbols
                for exchange_id, symbols in self.symbols.items():
                    for symbol in symbols:
                        try:
                            # Fetch market data
                            market_data = await self.fetch_market_data(exchange_id, symbol)
                            if not market_data:
                                logger.warning(f"No market data for {symbol} on {exchange_id}")
                                continue
                                
                            # Monitor trade-based whale activity
                            await self.monitor_trade_whale_activity(symbol, market_data)
                            
                            # Prevent rate limiting
                            await asyncio.sleep(1)
                            
                        except Exception as e:
                            logger.error(f"Error processing {symbol}: {str(e)}")
                
                # Calculate elapsed time and sleep until next cycle
                elapsed = time.time() - cycle_start
                sleep_time = max(10 - elapsed, 1)  # Minimum 1 second, target 10-second cycles
                logger.info(f"Cycle completed in {elapsed:.2f}s, sleeping for {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
            
            logger.info(f"Test completed. {len(self.alert_manager.alerts)} alerts generated.")
        
        finally:
            # Close exchange connections
            for exchange in self.exchanges.values():
                await exchange.close()

async def main():
    """Main function to run the test."""
    # Use command-line argument for duration if provided, default to 60 seconds
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    
    # Create and run the trade whale monitor
    monitor = TradeWhaleMonitor()
    await monitor.run_test(duration)

if __name__ == "__main__":
    asyncio.run(main()) 