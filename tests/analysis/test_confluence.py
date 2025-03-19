import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from src.analysis.confluence import ConfluenceAnalyzer
from src.core.logger import Logger

@pytest.fixture
def mock_config():
    return {
        'indicators': {
            'sentiment': {'enabled': True},
            'momentum': {'enabled': True},
            'volume': {'enabled': True}
        }
    }

@pytest.fixture
def mock_market_data():
    # Create sample OHLCV data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
    ohlcv = pd.DataFrame({
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 101,
        'low': np.random.randn(100).cumsum() + 99,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    return {
        'ohlcv': {'5min': ohlcv},
        'symbol': 'BTC/USDT',
        'timeframe': '5min'
    }

@pytest.fixture
def confluence_analyzer(mock_config):
    return ConfluenceAnalyzer(mock_config, Logger(__name__))

async def test_analyze_confluence_valid_data(confluence_analyzer, mock_market_data):
    """Test confluence analysis with valid market data."""
    result = await confluence_analyzer.analyze_confluence(
        symbol='BTC/USDT',
        symbol_data=mock_market_data,
        timeframe='5min'
    )
    
    assert isinstance(result, dict)
    assert 'overall_score' in result
    assert 'components' in result
    assert isinstance(result['overall_score'], float)
    assert 0 <= result['overall_score'] <= 100

async def test_analyze_confluence_invalid_data(confluence_analyzer):
    """Test confluence analysis with invalid market data."""
    result = await confluence_analyzer.analyze_confluence(
        symbol='BTC/USDT',
        symbol_data={},  # Invalid empty data
        timeframe='5min'
    )
    
    assert isinstance(result, dict)
    assert result['overall_score'] == 50.0
    assert 'error' in result

async def test_component_weights(confluence_analyzer):
    """Test component weights sum to 1."""
    weights_sum = sum(confluence_analyzer.weights.values())
    assert abs(weights_sum - 1.0) < 0.0001

async def test_indicator_initialization(confluence_analyzer):
    """Test all indicators are properly initialized."""
    assert 'sentiment' in confluence_analyzer.indicators
    assert 'momentum' in confluence_analyzer.indicators
    assert 'volume' in confluence_analyzer.indicators 