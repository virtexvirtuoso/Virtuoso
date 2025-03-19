#!/usr/bin/env python3
"""
Test script for the hybrid WebSocket + REST API implementation in MarketMonitor.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List
import pandas as pd
import sys
import os
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger('hybrid_test')

# Import components (make sure they're in your Python path)
try:
    from src.core.market.market_data_manager import MarketDataManager
    from src.core.exchanges.websocket_manager import WebSocketManager
    from src.core.exchanges.rate_limiter import BybitRateLimiter
    from src.monitoring.monitor import MarketMonitor
except ImportError as e:
    logger.error(f"Import error: {e}. Please make sure all required modules are in your Python path.")
    sys.exit(1)

# Test configuration
TEST_CONFIG = {
    "system": {
        "version": "1.0.0",
        "environment": "testing",
        "log_level": "DEBUG"
    },
    "exchanges": {
        "bybit": {
            "name": "bybit",
            "enabled": True,
            "testnet": False,
            "rest_endpoint": "https://api.bybit.com",
            "websocket": {
                "enabled": True,
                "mainnet_endpoint": "wss://stream.bybit.com/v5/public",
                "testnet_endpoint": "wss://stream-testnet.bybit.com/v5/public"
            },
            "api_credentials": {
                "api_key": "your_api_key",  # Replace with your API key if needed
                "api_secret": "your_api_secret"  # Replace with your API secret if needed
            }
        }
    },
    "analysis": {
        "weights": {
            "technical": 0.3,
            "orderflow": 0.2,
            "sentiment": 0.2,
            "orderbook": 0.15,
            "price_structure": 0.15
        },
        "indicators": {
            "strength_threshold": 0.5,
            "min_reliability": 0.6,
            "log_level": "DEBUG",
            "debug_mode": True
        },
        "confluence_thresholds": {
            "buy": 70,
            "sell": 30
        }
    },
    "monitoring": {
        "interval": 30,  # 30 seconds between monitoring cycles
        "summary_interval": 3600,  # 1 hour between summaries
        "symbols_to_monitor": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
    }
}

class MockExchangeManager:
    """Simple mock of the ExchangeManager for testing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('mock_exchange_manager')
    
    async def get_primary_exchange(self):
        """Get primary exchange (returns self for testing)"""
        return self
    
    async def initialize(self):
        """Initialize the exchange manager"""
        self.logger.info("Initialized mock exchange manager")
    
    async def fetch_ticker(self, symbol: str):
        """Mock method to fetch ticker data"""
        self.logger.info(f"Fetching ticker for {symbol}")
        # Return a mock response matching Bybit format
        return {
            "symbol": symbol,
            "lastPrice": "60000.00" if symbol == "BTCUSDT" else "3000.00",
            "indexPrice": "60050.00" if symbol == "BTCUSDT" else "3010.00",
            "markPrice": "60020.00" if symbol == "BTCUSDT" else "3005.00",
            "prevPrice24h": "58000.00" if symbol == "BTCUSDT" else "2900.00",
            "price24hPcnt": "0.034" if symbol == "BTCUSDT" else "0.034",
            "highPrice24h": "61000.00" if symbol == "BTCUSDT" else "3100.00",
            "lowPrice24h": "57000.00" if symbol == "BTCUSDT" else "2800.00",
            "prevPrice1h": "59800.00" if symbol == "BTCUSDT" else "2980.00",
            "openInterest": "100000000",
            "openInterestValue": "6000000000",
            "turnover24h": "5000000000",
            "volume24h": "80000",
            "fundingRate": "0.0001",
            "nextFundingTime": str(int(time.time() * 1000) + 3600000),
            "bid1Price": "59990.00" if symbol == "BTCUSDT" else "2999.00",
            "bid1Size": "1.5",
            "ask1Price": "60010.00" if symbol == "BTCUSDT" else "3001.00",
            "ask1Size": "2.0"
        }
    
    async def fetch_orderbook(self, symbol: str, limit: int = 50):
        """Mock method to fetch orderbook data"""
        self.logger.info(f"Fetching orderbook for {symbol} with limit {limit}")
        # Create mock bids and asks
        bids = [[float(59990) - i*10, 1.0/(i+1)] for i in range(limit)]
        asks = [[float(60010) + i*10, 1.0/(i+1)] for i in range(limit)]
        
        return {
            "symbol": symbol,
            "bids": bids,
            "asks": asks,
            "timestamp": int(time.time() * 1000),
            "datetime": pd.Timestamp.now().isoformat()
        }
    
    async def fetch_trades(self, symbol: str, limit: int = 100):
        """Mock method to fetch recent trades"""
        self.logger.info(f"Fetching trades for {symbol} with limit {limit}")
        # Create mock trades
        trades = []
        current_time = int(time.time() * 1000)
        
        for i in range(limit):
            price = 60000 + (i % 10) * 5 - 25
            amount = 0.1 + (i % 5) * 0.1
            side = "buy" if i % 2 == 0 else "sell"
            
            trades.append({
                "id": f"trade_{current_time}_{i}",
                "price": price,
                "amount": amount,
                "cost": price * amount,
                "side": side,
                "timestamp": current_time - i * 1000,
                "datetime": pd.Timestamp(current_time - i * 1000, unit='ms').isoformat(),
                "symbol": symbol,
                "taker_or_maker": "taker"
            })
        
        return trades
    
    async def fetch_ohlcv(self, symbol: str, interval: str, limit: int = 200):
        """Mock method to fetch OHLCV data"""
        self.logger.info(f"Fetching OHLCV for {symbol} with interval {interval} and limit {limit}")
        
        # Convert interval to minutes
        interval_minutes = {
            '1': 1,
            '5': 5,
            '30': 30,
            '240': 240
        }.get(interval, 1)
        
        # Generate mock OHLCV data
        interval_ms = interval_minutes * 60 * 1000
        current_time = int(time.time() * 1000)
        
        # Ensure current time is aligned to interval
        current_time = current_time - (current_time % interval_ms)
        
        candles = []
        base_price = 60000 if symbol == "BTCUSDT" else 3000
        
        for i in range(limit):
            timestamp = current_time - (i * interval_ms)
            open_price = base_price - (i % 20) * 10
            close_price = open_price + ((i % 10) - 5) * 10
            high_price = max(open_price, close_price) + (i % 10) * 2
            low_price = min(open_price, close_price) - (i % 10) * 2
            volume = 10 + (i % 100)
            
            candles.append({
                "timestamp": timestamp,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume
            })
        
        # Sort by timestamp (oldest first)
        candles.sort(key=lambda x: x["timestamp"])
        
        # Convert to DataFrame
        df = pd.DataFrame(candles)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Return in format expected by the market data manager
        return {
            "result": {
                "symbol": symbol,
                "list": [[
                    str(int(pd.Timestamp(row.name).timestamp() * 1000)),
                    str(row['open']),
                    str(row['high']),
                    str(row['low']),
                    str(row['close']),
                    str(row['volume']),
                    str(row['volume'] * row['close'])  # Turnover
                ] for _, row in df.iterrows()]
            }
        }
    
    async def fetch_long_short_ratio(self, symbol: str):
        """Mock method to fetch long/short ratio"""
        self.logger.info(f"Fetching long/short ratio for {symbol}")
        return {
            "symbol": symbol,
            "buyRatio": "0.65",
            "sellRatio": "0.35",
            "timestamp": str(int(time.time() * 1000))
        }
    
    async def fetch_risk_limits(self, symbol: str):
        """Mock method to fetch risk limits"""
        self.logger.info(f"Fetching risk limits for {symbol}")
        return {
            "riskLimitValue": "2000000",
            "maintenanceMargin": "0.005",
            "initialMargin": "0.01",
            "maxLeverage": "100.00"
        }
    
    async def ping(self):
        """Mock ping method"""
        return True
    
    async def close(self):
        """Close the exchange manager"""
        self.logger.info("Closed mock exchange manager")

