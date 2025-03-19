import logging
import pandas as pd
import numpy as np
import asyncio
import os
import sys
from datetime import datetime, timedelta
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_data_flow")

# Import necessary modules
try:
    from src.monitoring.monitor import MarketMonitor
    from src.indicators.technical_indicators import TechnicalIndicators
    logger.info("Successfully imported required modules")
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    exit(1)

# Create basic configuration for testing
def create_test_config():
    """Create a minimal configuration for testing"""
    config = {
        'exchange': {
            'name': 'binance',
            'key': '',
            'secret': '',
            'rate_limit': 10  # Requests per second
        },
        'timeframes': {
            'base': {
                'interval': '1m',
                'friendly_name': '1-min',
                'validation': {
                    'min_candles': 50,
                    'max_age': 3600
                },
                'weight': 1.0
            },
            'ltf': {
                'interval': '5m',
                'friendly_name': '5-min',
                'validation': {
                    'min_candles': 15,
                    'max_age': 18000
                },
                'weight': 0.8
            },
            'mtf': {
                'interval': '30m',
                'friendly_name': '30-min',
                'validation': {
                    'min_candles': 5,
                    'max_age': 86400
                },
                'weight': 0.6
            },
            'htf': {
                'interval': '4h',
                'friendly_name': '4-hour',
                'validation': {
                    'min_candles': 1,
                    'max_age': 604800
                },
                'weight': 0.4
            }
        },
        'validation': {
            'min_candles': 20,
            'timeframe_weights': {
                'base': 1.0,
                'ltf': 0.8,
                'mtf': 0.6,
                'htf': 0.4
            }
        },
        'analysis': {
            'indicators': {
                'momentum': {
                    'min_points': 20
                },
                'technical': {
                    'min_points': 20
                }
            }
        },
        'monitoring': {
            'cycle_interval': 60,
            'data_ttl': 300
        },
        'metrics': {
            'enabled': False
        },
        'alerts': {
            'enabled': False
        }
    }
    return config

# Create mock OHLCV data for testing
def create_mock_ohlcv_data():
    """Create mock OHLCV data with different timeframes"""
    now = datetime.now()
    
    # Base timeframe (1m) - create 120 datapoints
    base_dates = pd.date_range(end=now, periods=120, freq='1min')
    base_data = []
    for dt in base_dates:
        timestamp = int(dt.timestamp() * 1000)
        base_price = 20000 + (np.random.random() * 1000)
        base_data.append([
            timestamp,
            base_price,
            base_price + (np.random.random() * 50),
            base_price - (np.random.random() * 50),
            base_price + (np.random.random() * 100 - 50),
            np.random.random() * 10
        ])
    
    logger.info(f"Created mock OHLCV data with {len(base_data)} entries")
    return base_data

# Create minimal mock classes for MarketMonitor dependencies
class MockMetricsManager:
    """Mock metrics manager"""
    async def start(self):
        pass
    
    async def stop(self):
        pass
    
    async def record_metric(self, name, value, tags=None):
        pass
    
    async def update_metrics(self, data):
        pass

class MockAlertManager:
    """Mock alert manager"""
    async def start(self):
        pass
    
    async def stop(self):
        pass
    
    async def send_alert(self, message, level='info'):
        logger.info(f"MOCK ALERT: {message} (level: {level})")

class MockExchange:
    """Mock exchange class for testing without real API calls"""
    
    def __init__(self):
        self.ohlcv_data = create_mock_ohlcv_data()
        
    async def fetch_ohlcv(self, symbol, timeframe='1m', limit=1000):
        """Mock fetch_ohlcv method"""
        logger.info(f"Mock fetch_ohlcv called with timeframe={timeframe}, limit={limit}")
        return self.ohlcv_data[:limit]
    
    async def fetch_order_book(self, symbol, limit=100):
        """Mock fetch_order_book method"""
        return {
            'bids': [[19990.0, 1.5], [19980.0, 2.1], [19970.0, 3.0]],
            'asks': [[20010.0, 1.2], [20020.0, 1.8], [20030.0, 2.5]],
            'timestamp': int(datetime.now().timestamp() * 1000),
            'symbol': symbol
        }
    
    async def fetch_ticker(self, symbol):
        """Mock fetch_ticker method"""
        return {
            'symbol': symbol,
            'timestamp': int(datetime.now().timestamp() * 1000),
            'last': 20000.0,
            'bid': 19990.0,
            'ask': 20010.0,
            'volume': 1000.0
        }
    
    async def fetch_trades(self, symbol, limit=100):
        """Mock fetch_trades method"""
        trades = []
        now = datetime.now()
        for i in range(limit):
            timestamp = int((now - timedelta(minutes=i)).timestamp() * 1000)
            trades.append({
                'id': f'trade_{i}',
                'timestamp': timestamp,
                'datetime': now.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'symbol': symbol,
                'type': 'limit',
                'side': 'buy' if i % 2 == 0 else 'sell',
                'price': 20000.0 + (i % 10),
                'amount': 1.0 + (i % 5) * 0.1
            })
        return trades

