import pytest
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import Mock, patch
from src.analysis.session_analyzer import SessionAnalyzer

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
def sample_session_data():
    """Create sample session data in CCXT format."""
    return {
        'BTC/USDT': {
            'ohlcv': [
                [1625097600000, 35000.0, 35100.0, 34900.0, 35050.0, 100.0],
                [1625097900000, 35050.0, 35200.0, 35000.0, 35150.0, 120.0]
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
            },
            'open_interest': {
                'symbol': 'BTC/USDT',
                'timestamp': 1625097600000,
                'datetime': '2021-07-01T00:00:00Z',
                'value': 1000.0,
                'valueInUSD': 35050000.0
            }
        }
    }

@pytest.mark.asyncio
async def test_analyze_session(config, mock_logger, sample_session_data):
    """Test session analysis with CCXT formatted data."""
    analyzer = SessionAnalyzer(config, mock_logger)
    
    result = await analyzer.analyze_session(sample_session_data)
    
    assert isinstance(result, dict)
    assert 'timestamp' in result
    assert 'session_id' in result
    assert 'market_analyses' in result
    assert 'session_metrics' in result
    assert 'risk_metrics' in result
    assert 'performance_metrics' in result
    assert 'warnings' in result
    
    # Check market analyses
    market_analyses = result['market_analyses']
    assert 'BTC/USDT' in market_analyses
    
    # Check session metrics format
    session_metrics = result['session_metrics']
    assert isinstance(session_metrics, dict)
    
    # Check risk metrics format
    risk_metrics = result['risk_metrics']
    assert isinstance(risk_metrics, dict)
    
    # Check performance metrics format
    performance_metrics = result['performance_metrics']
    assert isinstance(performance_metrics, dict)

@pytest.mark.asyncio
async def test_analyze_session_with_invalid_data(config, mock_logger):
    """Test session analysis with invalid data."""
    analyzer = SessionAnalyzer(config, mock_logger)
    
    invalid_data = {'invalid': 'data'}
    result = await analyzer.analyze_session(invalid_data)
    
    assert isinstance(result, dict)
    assert result['warnings'] == ['Session analysis failed']
    assert not result['market_analyses']
    assert not result['session_metrics']
    assert not result['risk_metrics']
    assert not result['performance_metrics']

def test_standardize_session_data(config, mock_logger, sample_session_data):
    """Test session data standardization to CCXT format."""
    analyzer = SessionAnalyzer(config, mock_logger)
    
    standardized = analyzer._standardize_session_data(sample_session_data)
    
    assert isinstance(standardized, dict)
    assert 'BTC/USDT' in standardized
    
    symbol_data = standardized['BTC/USDT']
    assert 'ohlcv' in symbol_data
    assert 'trades' in symbol_data
    assert 'ticker' in symbol_data
    assert 'orderbook' in symbol_data
    assert 'open_interest' in symbol_data
    
    # Check OHLCV format
    ohlcv = symbol_data['ohlcv'][0]
    assert 'timestamp' in ohlcv
    assert 'open' in ohlcv
    assert 'high' in ohlcv
    assert 'low' in ohlcv
    assert 'close' in ohlcv
    assert 'volume' in ohlcv
    
    # Check trades format
    trade = symbol_data['trades'][0]
    assert 'id' in trade
    assert 'timestamp' in trade
    assert 'price' in trade
    assert 'amount' in trade
    
    # Check ticker format
    ticker = symbol_data['ticker']
    assert 'symbol' in ticker
    assert 'timestamp' in ticker
    assert 'bid' in ticker
    assert 'ask' in ticker
    
    # Check orderbook format
    orderbook = symbol_data['orderbook']
    assert 'symbol' in orderbook
    assert 'timestamp' in orderbook
    assert 'bids' in orderbook
    assert 'asks' in orderbook

def test_validate_session_data(config, mock_logger, sample_session_data):
    """Test session data validation with CCXT fields."""
    analyzer = SessionAnalyzer(config, mock_logger)
    
    # Test valid data
    assert analyzer._validate_session_data(analyzer._standardize_session_data(sample_session_data))
    
    # Test invalid data
    invalid_data = {'BTC/USDT': {'invalid': 'data'}}
    assert not analyzer._validate_session_data(invalid_data)
    
    # Test missing required fields
    incomplete_data = {'BTC/USDT': {'ohlcv': [], 'trades': []}}  # Missing ticker and orderbook
    assert not analyzer._validate_session_data(incomplete_data)

def test_standardize_ohlcv(config, mock_logger):
    """Test OHLCV data standardization to CCXT format."""
    analyzer = SessionAnalyzer(config, mock_logger)
    
    ohlcv_data = [
        [1625097600000, 35000.0, 35100.0, 34900.0, 35050.0, 100.0]
    ]
    
    standardized = analyzer._standardize_ohlcv(ohlcv_data)
    
    assert len(standardized) == 1
    candle = standardized[0]
    assert candle['timestamp'] == 1625097600000
    assert candle['open'] == 35000.0
    assert candle['high'] == 35100.0
    assert candle['low'] == 34900.0
    assert candle['close'] == 35050.0
    assert candle['volume'] == 100.0

def test_standardize_trades(config, mock_logger):
    """Test trades data standardization to CCXT format."""
    analyzer = SessionAnalyzer(config, mock_logger)
    
    trades_data = [{
        'id': '1',
        'timestamp': 1625097600000,
        'symbol': 'BTC/USDT',
        'price': '35000.0',
        'amount': '1.0'
    }]
    
    standardized = analyzer._standardize_trades(trades_data)
    
    assert len(standardized) == 1
    trade = standardized[0]
    assert trade['id'] == '1'
    assert trade['timestamp'] == 1625097600000
    assert trade['symbol'] == 'BTC/USDT'
    assert trade['price'] == 35000.0
    assert trade['amount'] == 1.0

def test_standardize_ticker(config, mock_logger):
    """Test ticker data standardization to CCXT format."""
    analyzer = SessionAnalyzer(config, mock_logger)
    
    ticker_data = {
        'symbol': 'BTC/USDT',
        'timestamp': 1625097600000,
        'bid': '35040.0',
        'ask': '35060.0'
    }
    
    standardized = analyzer._standardize_ticker(ticker_data)
    
    assert standardized['symbol'] == 'BTC/USDT'
    assert standardized['timestamp'] == 1625097600000
    assert standardized['bid'] == 35040.0
    assert standardized['ask'] == 35060.0

def test_standardize_orderbook(config, mock_logger):
    """Test orderbook data standardization to CCXT format."""
    analyzer = SessionAnalyzer(config, mock_logger)
    
    orderbook_data = {
        'symbol': 'BTC/USDT',
        'timestamp': 1625097600000,
        'bids': [['35040.0', '1.5'], ['35030.0', '2.0']],
        'asks': [['35060.0', '2.0'], ['35070.0', '1.0']]
    }
    
    standardized = analyzer._standardize_orderbook(orderbook_data)
    
    assert standardized['symbol'] == 'BTC/USDT'
    assert standardized['timestamp'] == 1625097600000
    assert len(standardized['bids']) == 2
    assert len(standardized['asks']) == 2
    assert standardized['bids'][0] == [35040.0, 1.5]
    assert standardized['asks'][0] == [35060.0, 2.0] 