class MockDatabase:
    """Mock database client for testing"""
    
    def __init__(self):
        self.logger = logging.getLogger('mock_database')
        self.stored_data = []
    
    async def initialize(self):
        """Initialize the database"""
        self.logger.info("Initialized mock database")
    
    async def store_analysis(self, symbol: str, analysis: Dict[str, Any], signals: List[Dict[str, Any]] = None):
        """Store analysis results"""
        self.logger.info(f"Storing analysis for {symbol} with {len(signals or [])} signals")
        self.stored_data.append({
            'symbol': symbol,
            'analysis': analysis,
            'signals': signals or [],
            'timestamp': pd.Timestamp.now().isoformat()
        })
    
    async def close(self):
        """Close the database connection"""
        self.logger.info("Closed mock database")
        
        # Print stored data summary
        self.logger.info(f"Stored {len(self.stored_data)} analysis records")

class MockConfluenceAnalyzer:
    """Mock confluence analyzer for testing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('mock_confluence_analyzer')
    
    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock analysis method"""
        symbol = market_data.get('symbol', 'unknown')
        self.logger.info(f"Analyzing market data for {symbol}")
        
        # Create mock analysis result
        components = {
            'technical': 65 + (hash(symbol) % 20),
            'orderflow': 60 + (hash(symbol[::-1]) % 25),
            'sentiment': 45 + (hash(symbol + 'sentiment') % 30),
            'orderbook': 55 + (hash(symbol + 'orderbook') % 20),
            'price_structure': 70 + (hash(symbol + 'structure') % 15)
        }
        
        # Calculate overall score
        weights = self.config.get('analysis', {}).get('weights', {})
        overall_score = sum(
            components.get(component, 50) * weights.get(component, 0.2)
            for component in components
        )
        
        return {
            'symbol': symbol,
            'score': overall_score,
            'reliability': 0.8,
            'components': components,
            'metadata': {
                'timestamp': pd.Timestamp.now().isoformat(),
                'analysis_time_ms': 120
            }
        }