async def test_data_flow():
    """Test the flow of data from fetching to technical indicators"""
    try:
        logger.info("Starting data flow test")
        
        # Create configuration
        config = create_test_config()
        
        # Create mock exchange
        exchange = MockExchange()
        
        # Create mock dependencies
        metrics_manager = MockMetricsManager()
        alert_manager = MockAlertManager()
        
        # Use a simpler approach by directly working with data without MarketMonitor
        logger.info("Creating mock market data...")
        
        # Get raw OHLCV data
        raw_ohlcv = await exchange.fetch_ohlcv("BTCUSDT", timeframe="1m", limit=1000)
        logger.info(f"Fetched {len(raw_ohlcv)} raw OHLCV data points")
        
        # Convert to DataFrame
        df = pd.DataFrame(raw_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('datetime')
        
        # Create timeframes manually
        logger.info("Creating timeframes...")
        
        # Function to resample OHLCV data
        def resample_ohlcv(df, rule):
            if df.empty:
                return df
            
            resampled = df.resample(rule).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
                'timestamp': 'first'
            })
            
            return resampled.reset_index()
        
        # Create timeframes
        ohlcv_data = {}
        ohlcv_data['base'] = df.copy().reset_index()  # No resampling for base
        ohlcv_data['ltf'] = resample_ohlcv(df, '5Min')
        ohlcv_data['mtf'] = resample_ohlcv(df, '30Min')
        ohlcv_data['htf'] = resample_ohlcv(df, '4h')  # Using lowercase 'h'
        
        # Log data points in each timeframe
        for tf, tf_df in ohlcv_data.items():
            logger.info(f"Timeframe {tf} has {len(tf_df)} data points")
        
        # Create market data structure
        market_data = {
            'symbol': "BTCUSDT",
            'ohlcv': ohlcv_data,
            'orderbook': await exchange.fetch_order_book("BTCUSDT"),
            'ticker': await exchange.fetch_ticker("BTCUSDT"),
            'trades': await exchange.fetch_trades("BTCUSDT"),
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        
        logger.info("Market data created, checking contents...")
        
        # Initialize technical indicators
        technical_indicators = TechnicalIndicators(config=config, logger=logger)
        
        # Set the TIMEFRAME_CONFIG directly on the instance to match our test data
        technical_indicators.TIMEFRAME_CONFIG = {
            'base': {
                'interval': '1m',
                'friendly_name': '1-min',
                'validation': {
                    'min_candles': 50,
                    'max_age': 3600
                },
                'weight': 1.0
            },
            'ltf': {
                'interval': '5m',
                'friendly_name': '5-min',
                'validation': {
                    'min_candles': 15,
                    'max_age': 18000
                },
                'weight': 0.8
            },
            'mtf': {
                'interval': '30m',
                'friendly_name': '30-min',
                'validation': {
                    'min_candles': 5,
                    'max_age': 86400
                },
                'weight': 0.6
            },
            'htf': {
                'interval': '4h',
                'friendly_name': '4-hour',
                'validation': {
                    'min_candles': 1,
                    'max_age': 604800
                },
                'weight': 0.4
            }
        }
        
        logger.info("Validating market data with technical indicators...")
        
        # Validate the data with technical indicators
        is_valid = technical_indicators._validate_input(market_data)
        logger.info(f"Technical indicators validation result: {is_valid}")
        
        if is_valid:
            logger.info("Calculating technical indicators...")
            result = await technical_indicators.calculate(market_data)
            
            logger.info(f"Technical indicator calculation complete")
            logger.info(f"Final score: {result.get('score')}")
            
            # Log scores for each component
            if 'components' in result:
                logger.info("Component scores:")
                for component, score in result['components'].items():
                    logger.info(f"  {component}: {score}")
            
            # Log scores for each timeframe
            if 'timeframe_scores' in result:
                logger.info("Timeframe scores:")
                for tf, scores in result['timeframe_scores'].items():
                    logger.info(f"  {tf}:")
                    for component, score in scores.items():
                        logger.info(f"    {component}: {score}")
            
            logger.info("✅ Data flow test completed successfully!")
        else:
            logger.error("❌ Technical indicators validation failed")
        
    except Exception as e:
        logger.error(f"Error in data flow test: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Starting test script")
    asyncio.run(test_data_flow()) 