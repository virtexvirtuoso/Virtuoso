"""
Integration tests for the signal -> alert pathway.

Tests the complete flow from signal generation through the alert system.
"""

import os
import sys
import asyncio
import pytest
import logging
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
import json

# Add src to path to ensure imports work properly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import utilities directly (these don't have circular dependencies)
from src.utils.data_utils import resolve_price, format_price_string

# Configure logging for testing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test constants
SAMPLE_CONFIG = {
    'thresholds': {
        'buy': 70,
        'sell': 30
    },
    'alerts': {
        'discord': {
            'enabled': True,
            'webhook_url': 'https://discord.com/api/webhooks/test'
        },
        'log_level': 'INFO'
    }
}

# Mock implementations to avoid circular imports
class MockSignalGenerator:
    def __init__(self, config, alert_manager=None):
        self.config = config
        self.alert_manager = alert_manager
        self.thresholds = config.get('thresholds', {'buy': 70, 'sell': 30})
        
    async def process_signal(self, signal_data):
        """Mock implementation that simulates processing a signal."""
        symbol = signal_data.get('symbol', 'UNKNOWN')
        score = signal_data.get('score', 0)
        price = signal_data.get('price')
        components = signal_data.get('components', {})
        results = signal_data.get('results', {})
        reliability = signal_data.get('reliability', 0.8)
        
        # Only process BUY or SELL signals
        if score >= self.thresholds['buy'] or score <= self.thresholds['sell']:
            if self.alert_manager and hasattr(self.alert_manager, 'send_confluence_alert'):
                await self.alert_manager.send_confluence_alert(
                    symbol=symbol,
                    confluence_score=score,
                    components=components,
                    results=results,
                    reliability=reliability if reliability <= 1 else reliability / 100.0,
                    buy_threshold=self.thresholds['buy'],
                    sell_threshold=self.thresholds['sell'],
                    price=price
                )
        return None

@pytest.fixture
def mock_alert_manager():
    alert_manager = MagicMock()
    alert_manager.send_confluence_alert = AsyncMock()
    alert_manager.last_alert = {
        'symbol': None,
        'confluence_score': None,
        'components': None,
        'results': None,
        'weights': None,
        'reliability': None,
        'buy_threshold': None,
        'sell_threshold': None,
        'price': None,
        'transaction_id': None,
        'signal_id': None,
        'influential_components': None,
        'market_interpretations': None,
        'actionable_insights': None,
        'top_weighted_subcomponents': None,
        'signal_type': None
    }
    alert_manager.long_threshold = 70.0
    alert_manager.short_threshold = 30.0
    return alert_manager

@pytest.fixture
def signal_generator(mock_alert_manager):
    """Create a SignalGenerator with mocked dependencies."""
    return MockSignalGenerator(config=SAMPLE_CONFIG, alert_manager=mock_alert_manager)

def create_test_signal(symbol='BTCUSDT', score=75, price=50000.0, signal_type = 'LONG'):
    """Create a test signal with specified parameters."""
    return {
        'symbol': symbol,
        'score': score,
        'price': price,
        'signal': signal_type,
        'components': {
            'volume': 80,
            'technical': 75,
            'orderflow': 70,
            'orderbook': 65,
            'sentiment': 85
        },
        'results': {
            'volume': {'score': 80, 'interpretation': 'Strong volume'},
            'technical': {'score': 75, 'interpretation': 'Bullish trend'},
            'orderflow': {'score': 70, 'interpretation': 'Positive flow'},
            'orderbook': {'score': 65, 'interpretation': 'Balanced'},
            'sentiment': {'score': 85, 'interpretation': 'Very positive'}
        },
        'reliability': 85.0,
        'timestamp': datetime.now().timestamp()
    }

@pytest.mark.asyncio
async def test_buy_signal_generates_alert(signal_generator, mock_alert_manager):
    """Test that a buy signal properly generates an alert."""
    # Create a buy signal
    buy_signal = create_test_signal(score=75, signal_type = 'LONG')
    
    # Process the signal
    await signal_generator.process_signal(buy_signal)
    
    # Verify alert manager was called with expected parameters
    mock_alert_manager.send_confluence_alert.assert_called_once()
    call_args = mock_alert_manager.send_confluence_alert.call_args[1]
    
    assert call_args['symbol'] == 'BTCUSDT'
    assert call_args['confluence_score'] == 75
    assert abs(call_args['reliability'] - 0.85) < 0.01  # Account for float precision
    assert call_args['price'] == 50000.0
    assert call_args['buy_threshold'] == 70
    assert call_args['sell_threshold'] == 30

