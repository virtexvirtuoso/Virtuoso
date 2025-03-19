import asyncio
import pytest
import logging
import numpy as np
import pandas as pd
from src.core.analysis.confluence import ConfluenceAnalysis, ConfluenceConfig
from src.core.exchanges.hyperliquid import HyperliquidExchange
from src.config import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

def generate_hyperliquid_test_data():
    """Generate sample Hyperliquid market data for testing."""
    now = datetime.utcnow()
    periods = 100
    
    # Generate timestamps
    timestamps = [now - timedelta(minutes=i) for i in range(periods)]
    timestamps.reverse()
    
    # Create price data with Hyperliquid-specific ranges
    price_data = pd.DataFrame({
        'timestamp': timestamps,
        'open': np.random.uniform(45000, 50000, periods),  # BTC price range
        'high': np.random.uniform(45000, 50000, periods),
        'low': np.random.uniform(45000, 50000, periods),
        'close': np.random.uniform(45000, 50000, periods),
        'volume': np.random.uniform(1, 100, periods)  # BTC volume in contracts
    })
    price_data.set_index('timestamp', inplace=True)
    
    # Create trades data with Hyperliquid-specific fields
    trades = []
    for _ in range(1000):
        timestamp = now - timedelta(minutes=np.random.randint(0, periods))
        trades.append({
            'timestamp': timestamp,
            'price': np.random.uniform(45000, 50000),
            'size': np.random.uniform(0.1, 1.0),  # Size in BTC
            'side': np.random.choice(['buy', 'sell']),
            'symbol': 'BTC-PERP',  # Hyperliquid perpetual contract
            'liquidation': np.random.choice([True, False], p=[0.05, 0.95])  # 5% chance of liquidation
        })
    
    trades_data = pd.DataFrame(trades)
    trades_data.set_index('timestamp', inplace=True)
    trades_data.sort_index(inplace=True)
    
    # Create Hyperliquid-specific orderbook data
    orderbook_data = {
        'bids': [(np.random.uniform(45000, 50000), np.random.uniform(0.1, 1.0)) for _ in range(10)],
        'asks': [(np.random.uniform(45000, 50000), np.random.uniform(0.1, 1.0)) for _ in range(10)]
    }
    
    # Create Hyperliquid-specific position data
    position_data = {
        'size': np.random.uniform(-10, 10),  # Position size (negative for short)
        'entry_price': np.random.uniform(45000, 50000),
        'liquidation_price': np.random.uniform(40000, 55000),
        'margin': np.random.uniform(1000, 10000),
        'leverage': np.random.uniform(1, 10)
    }
    
    # Create momentum data
    momentum_data = pd.DataFrame({
        'timestamp': timestamps,
        'rsi': np.random.uniform(0, 100, periods),
        'macd': np.random.uniform(-100, 100, periods),
        'macd_signal': np.random.uniform(-100, 100, periods),
        'macd_hist': np.random.uniform(-50, 50, periods),
        'stoch_k': np.random.uniform(0, 100, periods),
        'stoch_d': np.random.uniform(0, 100, periods)
    })
    momentum_data.set_index('timestamp', inplace=True)
    
    # Create sentiment data
    sentiment_data = {
        'funding_rate': np.random.uniform(-0.001, 0.001),  # Typical funding rate range
        'long_short_ratio': np.random.uniform(0.5, 2.0),  # Long/short ratio
        'liquidation_events': [
            {
                'timestamp': timestamp,
                'price': np.random.uniform(45000, 50000),
                'size': np.random.uniform(1, 10),
                'side': np.random.choice(['long', 'short'])
            }
            for timestamp in timestamps[:5]  # Last 5 liquidation events
        ],
        'market_sentiment': {
            'fear_greed_index': np.random.uniform(0, 100),
            'social_volume': np.random.uniform(1000, 10000),
            'social_sentiment': np.random.uniform(-1, 1)
        }
    }
    
    return {
        'price_data': {
            'ltf': price_data,
            'htf': price_data.resample('1h').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
        },
        'trades_data': trades_data,
        'orderbook_data': orderbook_data,
        'position_data': position_data,
        'momentum_data': momentum_data,
        'sentiment_data': sentiment_data
    }

@pytest.fixture
def config():
    """Load test configuration."""
    return load_config()

