import pytest
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import Mock, patch
from src.analysis.market_analyzer import MarketAnalyzer

@pytest.fixture
def mock_logger():
    return Mock()

@pytest.fixture
def config():
    return {
        'analysis': {
            'weights': {
                'confluence': {
                    'momentum': 0.135,
                    'volume': 0.15,
                    'orderflow': 0.25,
                    'orderbook': 0.2,
                    'position': 0.15,
                    'sentiment': 0.115
                }
            }
        }
    }

@pytest.fixture
def sample_market_data():
    """Create sample market data in CCXT format."""
    return {
        'ohlcv': [
            {
                'timestamp': 1625097600000,
                'open': 35000.0,
                'high': 35100.0,
                'low': 34900.0,
                'close': 35050.0,
                'volume': 100.0
            },
            {
                'timestamp': 1625097900000,
                'open': 35050.0,
                'high': 35200.0,
                'low': 35000.0,
                'close': 35150.0,
                'volume': 120.0
            }
        ],
        'trades': [
            {
                'id': '1',
                'timestamp': 1625097600000,
                'datetime': '2021-07-01T00:00:00Z',
                'symbol': 'BTC/USDT',
                'order': 'order1',
                'type': 'limit',
                'side': 'buy',
                'takerOrMaker': 'taker',
                'price': 35000.0,
                'amount': 1.0,
                'cost': 35000.0,
                'fee': {'cost': 0.1, 'currency': 'USDT'}
            }
        ],
        'ticker': {
            'symbol': 'BTC/USDT',
            'timestamp': 1625097600000,
            'datetime': '2021-07-01T00:00:00Z',
            'high': 35200.0,
            'low': 34900.0,
            'bid': 35040.0,
            'bidVolume': 1.5,
            'ask': 35060.0,
            'askVolume': 2.0,
            'vwap': 35050.0,
            'open': 35000.0,
            'close': 35050.0,
            'last': 35050.0,
            'previousClose': 34900.0,
            'change': 150.0,
            'percentage': 0.43,
            'average': 35025.0,
            'baseVolume': 100.0,
            'quoteVolume': 3505000.0
        },
        'orderbook': {
            'symbol': 'BTC/USDT',
            'timestamp': 1625097600000,
            'datetime': '2021-07-01T00:00:00Z',
            'nonce': 123456,
            'bids': [[35040.0, 1.5], [35030.0, 2.0]],
            'asks': [[35060.0, 2.0], [35070.0, 1.0]]
        }
    }

def test_calculate_volatility(config, mock_logger, sample_market_data):
    """Test volatility calculation with CCXT data."""
    analyzer = MarketAnalyzer(config, mock_logger)
    
    result = analyzer._calculate_volatility(sample_market_data['ohlcv'])
    
    assert isinstance(result, dict)
    assert 'score' in result
    assert 'level' in result
    assert 'atr' in result
    assert 'volatility_pct' in result
    assert 0 <= result['score'] <= 100
    assert result['level'] in ['very_low', 'low', 'moderate', 'high', 'very_high']

def test_calculate_liquidity(config, mock_logger, sample_market_data):
    """Test liquidity calculation with CCXT data."""
    analyzer = MarketAnalyzer(config, mock_logger)
    
    result = analyzer._calculate_liquidity(sample_market_data['orderbook'])
    
    assert isinstance(result, dict)
    assert 'score' in result
    assert 'level' in result
    assert 'spread' in result
    assert 'depth' in result
    assert 'bid_depth' in result
    assert 'ask_depth' in result
    assert 0 <= result['score'] <= 100
    assert result['level'] in ['very_low', 'low', 'moderate', 'high', 'very_high']

def test_calculate_trend(config, mock_logger, sample_market_data):
    """Test trend calculation with CCXT data."""
    analyzer = MarketAnalyzer(config, mock_logger)
    
    result = analyzer._calculate_trend(sample_market_data['ohlcv'])
    
    assert isinstance(result, dict)
    assert 'score' in result
    assert 'direction' in result
    assert 'strength' in result
    assert 'avg_change' in result
    assert 0 <= result['score'] <= 100
    assert result['direction'] in ['uptrend', 'downtrend', 'sideways', 'unknown']

