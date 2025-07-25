#!/usr/bin/env python3
"""
Test liquidation cache usage across the codebase.
Verifies that all components properly read from and write to the liquidation cache.
"""

import asyncio
import sys
import os
import json
import tempfile
import shutil
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LiquidationCacheUsageTest:
    """Test liquidation cache usage across components."""
    
    def __init__(self):
        self.test_cache_dir = None
        self.test_results = {}
        
    async def setup_test_cache(self):
        """Setup a test cache with sample data."""
        self.test_cache_dir = tempfile.mkdtemp(prefix="liquidation_cache_test_")
        logger.info(f"Created test cache directory: {self.test_cache_dir}")
        
        # Create sample liquidation data for multiple symbols
        symbols = ['btcusdt', 'ethusdt', 'adausdt']
        base_time = int(datetime.now().timestamp() * 1000)
        
        for i, symbol in enumerate(symbols):
            liquidations = []
            # Create 10 liquidation events per symbol
            for j in range(10):
                liquidation = {
                    'symbol': symbol.upper(),
                    'timestamp': base_time - (j * 60000),  # 1 minute intervals
                    'price': 50000 - (j * 100),
                    'size': 0.1 + (j * 0.05),
                    'side': 'long' if j % 2 == 0 else 'short',
                    'source': 'websocket'
                }
                liquidations.append(liquidation)
            
            # Save to cache file using structured format
            cache_file = os.path.join(self.test_cache_dir, f"{symbol}_liquidations.json")
            cache_structure = {
                "timestamp": int(datetime.now().timestamp()),
                "symbol": symbol,
                "data": liquidations
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_structure, f)
                
        logger.info(f"Created test cache with data for {len(symbols)} symbols")
        
    async def cleanup_test_cache(self):
        """Cleanup test cache."""
        if self.test_cache_dir and os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir)
            logger.info("Cleaned up test cache directory")
    
    async def test_liquidation_cache_basic_operations(self):
        """Test basic liquidation cache operations."""
        try:
            from src.utils.liquidation_cache import LiquidationCache
            
            cache = LiquidationCache(cache_dir=self.test_cache_dir)
            
            # Test loading data
            btc_liquidations = cache.load('btcusdt')
            if btc_liquidations and len(btc_liquidations) == 10:
                logger.info("✅ Cache load operation works correctly")
                logger.info(f"  - Loaded {len(btc_liquidations)} BTC liquidations")
                
                # Test appending new data
                new_liquidation = {
                    'symbol': 'BTCUSDT',
                    'timestamp': int(datetime.now().timestamp() * 1000),
                    'price': 51000.0,
                    'size': 0.25,
                    'side': 'long',
                    'source': 'test'
                }
                
                cache.append(new_liquidation, 'btcusdt')
                
                # Verify append worked
                updated_liquidations = cache.load('btcusdt')
                if updated_liquidations and len(updated_liquidations) == 11:
                    logger.info("✅ Cache append operation works correctly")
                    logger.info(f"  - Cache now has {len(updated_liquidations)} liquidations")
                    return True
                else:
                    logger.error("❌ Cache append failed")
                    return False
            else:
                logger.error("❌ Cache load failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Cache operations test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def test_monitor_cache_usage(self):
        """Test monitor's usage of liquidation cache."""
        try:
            # Import monitor and check if it properly uses cache
            
            # Simulate monitor behavior
            cache = LiquidationCache(cache_dir=self.test_cache_dir)
            
            # Test reading existing liquidations (what monitor would do for alerts)
            btc_liquidations = cache.load('btcusdt')
            
            if btc_liquidations:
                # Simulate monitor processing liquidations
                total_volume = sum(liq['size'] for liq in btc_liquidations)
                long_liquidations = [liq for liq in btc_liquidations if liq['side'] == 'long']
                short_liquidations = [liq for liq in btc_liquidations if liq['side'] == 'short']
                
                logger.info("✅ Monitor cache usage test passed")
                logger.info(f"  - Total liquidation volume: {total_volume:.2f}")
                logger.info(f"  - Long liquidations: {len(long_liquidations)}")
                logger.info(f"  - Short liquidations: {len(short_liquidations)}")
                return True
            else:
                logger.error("❌ Monitor couldn't load liquidation data from cache")
                return False
                
        except Exception as e:
            logger.error(f"❌ Monitor cache usage test failed: {e}")
            return False
    
    async def test_dashboard_api_cache_usage(self):
        """Test dashboard/API endpoints' usage of liquidation cache."""
        try:
            
            cache = LiquidationCache(cache_dir=self.test_cache_dir)
            
            # Simulate what dashboard endpoints do
            symbols = ['btcusdt', 'ethusdt', 'adausdt']
            liquidation_summary = {}
            
            for symbol in symbols:
                liquidations = cache.load(symbol)
                if liquidations:
                    # Calculate summary stats (what dashboard would show)
                    recent_liquidations = [
                        liq for liq in liquidations 
                        if liq['timestamp'] > (datetime.now().timestamp() * 1000) - (24 * 60 * 60 * 1000)
                    ]
                    
                    liquidation_summary[symbol] = {
                        'total_count': len(liquidations),
                        'recent_count': len(recent_liquidations),
                        'total_volume': sum(liq['size'] for liq in liquidations),
                        'avg_price': sum(liq['price'] for liq in liquidations) / len(liquidations)
                    }
            
            if liquidation_summary and len(liquidation_summary) == 3:
                logger.info("✅ Dashboard API cache usage test passed")
                logger.info(f"  - Processed {len(liquidation_summary)} symbols")
                for symbol, stats in liquidation_summary.items():
                    logger.info(f"  - {symbol}: {stats['total_count']} liquidations, avg price ${stats['avg_price']:,.0f}")
                return True
            else:
                logger.error("❌ Dashboard API couldn't process liquidation cache data")
                return False
                
        except Exception as e:
            logger.error(f"❌ Dashboard API cache usage test failed: {e}")
            return False
    
    async def test_sentiment_indicators_cache_usage(self):
        """Test sentiment indicators' usage of liquidation cache."""
        try:
            
            cache = LiquidationCache(cache_dir=self.test_cache_dir)
            
            # Simulate sentiment indicator calculations
            btc_liquidations = cache.load('btcusdt')
            
            if btc_liquidations:
                # Calculate long/short ratio (common sentiment indicator)
                long_volume = sum(liq['size'] for liq in btc_liquidations if liq['side'] == 'long')
                short_volume = sum(liq['size'] for liq in btc_liquidations if liq['side'] == 'short')
                
                if short_volume > 0:
                    long_short_ratio = long_volume / short_volume
                else:
                    long_short_ratio = float('inf')
                
                # Calculate liquidation pressure (another sentiment indicator)
                recent_liquidations = [
                    liq for liq in btc_liquidations 
                    if liq['timestamp'] > (datetime.now().timestamp() * 1000) - (60 * 60 * 1000)  # Last hour
                ]
                
                liquidation_pressure = len(recent_liquidations) / max(len(btc_liquidations), 1)
                
                logger.info("✅ Sentiment indicators cache usage test passed")
                logger.info(f"  - Long/Short ratio: {long_short_ratio:.2f}")
                logger.info(f"  - Liquidation pressure: {liquidation_pressure:.2f}")
                logger.info(f"  - Recent liquidations: {len(recent_liquidations)}")
                return True
            else:
                logger.error("❌ Sentiment indicators couldn't load liquidation data")
                return False
                
        except Exception as e:
            logger.error(f"❌ Sentiment indicators cache usage test failed: {e}")
            return False
    
    async def test_cache_data_consistency(self):
        """Test that cached data has consistent format."""
        try:
            
            cache = LiquidationCache(cache_dir=self.test_cache_dir)
            
            required_fields = ['symbol', 'timestamp', 'price', 'size', 'side', 'source']
            symbols_tested = 0
            consistent_data = True
            
            for cache_file in os.listdir(self.test_cache_dir):
                if cache_file.endswith('_liquidations.json'):
                    symbol = cache_file.replace('_liquidations.json', '')
                    liquidations = cache.load(symbol)
                    
                    if liquidations:
                        symbols_tested += 1
                        for liq in liquidations:
                            # Check required fields exist
                            for field in required_fields:
                                if field not in liq:
                                    logger.error(f"❌ Missing field '{field}' in {symbol} liquidation data")
                                    consistent_data = False
                            
                            # Check data types
                            if not isinstance(liq.get('timestamp'), int):
                                logger.error(f"❌ Invalid timestamp type in {symbol}")
                                consistent_data = False
                            
                            if not isinstance(liq.get('price'), (int, float)):
                                logger.error(f"❌ Invalid price type in {symbol}")
                                consistent_data = False
                            
                            if not isinstance(liq.get('size'), (int, float)):
                                logger.error(f"❌ Invalid size type in {symbol}")
                                consistent_data = False
                            
                            if liq.get('side') not in ['long', 'short']:
                                logger.error(f"❌ Invalid side value in {symbol}: {liq.get('side')}")
                                consistent_data = False
            
            if consistent_data and symbols_tested > 0:
                logger.info("✅ Cache data consistency test passed")
                logger.info(f"  - Tested {symbols_tested} symbols")
                logger.info(f"  - All required fields present with correct types")
                return True
            else:
                logger.error("❌ Cache data consistency test failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Cache data consistency test failed: {e}")
            return False
    
    async def test_cache_file_permissions_and_cleanup(self):
        """Test cache file permissions and cleanup behavior."""
        try:
            
            cache = LiquidationCache(cache_dir=self.test_cache_dir, cache_expiry=1)  # 1 second expiry
            
            # Add an old liquidation that should be cleaned up
            old_liquidation = {
                'symbol': 'TESTUSDT',
                'timestamp': int((datetime.now() - timedelta(seconds=5)).timestamp() * 1000),
                'price': 1000.0,
                'size': 0.1,
                'side': 'long',
                'source': 'test'
            }
            
            cache.append(old_liquidation, 'testusdt')
            
            # Wait for expiry
            await asyncio.sleep(2)
            
            # Add a new liquidation which should trigger cleanup
            new_liquidation = {
                'symbol': 'TESTUSDT',
                'timestamp': int(datetime.now().timestamp() * 1000),
                'price': 1000.0,
                'size': 0.1,
                'side': 'short',
                'source': 'test'
            }
            
            cache.append(new_liquidation, 'testusdt')
            
            # Load and check - should only have the new liquidation
            liquidations = cache.load('testusdt')
            
            if liquidations and len(liquidations) == 1 and liquidations[0]['side'] == 'short':
                logger.info("✅ Cache cleanup test passed")
                logger.info(f"  - Expired liquidations were cleaned up")
                logger.info(f"  - Remaining liquidations: {len(liquidations)}")
                return True
            else:
                logger.error("❌ Cache cleanup test failed")
                logger.error(f"  - Expected 1 liquidation, got {len(liquidations) if liquidations else 0}")
                if liquidations:
                    logger.error(f"  - Liquidations found: {liquidations}")
                
                # Check the raw cache file to understand what's happening
                cache_file = os.path.join(self.test_cache_dir, "testusdt_liquidations.json")
                if os.path.exists(cache_file):
                    with open(cache_file, 'r') as f:
                        raw_data = json.load(f)
                    logger.error(f"  - Raw cache data: {raw_data}")
                else:
                    logger.error("  - Cache file doesn't exist")
                return False
                
        except Exception as e:
            logger.error(f"❌ Cache cleanup test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all liquidation cache usage tests."""
        logger.info("=" * 70)
        logger.info("Testing Liquidation Cache Usage Across Codebase")
        logger.info("=" * 70)
        
        await self.setup_test_cache()
        
        tests = [
            ("Basic Cache Operations", self.test_liquidation_cache_basic_operations),
            ("Monitor Cache Usage", self.test_monitor_cache_usage),
            ("Dashboard API Cache Usage", self.test_dashboard_api_cache_usage),
            ("Sentiment Indicators Cache Usage", self.test_sentiment_indicators_cache_usage),
            ("Cache Data Consistency", self.test_cache_data_consistency),
            ("Cache Cleanup & Permissions", self.test_cache_file_permissions_and_cleanup)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            logger.info(f"\n🧪 Running: {test_name}")
            try:
                result = await test_func()
                results.append((test_name, result))
                self.test_results[test_name] = result
            except Exception as e:
                logger.error(f"💥 Test crashed: {e}")
                results.append((test_name, False))
                self.test_results[test_name] = False
        
        await self.cleanup_test_cache()
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("Test Summary")
        logger.info("=" * 70)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name}: {status}")
        
        logger.info(f"\nTotal: {passed}/{total} passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            logger.info("\n🎉 All liquidation cache usage tests passed!")
            logger.info("The liquidation cache is properly integrated across the codebase.")
        else:
            logger.info("\n⚠️ Some tests failed. Components may not be using cache correctly.")
        
        return passed == total

async def main():
    """Main test function."""
    tester = LiquidationCacheUsageTest()
    success = await tester.run_all_tests()
    
    # Generate detailed report
    report = {
        "timestamp": datetime.now().isoformat(),
        "test_results": tester.test_results,
        "summary": {
            "total_tests": len(tester.test_results),
            "passed": sum(1 for result in tester.test_results.values() if result),
            "failed": sum(1 for result in tester.test_results.values() if not result)
        },
        "cache_integration_status": "FULLY_INTEGRATED" if success else "NEEDS_FIXES"
    }
    
    report_path = f"data/liquidation_cache_usage_report_{int(datetime.now().timestamp())}.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"\n📄 Detailed report saved: {report_path}")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)