"""
Basic Integration Test for Refactored Monitoring Components

A simplified test to verify that the extracted components work together correctly
without complex pytest setup.
"""

import asyncio
import logging
import sys
import os
from unittest.mock import Mock, AsyncMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.monitoring.signal_processor import SignalProcessor
from src.monitoring.websocket_manager import MonitoringWebSocketManager
from src.monitoring.metrics_tracker import MetricsTracker


def create_mock_config():
    """Create a mock configuration."""
    return {
        'exchange': 'bybit',
        'monitoring_interval': 5,
        'confluence': {
            'thresholds': {
                'buy': 60.0,
                'sell': 40.0,
                'neutral_buffer': 5.0
            }
        },
        'websocket_config': {
            'enabled': True,
            'use_ws_for_orderbook': True,
            'use_ws_for_trades': True,
            'use_ws_for_tickers': True
        },
        'monitoring': {
            'thresholds': {
                'volume_change': 0.2,
                'orderflow_change': 0.15
            },
            'health_thresholds': {
                'memory_usage_warning': 85.0,
                'cpu_usage_warning': 80.0
            }
        },
        'trading': {
            'risk_percentage': 2.0,
            'stop_loss_percent': 2.0,
            'take_profit_percent': 6.0,
            'balance': 10000
        }
    }


def create_mock_managers():
    """Create mock manager instances."""
    signal_generator = Mock()
    signal_generator.process_signal = Mock()
    signal_generator._generate_enhanced_formatted_data = Mock(return_value={
        'market_interpretations': [],
        'actionable_insights': []
    })
    
    metrics_manager = Mock()
    metrics_manager.update_analysis_metrics = AsyncMock()
    metrics_manager.update_system_metrics = AsyncMock()
    metrics_manager.start_operation = Mock(return_value='mock_operation')
    metrics_manager.end_operation = Mock()
    metrics_manager.record_metric = Mock()
    
    market_data_manager = Mock()
    market_data_manager.get_market_data = AsyncMock(return_value={
        'ticker': {'last': 50000.0, 'close': 50000.0}
    })
    market_data_manager.get_stats = Mock(return_value={
        'rest_calls': 100,
        'websocket_updates': 50,
        'websocket': {
            'connected': True,
            'seconds_since_last_message': 5
        }
    })
    
    interpretation_manager = Mock()
    interpretation_manager.process_interpretations = Mock()
    
    exchange_manager = Mock()
    exchange_manager.ping = AsyncMock()
    
    timestamp_utility = Mock()
    timestamp_utility.get_utc_timestamp = Mock(return_value=1234567890000)
    
    return {
        'signal_generator': signal_generator,
        'metrics_manager': metrics_manager,
        'market_data_manager': market_data_manager,
        'interpretation_manager': interpretation_manager,
        'exchange_manager': exchange_manager,
        'timestamp_utility': timestamp_utility
    }


def test_signal_processor():
    """Test SignalProcessor functionality."""
    print("Testing SignalProcessor...")
    
    config = create_mock_config()
    managers = create_mock_managers()
    
    # Test initialization
    processor = SignalProcessor(
        config=config,
        signal_generator=managers['signal_generator'],
        metrics_manager=managers['metrics_manager'],
        interpretation_manager=managers['interpretation_manager'],
        market_data_manager=managers['market_data_manager']
    )
    
    assert processor.config == config
    assert processor.signal_generator == managers['signal_generator']
    print("✓ SignalProcessor initialization successful")
    
    # Test trade parameter calculation
    params = processor.calculate_trade_parameters(
        symbol='BTCUSDT',
        price=50000.0,
        signal_type='BUY',
        score=75.0,
        reliability=1.0
    )
    
    assert params['entry_price'] == 50000.0
    assert params['stop_loss'] < 50000.0  # Stop loss below entry for BUY
    assert params['take_profit'] > 50000.0  # Take profit above entry for BUY
    assert 0 < params['confidence'] <= 1.0
    print("✓ Trade parameter calculation works correctly")
    
    return True


async def test_signal_processing():
    """Test signal processing functionality."""
    print("Testing signal processing...")
    
    config = create_mock_config()
    managers = create_mock_managers()
    
    processor = SignalProcessor(
        config=config,
        signal_generator=managers['signal_generator'],
        metrics_manager=managers['metrics_manager'],
        interpretation_manager=managers['interpretation_manager'],
        market_data_manager=managers['market_data_manager']
    )
    
    # Test analysis result processing
    analysis_result = {
        'confluence_score': 65.0,
        'reliability': 1.0,
        'components': {
            'volume': 70.0,
            'sentiment': 60.0,
            'orderflow': 65.0
        },
        'results': {},
        'market_interpretations': []
    }
    
    await processor.process_analysis_result('BTCUSDT', analysis_result)
    
    # Verify metrics were updated
    managers['metrics_manager'].update_analysis_metrics.assert_called_once()
    print("✓ Analysis result processing works correctly")
    
    return True