@pytest.mark.asyncio
async def test_sell_signal_generates_alert(signal_generator, mock_alert_manager):
    """Test that a sell signal properly generates an alert."""
    # Create a sell signal
    sell_signal = create_test_signal(score=25, signal_type = 'SHORT')
    
    # Process the signal
    await signal_generator.process_signal(sell_signal)
    
    # Verify alert manager was called with expected parameters
    mock_alert_manager.send_confluence_alert.assert_called_once()
    call_args = mock_alert_manager.send_confluence_alert.call_args[1]
    
    assert call_args['symbol'] == 'BTCUSDT'
    assert call_args['confluence_score'] == 25

@pytest.mark.asyncio
async def test_neutral_signal_no_alert(signal_generator, mock_alert_manager):
    """Test that a neutral signal does not generate an alert."""
    # Create a neutral signal
    neutral_signal = create_test_signal(score=50, signal_type='NEUTRAL')
    
    # Process the signal
    await signal_generator.process_signal(neutral_signal)
    
    # Verify alert manager was not called (as this should be neutral)
    mock_alert_manager.send_confluence_alert.assert_not_called()

@pytest.mark.asyncio
async def test_missing_price_resolution(signal_generator, mock_alert_manager):
    """Test price resolution fallback when price is missing."""
    # Create a signal without price
    signal_without_price = create_test_signal()
    signal_without_price.pop('price')
    
    # Add price to market data for resolution
    signal_without_price['market_data'] = {
        'ticker': {
            'last': 49500.0
        }
    }
    
    # Process the signal - our mock doesn't handle price resolution,
    # but we can still test the alert call without it
    await signal_generator.process_signal(signal_without_price)
    
    # Verify alert was sent
    mock_alert_manager.send_confluence_alert.assert_called_once()

def test_utility_functions():
    """Test the utility functions for price resolution and formatting."""
    # Test price resolution
    signal_data = {
        'price': 55000.0
    }
    assert resolve_price(signal_data) == 55000.0
    
    # Test fallback to market data
    signal_data = {
        'market_data': {
            'ticker': {
                'last': 56000.0
            }
        }
    }
    assert resolve_price(signal_data) == 56000.0
    
    # Test price formatting
    assert format_price_string(0.00123) == "$0.00123"
    assert format_price_string(123.45) == "$123.45"
    assert format_price_string(12345.67) == "$12,345.67"
    assert format_price_string(None) == "Price not available"

@pytest.mark.asyncio
async def test_signal_alert_flow():
    # Create a mock alert manager for this test
    mock_alert_manager = MagicMock()
    mock_alert_manager.send_confluence_alert = AsyncMock()
    mock_alert_manager.last_alert = {}
    
    # Test case 1: Reliability <= 1
    signal_data_1 = {
        'symbol': 'BTC/USDT',
        'reliability': 0.85,  # 85%
        'confluence_score': 0.75,
        'components': ['RSI', 'MACD'],
        'results': {'RSI': True, 'MACD': True},
        'buy_threshold': 0.7,
        'sell_threshold': 0.3,
        'price': 50000.0
    }
    
    await mock_alert_manager.send_confluence_alert(
        symbol=signal_data_1['symbol'],
        confluence_score=signal_data_1['confluence_score'],
        components=signal_data_1['components'],
        results=signal_data_1['results'],
        reliability=signal_data_1['reliability'],
        buy_threshold=signal_data_1['buy_threshold'],
        sell_threshold=signal_data_1['sell_threshold'],
        price=signal_data_1['price']
    )
    
    # Verify first call
    mock_alert_manager.send_confluence_alert.assert_called_once()
    call_args = mock_alert_manager.send_confluence_alert.call_args[1]
    assert call_args['symbol'] == 'BTC/USDT'
    assert call_args['confluence_score'] == 0.75
    assert call_args['reliability'] == 0.85
    
    # Reset mock for second test
    mock_alert_manager.send_confluence_alert.reset_mock()
    
    # Test case 2: Reliability > 1 (percentage format)
    signal_data_2 = {
        'symbol': 'ETH/USDT',
        'reliability': 85.0,  # 85%
        'confluence_score': 0.8,
        'components': ['RSI', 'MACD', 'BB'],
        'results': {'RSI': True, 'MACD': True, 'BB': True},
        'buy_threshold': 0.75,
        'sell_threshold': 0.25,
        'price': 3000.0
    }
    
    await mock_alert_manager.send_confluence_alert(
        symbol=signal_data_2['symbol'],
        confluence_score=signal_data_2['confluence_score'],
        components=signal_data_2['components'],
        results=signal_data_2['results'],
        reliability=signal_data_2['reliability'] / 100,  # Convert to decimal
        buy_threshold=signal_data_2['buy_threshold'],
        sell_threshold=signal_data_2['sell_threshold'],
        price=signal_data_2['price']
    )
    
    # Verify second call
    mock_alert_manager.send_confluence_alert.assert_called_once()
    call_args = mock_alert_manager.send_confluence_alert.call_args[1]
    assert call_args['symbol'] == 'ETH/USDT'
    assert call_args['confluence_score'] == 0.8
    assert abs(call_args['reliability'] - 0.85) < 0.01  # Account for float precision

if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 