@pytest.fixture
def analysis_engine(config):
    """Initialize analysis engine with configuration."""
    return ConfluenceAnalysis(config)

@pytest.mark.asyncio
async def test_confluence_analysis():
    """Test the confluence analysis functionality"""
    try:
        # Load config
        config = load_config()
        
        # Initialize exchange and analysis
        exchange = HyperliquidExchange(config)
        analysis = ConfluenceAnalysis(ConfluenceConfig())

        # Generate test data
        market_data = {
            'trades': pd.DataFrame({
                'symbol': ['BTCUSDT'] * 100,
                'price': np.random.uniform(950, 1050, 100),
                'size': np.random.uniform(1, 100, 100),
                'side': np.random.choice(['buy', 'sell'], 100),
                'amount': np.random.uniform(1000, 10000, 100),
                'timestamp': pd.date_range(end=pd.Timestamp.now(), periods=100, freq='1min')
            }),
            'price_data': {
                'ltf': pd.DataFrame({
                    'open': np.random.uniform(950, 1050, 100),
                    'high': np.random.uniform(950, 1050, 100),
                    'low': np.random.uniform(950, 1050, 100),
                    'close': np.random.uniform(950, 1050, 100),
                    'volume': np.random.uniform(1000, 10000, 100),
                    'timestamp': pd.date_range(end=pd.Timestamp.now(), periods=100, freq='1min')
                }),
                'mtf': pd.DataFrame({
                    'open': np.random.uniform(950, 1050, 100),
                    'high': np.random.uniform(950, 1050, 100),
                    'low': np.random.uniform(950, 1050, 100),
                    'close': np.random.uniform(950, 1050, 100),
                    'volume': np.random.uniform(1000, 10000, 100),
                    'timestamp': pd.date_range(end=pd.Timestamp.now(), periods=100, freq='5min')
                }),
                'htf': pd.DataFrame({
                    'open': np.random.uniform(950, 1050, 100),
                    'high': np.random.uniform(950, 1050, 100),
                    'low': np.random.uniform(950, 1050, 100),
                    'close': np.random.uniform(950, 1050, 100),
                    'volume': np.random.uniform(1000, 10000, 100),
                    'timestamp': pd.date_range(end=pd.Timestamp.now(), periods=100, freq='15min')
                })
            },
            'orderbook': pd.DataFrame({
                'symbol': ['BTCUSDT'] * 10,
                'price': np.linspace(990, 1010, 10),
                'size': np.random.uniform(1, 100, 10),
                'side': ['buy'] * 5 + ['sell'] * 5
            }),
            'positions': pd.DataFrame({
                'symbol': ['BTCUSDT'],
                'size': [10.0],
                'side': ['buy'],
                'entry_price': [1000.0],
                'leverage': [10.0],
                'liquidation_price': [900.0],
                'margin_ratio': [0.1],
                'unrealized_pnl': [100.0],
                'realized_pnl': [50.0],
                'margin': [1000.0],
                'longShortRatio': [1.5],
                'position_value': [10000.0],
                'position_risk': [0.1],
                'position_margin': [1000.0],
                'open_interest': [1000000.0]
            })
        }

        # Run analysis
        result = await analysis.analyze(market_data)

        # Log results
        logging.info("\nAnalysis Results:")
        logging.info(f"Overall Score: {result['score']:.2f}")
        logging.info("\nComponent Scores:")
        for component, score in result['components'].items():
            logging.info(f"{component.capitalize()}: {score:.2f}")
        logging.info("\nInterpretation:")
        for component, interp in result['interpretation'].items():
            logging.info(f"{component.capitalize()}: {interp}")

        # Assertions
        assert isinstance(result, dict)
        assert 'score' in result
        assert 'components' in result
        assert 'interpretation' in result
        assert isinstance(result['score'], float)
        assert isinstance(result['components'], dict)
        assert isinstance(result['interpretation'], dict)
        assert 0 <= result['score'] <= 100

    except Exception as e:
        logging.error(f"Error in Hyperliquid confluence analysis test: {e}")
        raise

if __name__ == '__main__':
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Load config
    config = load_config()
    
    # Initialize analysis engine
    analysis_engine = ConfluenceAnalysis(config)
    
    # Run test in event loop
    asyncio.run(test_confluence_analysis()) 