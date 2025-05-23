#!/usr/bin/env python3
"""
Test script for the enhanced whale activity monitoring.

This script creates synthetic market data with known whale patterns in both 
orderbook and trades data, then calls the whale monitoring code to test alert generation.
"""

import asyncio
import logging
import sys
import os
import time
import random
from typing import Dict, Any, List
from decimal import Decimal

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import required modules
from src.monitoring.alert_manager import AlertManager
from src.monitoring.monitor import MarketMonitor
from src.monitoring.metrics_manager import MetricsManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("whale_test")

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

class TestWhaleAlerts:
    """Test class for whale activity monitoring."""
    
    def __init__(self):
        """Initialize the test class."""
        self.alert_manager = MockAlertManager()
        
        # Create a minimal config for metrics manager
        config = {
            'metrics': {
                'enabled': True,
                'interval': 60
            }
        }
        
        # Initialize metrics manager with required parameters
        self.metrics_manager = MetricsManager(
            config=config,
            alert_manager=self.alert_manager
        )
        
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
        
        # Configure whale activity monitoring
        self.monitor.whale_activity_config = {
            'enabled': True,
            'accumulation_threshold': 100000,  # $100k threshold for testing
            'distribution_threshold': 100000,  # $100k threshold for testing
            'cooldown': 0,                     # No cooldown for testing
            'imbalance_threshold': 0.2,        # 20% order book imbalance threshold
            'min_order_count': 3,              # Minimum number of whale orders
            'market_percentage': 0.02,         # 2% of market to be considered significant
        }
        
        # Initialize tracking dict
        self.monitor._last_whale_alert = {}
        self.monitor._last_whale_activity = {}
        
    def create_accumulation_market_data(self, symbol="BTCUSDT", with_trades=True) -> Dict[str, Any]:
        """Create synthetic market data showing accumulation pattern."""
        current_time = time.time()
        current_price = 50000.0  # Example BTC price
        
        # Create orderbook with whale bids (accumulation pattern)
        bids = []
        asks = []
        
        # Regular bids
        for i in range(20):
            price = current_price - (i * 10)
            size = random.uniform(0.1, 0.5)  # Regular sizes
            bids.append([price, size])
        
        # Add whale bids (large buy orders)
        whale_sizes = [5.0, 4.8, 6.2, 4.5, 5.5]  # Large sizes
        for i, size in enumerate(whale_sizes):
            price = current_price - (i * 5)
            bids.insert(i, [price, size])
        
        # Regular asks
        for i in range(20):
            price = current_price + (i * 10)
            size = random.uniform(0.1, 0.5)  # Regular sizes
            asks.append([price, size])
        
        # Sort bids (descending) and asks (ascending)
        bids.sort(key=lambda x: float(x[0]), reverse=True)
        asks.sort(key=lambda x: float(x[0]))
        
        # Create orderbook structure
        orderbook = {
            'bids': bids,
            'asks': asks,
            'timestamp': int(current_time * 1000)
        }
        
        # Create ticker data
        ticker = {
            'symbol': symbol,
            'last': current_price,
            'bid': bids[0][0] if bids else current_price - 10,
            'ask': asks[0][0] if asks else current_price + 10,
            'volume': 1000.0,
            'timestamp': int(current_time * 1000)
        }
        
        # Create market data structure
        market_data = {
            'symbol': symbol,
            'timestamp': int(current_time * 1000),
            'orderbook': orderbook,
            'ticker': ticker
        }
        
        # Add trades data if requested
        if with_trades:
            trades = []
            
            # Create confirming trades (mostly buys)
            for i in range(30):
                # 80% buys, 20% sells for confirmation
                side = "buy" if random.random() < 0.8 else "sell"
                
                # Create some large (whale) trades among regular ones
                is_whale = random.random() < 0.3
                size = random.uniform(2.0, 8.0) if is_whale else random.uniform(0.1, 0.5)
                
                trade = {
                    'id': str(i),
                    'timestamp': int((current_time - random.uniform(0, 1800)) * 1000),  # Last 30 min
                    'side': side,
                    'price': current_price * random.uniform(0.99, 1.01),
                    'amount': size,
                    'cost': size * current_price
                }
                trades.append(trade)
            
            market_data['trades'] = trades
        
        return market_data
    
    def create_distribution_market_data(self, symbol="BTCUSDT", with_trades=True) -> Dict[str, Any]:
        """Create synthetic market data showing distribution pattern."""
        current_time = time.time()
        current_price = 50000.0  # Example BTC price
        
        # Create orderbook with whale asks (distribution pattern)
        bids = []
        asks = []
        
        # Regular bids
        for i in range(20):
            price = current_price - (i * 10)
            size = random.uniform(0.1, 0.5)  # Regular sizes
            bids.append([price, size])
        
        # Regular asks
        for i in range(20):
            price = current_price + (i * 10)
            size = random.uniform(0.1, 0.5)  # Regular sizes
            asks.append([price, size])
            
        # Add whale asks (large sell orders)
        whale_sizes = [5.0, 4.8, 6.2, 4.5, 5.5]  # Large sizes
        for i, size in enumerate(whale_sizes):
            price = current_price + (i * 5)
            asks.insert(i, [price, size])
        
        # Sort bids (descending) and asks (ascending)
        bids.sort(key=lambda x: float(x[0]), reverse=True)
        asks.sort(key=lambda x: float(x[0]))
        
        # Create orderbook structure
        orderbook = {
            'bids': bids,
            'asks': asks,
            'timestamp': int(current_time * 1000)
        }
        
        # Create ticker data
        ticker = {
            'symbol': symbol,
            'last': current_price,
            'bid': bids[0][0] if bids else current_price - 10,
            'ask': asks[0][0] if asks else current_price + 10,
            'volume': 1000.0,
            'timestamp': int(current_time * 1000)
        }
        
        # Create market data structure
        market_data = {
            'symbol': symbol,
            'timestamp': int(current_time * 1000),
            'orderbook': orderbook,
            'ticker': ticker
        }
        
        # Add trades data if requested
        if with_trades:
            trades = []
            
            # Create confirming trades (mostly sells)
            for i in range(30):
                # 80% sells, 20% buys for confirmation
                side = "sell" if random.random() < 0.8 else "buy"
                
                # Create some large (whale) trades among regular ones
                is_whale = random.random() < 0.3
                size = random.uniform(2.0, 8.0) if is_whale else random.uniform(0.1, 0.5)
                
                trade = {
                    'id': str(i),
                    'timestamp': int((current_time - random.uniform(0, 1800)) * 1000),  # Last 30 min
                    'side': side,
                    'price': current_price * random.uniform(0.99, 1.01),
                    'amount': size,
                    'cost': size * current_price
                }
                trades.append(trade)
            
            market_data['trades'] = trades
        
        return market_data
    
    def create_contradicting_market_data(self, symbol="BTCUSDT") -> Dict[str, Any]:
        """Create synthetic market data where orderbook and trades contradict each other."""
        # Start with accumulation orderbook
        market_data = self.create_accumulation_market_data(symbol, with_trades=False)
        
        # But add contradicting trades (mostly sells)
        current_time = time.time()
        current_price = 50000.0
        trades = []
        
        for i in range(30):
            # 80% sells, 20% buys (contradicting the accumulation in orderbook)
            side = "sell" if random.random() < 0.8 else "buy"
            
            # Create some large (whale) trades among regular ones
            is_whale = random.random() < 0.3
            size = random.uniform(2.0, 8.0) if is_whale else random.uniform(0.1, 0.5)
            
            trade = {
                'id': str(i),
                'timestamp': int((current_time - random.uniform(0, 1800)) * 1000),  # Last 30 min
                'side': side,
                'price': current_price * random.uniform(0.99, 1.01),
                'amount': size,
                'cost': size * current_price
            }
            trades.append(trade)
        
        market_data['trades'] = trades
        return market_data
    
    async def run_tests(self):
        """Run all the whale activity tests."""
        logger.info("Starting whale activity monitoring tests")
        
        # Test 1: Accumulation with confirming trades
        logger.info("\nTEST 1: ACCUMULATION WITH CONFIRMING TRADES")
        market_data = self.create_accumulation_market_data("BTCUSDT")
        await self.monitor._monitor_whale_activity("BTCUSDT", market_data)
        
        # Test 2: Distribution with confirming trades
        logger.info("\nTEST 2: DISTRIBUTION WITH CONFIRMING TRADES")
        market_data = self.create_distribution_market_data("ETHUSDT")
        await self.monitor._monitor_whale_activity("ETHUSDT", market_data)
        
        # Test 3: Accumulation in orderbook with contradicting trades
        logger.info("\nTEST 3: CONTRADICTING SIGNALS")
        market_data = self.create_contradicting_market_data("SOLUSDT")
        await self.monitor._monitor_whale_activity("SOLUSDT", market_data)
        
        # Test 4: Orderbook-only (no trades)
        logger.info("\nTEST 4: ORDERBOOK-ONLY (NO TRADES)")
        market_data = self.create_accumulation_market_data("DOGEUSDT", with_trades=False)
        await self.monitor._monitor_whale_activity("DOGEUSDT", market_data)
        
        logger.info(f"\nTests completed. {len(self.alert_manager.alerts)} alerts generated.")

async def main():
    """Main function to run the tests."""
    test = TestWhaleAlerts()
    await test.run_tests()

if __name__ == "__main__":
    asyncio.run(main()) 