def test_calculate_momentum(config, mock_logger, sample_market_data):
    """Test momentum calculation with CCXT data."""
    analyzer = MarketAnalyzer(config, mock_logger)
    
    result = analyzer._calculate_momentum(sample_market_data['ohlcv'])
    
    assert isinstance(result, dict)
    assert 'score' in result
    assert 'signal' in result
    assert 'rsi' in result
    assert 0 <= result['score'] <= 100
    assert result['signal'] in ['overbought', 'oversold', 'neutral', 'unknown']
    assert 0 <= result['rsi'] <= 100

def test_calculate_volume_profile(config, mock_logger, sample_market_data):
    """Test volume profile calculation with CCXT data."""
    analyzer = MarketAnalyzer(config, mock_logger)
    
    result = analyzer._calculate_volume_profile(sample_market_data['trades'])
    
    assert isinstance(result, dict)
    assert 'score' in result
    assert 'profile' in result
    assert 'buy_ratio' in result
    assert 'sell_ratio' in result
    assert 'total_volume' in result
    assert 0 <= result['score'] <= 100
    assert result['profile'] in ['buying_pressure', 'selling_pressure', 'balanced', 'unknown']
    assert 0 <= result['buy_ratio'] <= 1
    assert 0 <= result['sell_ratio'] <= 1

def test_calculate_market_impact(config, mock_logger, sample_market_data):
    """Test market impact calculation with CCXT data."""
    analyzer = MarketAnalyzer(config, mock_logger)
    
    result = analyzer._calculate_market_impact(
        sample_market_data['orderbook'],
        sample_market_data['trades']
    )
    
    assert isinstance(result, dict)
    assert 'score' in result
    assert 'impact' in result
    assert 'impact_ratio' in result
    assert 'avg_trade_size' in result
    assert 'total_liquidity' in result
    assert 0 <= result['score'] <= 100
    assert result['impact'] in ['negligible', 'low', 'moderate', 'high', 'very_high', 'unknown']
    assert result['impact_ratio'] >= 0

def test_get_market_conditions(config, mock_logger, sample_market_data):
    """Test market conditions calculation with CCXT data."""
    analyzer = MarketAnalyzer(config, mock_logger)
    
    result = analyzer.get_market_conditions('BTC/USDT', sample_market_data)
    
    assert isinstance(result, dict)
    assert 'volatility' in result
    assert 'liquidity' in result
    assert 'trend' in result
    assert 'momentum' in result
    assert 'volume_profile' in result
    assert 'market_impact' in result

def test_empty_market_data(config, mock_logger):
    """Test handling of empty market data."""
    analyzer = MarketAnalyzer(config, mock_logger)
    
    empty_data = {}
    result = analyzer.get_market_conditions('BTC/USDT', empty_data)
    
    assert isinstance(result, dict)
    assert not result  # Should be empty dict

def test_invalid_market_data(config, mock_logger):
    """Test handling of invalid market data."""
    analyzer = MarketAnalyzer(config, mock_logger)
    
    invalid_data = {'invalid': 'data'}
    result = analyzer.get_market_conditions('BTC/USDT', invalid_data)
    
    assert isinstance(result, dict)
    assert not result  # Should be empty dict

def test_partial_market_data(config, mock_logger, sample_market_data):
    """Test handling of partial market data."""
    analyzer = MarketAnalyzer(config, mock_logger)
    
    # Test with only OHLCV data
    partial_data = {'ohlcv': sample_market_data['ohlcv']}
    result = analyzer.get_market_conditions('BTC/USDT', partial_data)
    
    assert isinstance(result, dict)
    assert 'volatility' in result
    assert 'trend' in result
    assert 'momentum' in result 