import logging
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.orderbook_indicators import OrderbookIndicators
from src.indicators.sentiment_indicators import SentimentIndicators

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(message)s')

# Create a simple mock config
def create_mock_config():
    """Create a mock configuration for indicators."""
    return {
        'timeframes': {
            'base': {
                'weight': 0.5,
                'interval': 60,
                'validation': {'min_candles': 20}
            },
            'ltf': {
                'weight': 0.1,
                'interval': 15,
                'validation': {'min_candles': 20}
            },
            'mtf': {
                'weight': 0.2,
                'interval': 240,
                'validation': {'min_candles': 20}
            },
            'htf': {
                'weight': 0.2,
                'interval': 1440,
                'validation': {'min_candles': 20}
            }
        },
        'log_level': 'INFO',
        'components': {
            'volume': {'enabled': True},
            'orderbook': {'enabled': True},
            'sentiment': {'enabled': True}
        },
        'validation_requirements': {
            'trades': {'min_trades': 50, 'max_age': 3600},
            'orderbook': {'min_depth': 10, 'max_age': 60}
        }
    }

# Create a simple mock market data dictionary
def create_mock_market_data():
    """Create mock market data for testing."""
    import pandas as pd
    import numpy as np
    
    # Create sample OHLCV data
    dates = pd.date_range(start='2023-01-01', periods=100, freq='1h')
    ohlcv = pd.DataFrame({
        'open': np.random.normal(50000, 1000, 100),
        'high': np.random.normal(51000, 1000, 100),
        'low': np.random.normal(49000, 1000, 100),
        'close': np.random.normal(50500, 1000, 100),
        'volume': np.random.normal(100, 20, 100)
    }, index=dates)
    
    # Create mock orderbook data
    orderbook = {
        'bids': [(49900, 1.5), (49800, 2.0), (49700, 2.5)],
        'asks': [(50100, 1.2), (50200, 1.8), (50300, 2.2)]
    }
    
    # Create mock sentiment data
    sentiment = {
        'funding_rate': 0.0001,
        'long_short_ratio': 1.2,
        'liquidations': {'long': 1000000, 'short': 800000},
        'market_mood': 60,
        'risk_score': 45
    }
    
    return {
        'symbol': 'BTC/USDT',
        'ohlcv': {'base': ohlcv},
        'orderbook': orderbook,
        'sentiment': sentiment
    }

async def test_indicators():
    """Test the formatting of indicator results."""
    print("\n\n===== TESTING INDICATOR FORMATTING =====\n")
    
    # Create mock config and market data
    config = create_mock_config()
    market_data = create_mock_market_data()
    
    # Test Volume Indicators
    print("\n\n===== VOLUME INDICATORS =====\n")
    vi = VolumeIndicators(config)
    await vi.calculate(market_data)
    
    # Test Orderbook Indicators
    print("\n\n===== ORDERBOOK INDICATORS =====\n")
    oi = OrderbookIndicators(config)
    await oi.calculate(market_data)
    
    # Test Sentiment Indicators
    print("\n\n===== SENTIMENT INDICATORS =====\n")
    si = SentimentIndicators(config)
    await si.calculate(market_data)
    
    print("\n\n===== TEST COMPLETE =====\n")

if __name__ == "__main__":
    asyncio.run(test_indicators()) 