class MockSignalGenerator:
    """Mock signal generator for testing"""
    
    def __init__(self):
        self.logger = logging.getLogger('mock_signal_generator')
        self.signals = []
    
    async def process_signal(self, signal_data: Dict[str, Any]):
        """Process a signal"""
        self.logger.info(f"Processing signal for {signal_data.get('symbol')}: {signal_data.get('direction', 'unknown')}")
        self.signals.append(signal_data)
    
    async def generate_signals(self, symbol: str, market_data: Dict[str, Any], analysis: Dict[str, Any]):
        """Generate signals based on analysis"""
        self.logger.info(f"Generating signals for {symbol}")
        score = analysis.get('score', 50)
        
        if score >= 70:
            signal = {
                'symbol': symbol,
                'direction': 'buy',
                'score': score,
                'timestamp': pd.Timestamp.now().isoformat()
            }
            self.signals.append(signal)
            return [signal]
        elif score <= 30:
            signal = {
                'symbol': symbol,
                'direction': 'sell',
                'score': score,
                'timestamp': pd.Timestamp.now().isoformat()
            }
            self.signals.append(signal)
            return [signal]
        else:
            return []

async def test_market_data_manager():
    """Test the MarketDataManager directly"""
    logger.info("=== Testing MarketDataManager ===")
    
    # Create mock exchange manager
    exchange_manager = MockExchangeManager(TEST_CONFIG)
    
    # Create market data manager
    market_data_manager = MarketDataManager(TEST_CONFIG, exchange_manager)
    
    # Initialize with test symbols
    symbols = TEST_CONFIG['monitoring']['symbols_to_monitor']
    logger.info(f"Initializing MarketDataManager with symbols: {symbols}")
    await market_data_manager.initialize(symbols)
    
    # Start monitoring
    logger.info("Starting market data monitoring")
    await market_data_manager.start_monitoring()
    
    # Wait a bit for initial data to be fetched
    logger.info("Waiting for initial data to be fetched...")
    await asyncio.sleep(5)
    
    # Get market data for a symbol
    symbol = symbols[0]
    logger.info(f"Fetching market data for {symbol}")
    market_data = await market_data_manager.get_market_data(symbol)
    
    # Print summary of the fetched data
    if market_data:
        logger.info(f"Successfully fetched market data for {symbol}")
        
        # Log ticker data
        if 'ticker' in market_data and market_data['ticker']:
            ticker = market_data['ticker']
            logger.info(f"Ticker: Last Price = {ticker.get('lastPrice')}, 24h Change = {ticker.get('price24hPcnt')}")
        
        # Log orderbook depth
        if 'orderbook' in market_data and market_data['orderbook']:
            orderbook = market_data['orderbook']
            logger.info(f"Orderbook: {len(orderbook.get('bids', []))} bids, {len(orderbook.get('asks', []))} asks")
        
        # Log OHLCV data
        if 'kline' in market_data:
            for tf_name, tf_data in market_data['kline'].items():
                if tf_data and 'data' in tf_data and isinstance(tf_data['data'], pd.DataFrame):
                    df = tf_data['data']
                    logger.info(f"OHLCV {tf_name}: {len(df)} candles, last close = {df['close'].iloc[-1] if not df.empty else 'N/A'}")
    else:
        logger.error(f"Failed to fetch market data for {symbol}")
    
    # Get stats
    stats = market_data_manager.get_stats()
    logger.info(f"MarketDataManager stats: {json.dumps(stats, default=str)}")
    
    # Wait for WebSocket updates
    logger.info("Waiting for WebSocket updates (10s)...")
    await asyncio.sleep(10)
    
    # Get updated market data
    logger.info(f"Fetching updated market data for {symbol}")
    updated_market_data = await market_data_manager.get_market_data(symbol)
    
    # Check if we got WebSocket updates
    if updated_market_data:
        # Get updated stats
        updated_stats = market_data_manager.get_stats()
        ws_updates = updated_stats.get('websocket_updates', 0)
        logger.info(f"Received {ws_updates} WebSocket updates")
    
    # Stop the market data manager
    logger.info("Stopping MarketDataManager")
    await market_data_manager.stop()
    
    logger.info("MarketDataManager test completed")

