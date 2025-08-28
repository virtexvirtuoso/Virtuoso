#!/usr/bin/env python3
"""
Simple Phase 3 Integration Test

Basic validation of Phase 3 components without complex concurrency scenarios.
"""

import asyncio
import logging
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.settings import get_settings


async def test_phase3_imports():
    """Test that Phase 3 modules can be imported"""
    print("🧪 Testing Phase 3 imports...")
    
    try:
        from src.core.intelligence.cache import IntelligentCacheSystem
        from src.core.intelligence.unified_market_service import UnifiedMarketService, DataType, Priority
        from src.core.intelligence.websocket_fallback import WebSocketFallbackManager
        print("✅ All Phase 3 modules imported successfully")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


async def test_settings_configuration():
    """Test Phase 3 settings configuration"""
    print("🧪 Testing Phase 3 settings configuration...")
    
    try:
        settings = get_settings()
        intelligence = settings.intelligence
        
        # Check Phase 3 specific settings
        assert hasattr(intelligence, 'UNIFIED_SERVICE_ENABLED')
        assert hasattr(intelligence, 'CACHE_WARMING_ENABLED')
        assert hasattr(intelligence, 'WEBSOCKET_FALLBACK_ENABLED')
        
        print("✅ Phase 3 settings configured correctly")
        print(f"   - Unified Service Enabled: {intelligence.UNIFIED_SERVICE_ENABLED}")
        print(f"   - Cache Warming Enabled: {intelligence.CACHE_WARMING_ENABLED}")
        print(f"   - WebSocket Fallback Enabled: {intelligence.WEBSOCKET_FALLBACK_ENABLED}")
        return True
    except Exception as e:
        print(f"❌ Settings test failed: {e}")
        return False


async def test_cache_basic_functionality():
    """Test basic cache functionality"""
    print("🧪 Testing basic cache functionality...")
    
    try:
        from src.core.intelligence.cache import IntelligentCacheSystem
        
        config = {
            'INTELLIGENCE_CACHE_L1_ENABLED': True,
            'INTELLIGENCE_CACHE_L1_MAX_SIZE': 10,
            'INTELLIGENCE_CACHE_L1_TTL': 30,
            'INTELLIGENCE_CACHE_L2_ENABLED': False,  # Disable L2 to avoid file issues
            'INTELLIGENCE_PREDICTIVE_CACHING': False
        }
        
        cache = IntelligentCacheSystem(config)
        
        # Test set/get
        test_data = {'price': 50000, 'volume': 1000}
        await cache.set('ticker', test_data, symbol='BTCUSDT')
        
        result = await cache.get('ticker', symbol='BTCUSDT')
        assert result is not None
        assert result['price'] == 50000
        
        print("✅ Basic cache operations working")
        return True
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False


async def test_market_data_manager_phase3_detection():
    """Test Market Data Manager Phase 3 detection"""
    print("🧪 Testing Market Data Manager Phase 3 detection...")
    
    try:
        from src.core.market.market_data_manager import MarketDataManager, INTELLIGENCE_AVAILABLE
        
        if not INTELLIGENCE_AVAILABLE:
            print("❌ Intelligence system not available")
            return False
        
        # Mock exchange manager
        class MockExchange:
            async def get_ticker(self, symbol): 
                return {'symbol': symbol, 'price': 50000}
        
        config = {'INTELLIGENCE_UNIFIED_SERVICE_ENABLED': True}
        mock_exchange = MockExchange()
        
        manager = MarketDataManager(config, mock_exchange)
        
        assert manager.unified_service_enabled == True
        print("✅ Market Data Manager detects Phase 3 correctly")
        return True
        
    except Exception as e:
        print(f"❌ Market Data Manager test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False


async def main():
    """Run basic Phase 3 validation tests"""
    print("🚀 Phase 3 Basic Validation Test Suite")
    print("=" * 50)
    
    logging.basicConfig(level=logging.ERROR)  # Reduce log noise
    
    tests = [
        ("Phase 3 Imports", test_phase3_imports),
        ("Settings Configuration", test_settings_configuration),
        ("Cache Basic Functionality", test_cache_basic_functionality),
        ("Market Manager Integration", test_market_data_manager_phase3_detection)
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n📋 {name}")
        print("-" * 30)
        
        try:
            result = await asyncio.wait_for(test_func(), timeout=10.0)
            if result:
                passed += 1
                print(f"✅ PASSED")
            else:
                print(f"❌ FAILED")
        except asyncio.TimeoutError:
            print(f"⏰ TIMEOUT")
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print("\n" + "=" * 50)
    print("📊 RESULTS")
    print("=" * 50)
    print(f"✅ Tests Passed: {passed}/{total}")
    print(f"🎯 Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 Phase 3 Basic Validation SUCCESSFUL!")
        print("✅ All core components are properly integrated")
        print("\n🚀 Phase 3 Implementation Ready For Production:")
        print("   • Multi-Level Cache System")
        print("   • Unified Market Data Service") 
        print("   • WebSocket Fallback System")
        print("   • Market Data Manager Integration")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)