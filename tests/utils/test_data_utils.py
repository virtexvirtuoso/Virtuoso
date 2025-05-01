"""
Tests for data utility functions.

These tests verify that the data utilities properly handle various scenarios.
"""

import os
import sys
import pytest
from datetime import datetime

# Add src to path to ensure imports work properly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.utils.data_utils import resolve_price, format_price_string

def test_resolve_price_direct():
    """Test price resolution with direct price field."""
    data = {'price': 55000.0, 'symbol': 'BTCUSDT'}
    result = resolve_price(data)
    assert result == 55000.0

def test_resolve_price_current_price():
    """Test price resolution falling back to current_price."""
    data = {'current_price': 56000.0, 'symbol': 'BTCUSDT'}
    result = resolve_price(data)
    assert result == 56000.0

def test_resolve_price_from_market_data():
    """Test price resolution from market data ticker."""
    # Test with last price
    data = {
        'symbol': 'BTCUSDT',
        'market_data': {
            'ticker': {
                'last': 57000.0
            }
        }
    }
    result = resolve_price(data)
    assert result == 57000.0
    
    # Test with close price
    data = {
        'symbol': 'ETHUSDT',
        'market_data': {
            'ticker': {
                'close': 3000.0
            }
        }
    }
    result = resolve_price(data)
    assert result == 3000.0

def test_resolve_price_from_components():
    """Test price resolution from components dictionary."""
    data = {
        'symbol': 'BTCUSDT',
        'components': {
            'price': 58000.0
        }
    }
    result = resolve_price(data)
    assert result == 58000.0

def test_resolve_price_from_results():
    """Test price resolution from results dictionary."""
    # Direct price in results
    data = {
        'symbol': 'BTCUSDT',
        'results': {
            'price': 59000.0
        }
    }
    result = resolve_price(data)
    assert result == 59000.0
    
    # Alternative fields in results
    data = {
        'symbol': 'BTCUSDT',
        'results': {
            'last_price': 59500.0
        }
    }
    result = resolve_price(data)
    assert result == 59500.0

def test_resolve_price_from_metadata():
    """Test price resolution from metadata."""
    # Price in metadata
    data = {
        'symbol': 'BTCUSDT',
        'results': {
            'metadata': {
                'price': 60000.0
            }
        }
    }
    result = resolve_price(data)
    assert result == 60000.0
    
    # Last price in metadata
    data = {
        'symbol': 'BTCUSDT',
        'results': {
            'metadata': {
                'last_price': 60500.0
            }
        }
    }
    result = resolve_price(data)
    assert result == 60500.0

def test_resolve_price_priority():
    """Test that price resolution follows the correct priority order."""
    # Data with multiple price sources - should pick direct price
    data = {
        'price': 61000.0,
        'current_price': 62000.0,
        'market_data': {'ticker': {'last': 63000.0}},
        'components': {'price': 64000.0},
        'results': {'price': 65000.0, 'metadata': {'price': 66000.0}}
    }
    result = resolve_price(data)
    assert result == 61000.0
    
    # Remove direct price - should pick current_price next
    data.pop('price')
    result = resolve_price(data)
    assert result == 62000.0
    
    # Remove current_price - should pick market_data.ticker.last next
    data.pop('current_price')
    result = resolve_price(data)
    assert result == 63000.0
    
    # Remove market_data - should pick components.price next
    data.pop('market_data')
    result = resolve_price(data)
    assert result == 64000.0
    
    # Remove components - should pick results.price next
    data.pop('components')
    result = resolve_price(data)
    assert result == 65000.0
    
    # Remove results.price but keep metadata - should pick results.metadata.price last
    data['results'].pop('price')
    result = resolve_price(data)
    assert result == 66000.0

def test_resolve_price_converts_types():
    """Test that price is properly converted to float."""
    # Price as string
    data = {'price': '67000.0'}
    result = resolve_price(data)
    assert result == 67000.0
    assert isinstance(result, float)
    
    # Price as integer
    data = {'price': 68000}
    result = resolve_price(data)
    assert result == 68000.0
    assert isinstance(result, float)

def test_resolve_price_handles_invalid():
    """Test handling of invalid price values."""
    # Non-numeric price
    data = {'price': 'not-a-number'}
    result = resolve_price(data)
    assert result is None
    
    # Empty data
    result = resolve_price({})
    assert result is None

def test_format_price_string():
    """Test price formatting for different price ranges."""
    # Small price (< 1)
    assert format_price_string(0.00345) == "$0.00345"
    
    # Medium price (1-999)
    assert format_price_string(123.45) == "$123.45"
    
    # Large price (≥ 1000)
    assert format_price_string(1234.56) == "$1,234.56"
    
    # Very large price
    assert format_price_string(1234567.89) == "$1,234,567.89"
    
    # Missing price
    assert format_price_string(None) == "Price not available"

if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 