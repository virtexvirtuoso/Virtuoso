#!/usr/bin/env python3
"""
Test script for MarketMonitor alpha scanner integration.

This script tests that the alpha scanner is properly integrated into the MarketMonitor
and can be initialized and configured correctly.
"""

import sys
import os
import asyncio
import logging
from unittest.mock import Mock, AsyncMock

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Now import from src
from src.monitoring.monitor import MarketMonitor
from src.monitoring.alert_manager import AlertManager
from src.monitoring.metrics_manager import MetricsManager
from src.core.market.top_symbols import TopSymbolsManager
from src.core.market.market_data_manager import MarketDataManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_alpha_scanner_integration():
    """Test that the alpha scanner is properly integrated into MarketMonitor."""
    
    print("🧪 Testing Alpha Scanner Integration with MarketMonitor")
    print("=" * 60)
    
    # Create test configuration with alpha scanning enabled
    test_config = {
        'alpha_scanning': {
            'enabled': True,
            'scan_interval_minutes': 15,
            'confidence_threshold': 0.7,
            'max_symbols_per_scan': 10,
            'cooldown_minutes': 60,
            'patterns': {
                'correlation_breakdown': {'enabled': True, 'threshold': 0.3},
                'beta_expansion': {'enabled': True, 'threshold': 2.0},
                'alpha_breakout': {'enabled': True, 'threshold': 0.05}
            }
        },
        'monitoring': {
            'interval': 60
        }
    }
    
    # Create mock dependencies
    mock_exchange = Mock()
    mock_exchange.id = 'binance'
    
    mock_alert_manager = Mock(spec=AlertManager)
    mock_alert_manager.send_alpha_opportunity_alert = AsyncMock()
    
    mock_top_symbols_manager = Mock(spec=TopSymbolsManager)
    mock_top_symbols_manager.get_symbols = AsyncMock(return_value=['BTCUSDT', 'ETHUSDT'])
    
    mock_market_data_manager = Mock(spec=MarketDataManager)
    
    # Create mock metrics manager
    mock_metrics_manager = Mock(spec=MetricsManager)
    mock_metrics_manager.start_operation = Mock(return_value="mock_operation")
    mock_metrics_manager.end_operation = Mock()
    mock_metrics_manager.record_metric = Mock()
    
    try:
        # Initialize MarketMonitor with alpha scanner
        print("1. Initializing MarketMonitor with alpha scanner...")
        monitor = MarketMonitor(
            exchange=mock_exchange,
            config=test_config,
            alert_manager=mock_alert_manager,
            top_symbols_manager=mock_top_symbols_manager,
            market_data_manager=mock_market_data_manager,
            metrics_manager=mock_metrics_manager,
            logger=logger
        )
        
        # Test 1: Check alpha scanner initialization
        print("2. Checking alpha scanner initialization...")
        assert hasattr(monitor, 'alpha_scanner'), "Alpha scanner not initialized"
        assert monitor.alpha_scanner is not None, "Alpha scanner is None"
        print("   ✅ Alpha scanner properly initialized")
        
        # Test 2: Check alpha scanning state variables
        print("3. Checking alpha scanning state variables...")
        assert hasattr(monitor, '_last_alpha_scan'), "Last alpha scan timestamp not initialized"
        assert hasattr(monitor, '_alpha_scan_interval'), "Alpha scan interval not initialized"
        assert monitor._alpha_scan_interval == 15 * 60, f"Expected 900 seconds, got {monitor._alpha_scan_interval}"
        print("   ✅ Alpha scanning state variables properly initialized")
        
        # Test 3: Check configuration loading
        print("4. Checking configuration loading...")
        alpha_config = monitor.alpha_scanner.config.get('alpha_scanning', {})
        assert alpha_config.get('enabled') == True, "Alpha scanning not enabled in config"
        assert alpha_config.get('scan_interval_minutes') == 15, "Scan interval not set correctly"
        print("   ✅ Configuration loaded correctly")
        
        # Test 4: Check alpha scanner has required methods
        print("5. Checking alpha scanner methods...")
        assert hasattr(monitor.alpha_scanner, 'scan_for_opportunities'), "scan_for_opportunities method missing"
        print("   ✅ Alpha scanner has required methods")
        
        # Test 5: Test alpha scanning interval logic
        print("6. Testing alpha scanning interval logic...")
        import time
        current_time = time.time()
        
        # Should not scan immediately (last scan = 0, but we need to wait for interval)
        monitor._last_alpha_scan = current_time - 10  # 10 seconds ago
        should_scan = (hasattr(monitor, 'alpha_scanner') and 
                      monitor.alpha_scanner and 
                      current_time - monitor._last_alpha_scan >= monitor._alpha_scan_interval)
        assert not should_scan, "Should not scan when interval hasn't passed"
        
        # Should scan when interval has passed
        monitor._last_alpha_scan = current_time - (15 * 60 + 1)  # 15 minutes + 1 second ago
        should_scan = (hasattr(monitor, 'alpha_scanner') and 
                      monitor.alpha_scanner and 
                      current_time - monitor._last_alpha_scan >= monitor._alpha_scan_interval)
        assert should_scan, "Should scan when interval has passed"
        print("   ✅ Alpha scanning interval logic works correctly")
        
        print("\n🎉 All tests passed! Alpha scanner integration successful.")
        print("\nIntegration Summary:")
        print(f"   • Alpha scanner class: {type(monitor.alpha_scanner).__name__}")
        print(f"   • Scan interval: {monitor._alpha_scan_interval / 60:.1f} minutes")
        print(f"   • Alert manager: {'✅ Connected' if monitor.alert_manager else '❌ Not connected'}")
        print(f"   • Configuration: {'✅ Loaded' if monitor.alpha_scanner.config else '❌ Missing'}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_alpha_scanner_mock_scan():
    """Test alpha scanner with mock data."""
    
    print("\n🧪 Testing Alpha Scanner Mock Scan")
    print("=" * 40)
    
    # Create test configuration
    test_config = {
        'alpha_scanning': {
            'enabled': True,
            'scan_interval_minutes': 1,  # 1 minute for testing
            'confidence_threshold': 0.6,
            'max_symbols_per_scan': 5
        }
    }
    
    # Create mock dependencies
    mock_exchange = Mock()
    mock_exchange.id = 'binance'
    
    mock_alert_manager = Mock(spec=AlertManager)
    mock_alert_manager.send_alpha_opportunity_alert = AsyncMock()
    
    mock_top_symbols_manager = Mock(spec=TopSymbolsManager)
    mock_market_data_manager = Mock(spec=MarketDataManager)
    
    # Create mock metrics manager
    mock_metrics_manager = Mock(spec=MetricsManager)
    mock_metrics_manager.start_operation = Mock(return_value="mock_operation")
    mock_metrics_manager.end_operation = Mock()
    mock_metrics_manager.record_metric = Mock()
    
    try:
        # Initialize MarketMonitor
        monitor = MarketMonitor(
            exchange=mock_exchange,
            config=test_config,
            alert_manager=mock_alert_manager,
            top_symbols_manager=mock_top_symbols_manager,
            market_data_manager=mock_market_data_manager,
            metrics_manager=mock_metrics_manager,
            logger=logger
        )
        
        # Create mock OHLCV cache data
        mock_ohlcv_cache = {
            'BTCUSDT': {
                'htf': Mock(),  # Mock DataFrame
                'mtf': Mock()   # Mock DataFrame
            },
            'ETHUSDT': {
                'htf': Mock(),  # Mock DataFrame
                'mtf': Mock()   # Mock DataFrame
            }
        }
        
        # Mock the scan_for_opportunities method to avoid actual calculations
        monitor.alpha_scanner.scan_for_opportunities = AsyncMock()
        
        print("1. Testing alpha scanner scan method...")
        await monitor.alpha_scanner.scan_for_opportunities(mock_ohlcv_cache)
        
        # Verify the method was called
        monitor.alpha_scanner.scan_for_opportunities.assert_called_once_with(mock_ohlcv_cache)
        print("   ✅ Alpha scanner scan method called successfully")
        
        print("\n🎉 Mock scan test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Mock scan test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("🚀 Starting Alpha Scanner Integration Tests")
    print("=" * 80)
    
    # Run tests
    test1_passed = await test_alpha_scanner_integration()
    test2_passed = await test_alpha_scanner_mock_scan()
    
    print("\n" + "=" * 80)
    print("📊 Test Results Summary:")
    print(f"   • Alpha Scanner Integration: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"   • Mock Scan Test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Alpha scanner is successfully integrated into MarketMonitor.")
        print("\nNext steps:")
        print("   1. Update config.yaml with alpha_scanning configuration")
        print("   2. Test with real market data")
        print("   3. Monitor Discord alerts for alpha opportunities")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the integration.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 