async def test_market_monitor():
    """Test the MarketMonitor with the hybrid data fetching architecture"""
    logger.info("=== Testing MarketMonitor with Hybrid Architecture ===")
    
    # Create mock components
    exchange_manager = MockExchangeManager(TEST_CONFIG)
    database = MockDatabase()
    confluence_analyzer = MockConfluenceAnalyzer(TEST_CONFIG)
    signal_generator = MockSignalGenerator()
    
    # Create market monitor
    monitor = MarketMonitor(
        logger=logging.getLogger('test_market_monitor')
    )
    
    # Set attributes directly
    monitor.exchange_manager = exchange_manager
    monitor.database_client = database
    monitor.portfolio_analyzer = None  # Not needed for this test
    monitor.confluence_analyzer = confluence_analyzer
    monitor.config = TEST_CONFIG
    monitor.signal_generator = signal_generator
    
    # Start the monitor
    logger.info("Starting MarketMonitor")
    await monitor.start()
    
    # Wait for monitoring cycles
    logger.info("Waiting for monitoring cycles (30s)...")
    await asyncio.sleep(30)
    
    # Get monitor stats
    stats = monitor.stats
    logger.info(f"MarketMonitor stats: {json.dumps(stats, default=str)}")
    
    # Check signals generated
    logger.info(f"Generated signals: {len(signal_generator.signals)}")
    for signal in signal_generator.signals:
        logger.info(f"Signal for {signal.get('symbol')}: {signal.get('direction')} (score: {signal.get('confluence_score', signal.get('score', 0)):.1f})")
    
    # Stop the monitor
    logger.info("Stopping MarketMonitor")
    await monitor.stop()
    
    logger.info("MarketMonitor test completed")

async def main():
    """Main test function"""
    logger.info("Starting hybrid WebSocket + REST API architecture test")
    
    # Test MarketDataManager directly
    await test_market_data_manager()
    
    # Test MarketMonitor with hybrid architecture
    await test_market_monitor()
    
    logger.info("All tests completed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Error in test: {e}")
        import traceback
        traceback.print_exc() 