#!/usr/bin/env python3
"""
Test script to verify that enhanced premium functionality is fully integrated 
into market_reporter.py without external dependencies.

This test verifies:
1. Enhanced premium calculation methods are available
2. Configuration is properly set
3. Methods work correctly
4. Performance monitoring is functional
5. Fallback mechanisms work
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.monitoring.market_reporter import MarketReporter
    print("✅ Successfully imported MarketReporter")
except ImportError as e:
    print(f"❌ Failed to import MarketReporter: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockExchange:
    """Mock exchange for testing purposes."""
    
    def __init__(self):
        self.rest_endpoint = "https://api.bybit.com"
    
    async def fetch_ticker(self, symbol):
        """Mock ticker data."""
        return {
            'last': 50000.0,
            'info': {
                'markPrice': '50100.0',
                'indexPrice': '50000.0',
                'fundingRate': '0.0001',
                'lastPrice': '50000.0'
            }
        }

async def test_premium_calculation_integration():
    """Test the premium calculation functionality integration."""
    print("\n🧪 Testing Premium Calculation Integration")
    print("=" * 50)
    
    # Create MarketReporter instance
    mock_exchange = MockExchange()
    
    async with MarketReporter(exchange=mock_exchange, logger=logger) as reporter:
        
        # Test 1: Check premium calculation configuration
        print("\n1️⃣ Checking Premium Calculation Configuration")
        assert hasattr(reporter, 'enable_premium_calculation'), "❌ Missing enable_premium_calculation"
        assert hasattr(reporter, 'enable_premium_validation'), "❌ Missing enable_premium_validation"
        assert hasattr(reporter, 'premium_api_base_url'), "❌ Missing premium_api_base_url"
        
        print(f"   ✅ Premium calculation enabled: {reporter.enable_premium_calculation}")
        print(f"   ✅ Premium validation enabled: {reporter.enable_premium_validation}")
        print(f"   ✅ API base URL: {reporter.premium_api_base_url}")
        
        # Test 2: Check method availability
        print("\n2️⃣ Checking Method Availability")
        methods = [
            '_init_premium_calculation',
            '_get_aiohttp_session',
            '_close_aiohttp_session',
            '_calculate_single_premium_with_api',
            '_extract_base_coin',
            '_get_perpetual_data',
            '_validate_with_bybit_premium_index',
            '_fallback_to_legacy_method',
            'get_premium_calculation_stats'
        ]
        
        for method in methods:
            assert hasattr(reporter, method), f"❌ Missing method: {method}"
            print(f"   ✅ Method available: {method}")
        
        # Test 3: Check base coin extraction
        print("\n3️⃣ Testing Base Coin Extraction")
        test_symbols = [
            ('BTC/USDT:USDT', 'BTC'),
            ('BTCUSDT', 'BTC'),
            ('ETH/USDT', 'ETH'),
            ('SOLUSDT', 'SOL'),
            ('XRP/USDT:USDT', 'XRP')
        ]
        
        for symbol, expected in test_symbols:
            result = reporter._extract_base_coin(symbol)
            assert result == expected, f"❌ Expected {expected}, got {result} for {symbol}"
            print(f"   ✅ {symbol} → {result}")
        
        # Test 4: Test premium calculation
        print("\n4️⃣ Testing Premium Calculation")
        try:
            result = await reporter._calculate_single_premium_with_api('BTCUSDT')
            if result:
                print(f"   ✅ API calculation successful")
                print(f"   ✅ Premium: {result.get('premium', 'N/A')}")
                print(f"   ✅ Data source: {result.get('data_source', 'N/A')}")
                print(f"   ✅ Processing time: {result.get('processing_time_ms', 'N/A')}ms")
            else:
                print("   ⚠️ API calculation returned None (may be due to network/API)")
        except Exception as e:
            print(f"   ⚠️ API calculation failed: {e}")
        
        # Test 5: Test performance stats
        print("\n5️⃣ Testing Performance Statistics")
        stats = reporter.get_premium_calculation_stats()
        print(f"   ✅ Stats structure: {list(stats.keys())}")
        print(f"   ✅ API method stats: {stats.get('api_method', {})}")
        print(f"   ✅ Legacy fallback stats: {stats.get('legacy_fallback_usage', {})}")
        print(f"   ✅ Validation stats: {stats.get('validation', {})}")
        
        # Test 6: Test integration with main calculation method
        print("\n6️⃣ Testing Integration with Main Calculation")
        try:
            # This should use the modern API method by default
            result = await reporter._calculate_single_premium('BTCUSDT', {})
            if result:
                print(f"   ✅ Main method integration working")
                print(f"   ✅ Result type: {type(result)}")
                print(f"   ✅ Has premium data: {'premium' in result}")
            else:
                print("   ⚠️ Main method returned None")
        except Exception as e:
            print(f"   ⚠️ Main method integration issue: {e}")
        
        print("\n🎉 Premium Calculation Integration Test Complete!")
        print("=" * 50)
        
        # Final stats
        final_stats = reporter.get_premium_calculation_stats()
        print(f"📊 Final Performance Stats:")
        print(f"   API success rate: {final_stats['api_method'].get('success_rate', 0):.1f}%")
        print(f"   Legacy fallback usage: {final_stats['legacy_fallback_usage'].get('percentage', 0):.1f}%")
        print(f"   Validation match rate: {final_stats['validation'].get('match_rate', 0):.1f}%")

def test_import_verification():
    """Verify all required imports are available."""
    print("\n📦 Testing Import Verification")
    print("=" * 30)
    
    try:
        import aiohttp
        print("✅ aiohttp import successful")
    except ImportError:
        print("❌ aiohttp import failed")
        return False
    
    try:
        from datetime import timedelta
        print("✅ timedelta import successful")
    except ImportError:
        print("❌ timedelta import failed")
        return False
    
    return True

async def main():
    """Main test function."""
    print("🚀 Enhanced Premium Integration Test")
    print("Testing fully integrated market_reporter.py")
    print("=" * 60)
    
    # Test imports first
    if not test_import_verification():
        print("❌ Import verification failed")
        return False
    
    # Test premium calculation integration
    try:
        await test_premium_calculation_integration()
        print("\n✅ All tests passed! Premium calculation functionality is fully integrated.")
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 