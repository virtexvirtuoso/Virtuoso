import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_sample_price_data(start_time=None, periods=100):
    """Create sample price data for testing."""
    if start_time is None:
        start_time = datetime.utcnow()
    
    return pd.DataFrame({
        'timestamp': pd.date_range(start=start_time, periods=periods, freq='1min'),
        'open': np.random.uniform(45000, 46000, periods),
        'high': np.random.uniform(45500, 46500, periods),
        'low': np.random.uniform(44500, 45500, periods),
        'close': np.random.uniform(45000, 46000, periods),
        'volume': np.random.uniform(1, 100, periods)
    })

def create_sample_trades_data(periods=50):
    """Create sample trades data for testing."""
    return pd.DataFrame({
        'timestamp': pd.date_range(start=datetime.utcnow(), periods=periods, freq='1min'),
        'price': np.random.uniform(45000, 46000, periods),
        'size': np.random.uniform(0.1, 1.0, periods),
        'side': np.random.choice(['Buy', 'Sell'], periods)
    })

def create_sample_orderbook_data():
    """Create sample orderbook data for testing."""
    return {
        'bids': [
            (45000, 1.5),
            (44900, 2.0),
            (44800, 1.0),
            (44700, 2.5),
            (44600, 1.8)
        ],
        'asks': [
            (45100, 1.0),
            (45200, 2.0),
            (45300, 1.5),
            (45400, 1.2),
            (45500, 2.3)
        ]
    }

def create_sample_session_data():
    """Create complete sample session data for testing."""
    return {
        'BTCUSDT': {
            'indicator_data': {
                'price_data': create_sample_price_data(),
                'trades_data': create_sample_trades_data(),
                'orderbook_data': create_sample_orderbook_data()
            },
            'session_start': datetime.utcnow(),
            'symbol': 'BTCUSDT'
        }
    }

class MockDataFetcher:
    """Mock data fetcher for testing."""
    async def fetch_session_data(self, symbols, session_info):
        return create_sample_session_data() 