def test_websocket_manager():
    """Test WebSocket manager functionality."""
    print("Testing WebSocket Manager...")
    
    config = create_mock_config()
    managers = create_mock_managers()
    
    # Test initialization
    ws_manager = MonitoringWebSocketManager(
        config=config,
        symbol='BTCUSDT',
        exchange_id='bybit',
        timestamp_utility=managers['timestamp_utility'],
        metrics_manager=managers['metrics_manager']
    )
    
    assert ws_manager.symbol == 'BTCUSDT'
    assert ws_manager.exchange_id == 'bybit'
    assert not ws_manager.is_connected  # Not connected initially
    print("✓ WebSocket Manager initialization successful")
    
    # Test status retrieval
    status = ws_manager.get_websocket_status()
    assert 'connected' in status
    assert 'enabled' in status
    print("✓ WebSocket status retrieval works correctly")
    
    return True


async def test_websocket_message_processing():
    """Test WebSocket message processing."""
    print("Testing WebSocket message processing...")
    
    config = create_mock_config()
    managers = create_mock_managers()
    
    ws_manager = MonitoringWebSocketManager(
        config=config,
        symbol='BTCUSDT',
        exchange_id='bybit',
        timestamp_utility=managers['timestamp_utility'],
        metrics_manager=managers['metrics_manager']
    )
    
    # Test ticker message processing
    ticker_message = {
        'data': {
            'data': {
                'lastPrice': '50000.0',
                'bid1Price': '49999.0',
                'ask1Price': '50001.0',
                'highPrice24h': '51000.0',
                'lowPrice24h': '49000.0',
                'volume24h': '1000.0'
            }
        },
        'timestamp': 1234567890000
    }
    
    await ws_manager._process_ticker_update(ticker_message)
    
    # Check if ticker data was stored
    ticker_data = ws_manager.get_ticker_data()
    assert ticker_data is not None
    assert ticker_data['last'] == 50000.0
    assert ticker_data['symbol'] == 'BTCUSDT'
    print("✓ WebSocket ticker processing works correctly")
    
    return True


def test_metrics_tracker():
    """Test MetricsTracker functionality."""
    print("Testing Metrics Tracker...")
    
    config = create_mock_config()
    managers = create_mock_managers()
    
    # Test initialization
    tracker = MetricsTracker(
        config=config,
        metrics_manager=managers['metrics_manager'],
        market_data_manager=managers['market_data_manager'],
        exchange_manager=managers['exchange_manager']
    )
    
    assert tracker.config == config
    assert tracker._stats['total_messages'] == 0
    print("✓ Metrics Tracker initialization successful")
    
    # Test message recording
    tracker.record_message(is_valid=True, is_delayed=False)
    tracker.record_message(is_valid=False, is_delayed=True)
    tracker.record_error()
    
    stats = tracker.get_stats()
    assert stats['total_messages'] == 2
    assert stats['invalid_messages'] == 1
    assert stats['delayed_messages'] == 1
    assert stats['error_count'] == 1
    print("✓ Message recording and statistics work correctly")
    
    return True


async def test_metrics_health_checks():
    """Test health monitoring functionality."""
    print("Testing health checks...")
    
    config = create_mock_config()
    managers = create_mock_managers()
    
    tracker = MetricsTracker(
        config=config,
        metrics_manager=managers['metrics_manager'],
        market_data_manager=managers['market_data_manager'],
        exchange_manager=managers['exchange_manager']
    )
    
    # Test system health check
    health = await tracker.check_system_health()
    assert 'status' in health
    assert 'components' in health
    assert 'timestamp' in health
    print("✓ System health check works correctly")
    
    # Test individual component checks
    exchange_health = await tracker.check_exchange_health()
    assert 'status' in exchange_health
    print("✓ Exchange health check works correctly")
    
    memory_health = await tracker.check_memory_usage()
    assert 'status' in memory_health
    # Memory check might fail on some systems, just check if we get a response
    if 'usage_percent' not in memory_health:
        print(f"Memory health response: {memory_health}")
        # If it's an error response, that's also valid behavior
        assert 'message' in memory_health or 'usage_percent' in memory_health
    print("✓ Memory health check works correctly")
    
    return True


async def run_all_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("Running Basic Integration Tests for Refactored Components")
    print("=" * 60)
    
    try:
        # Synchronous tests
        test_signal_processor()
        test_websocket_manager()
        test_metrics_tracker()
        
        # Asynchronous tests
        await test_signal_processing()
        await test_websocket_message_processing()
        await test_metrics_health_checks()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED! Refactored components are working correctly.")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.WARNING,  # Reduce logging noise during tests
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)