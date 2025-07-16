#!/usr/bin/env python3
"""
Test script for API optimizations:
1. Batch Price API
2. 30-second TTL caching
3. Smart intervals

This script tests the new optimizations to ensure they work correctly.
"""

import asyncio
import aiohttp
import time
import json
import logging
from typing import Dict, List, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class APIOptimizationTester:
    """Test the API optimizations."""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_batch_ticker_api(self) -> Dict[str, Any]:
        """Test the new batch ticker API endpoint."""
        logger.info("🔄 Testing Batch Ticker API...")
        
        test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"]
        
        # Test batch request
        batch_start = time.time()
        try:
            async with self.session.post(
                f"{self.base_url}/api/market/ticker/batch",
                json={
                    "symbols": test_symbols,
                    "exchange_id": "bybit"
                }
            ) as response:
                if response.status == 200:
                    batch_data = await response.json()
                    batch_time = time.time() - batch_start
                    
                    logger.info(f"✅ Batch API successful: {batch_data['successful']}/{batch_data['total_requested']} symbols")
                    logger.info(f"⏱️  Batch request time: {batch_time:.2f}s")
                    
                    # Test individual requests for comparison
                    individual_start = time.time()
                    individual_results = []
                    
                    for symbol in test_symbols:
                        try:
                            async with self.session.get(
                                f"{self.base_url}/api/market/ticker/{symbol}?exchange_id=bybit"
                            ) as ind_response:
                                if ind_response.status == 200:
                                    individual_results.append(await ind_response.json())
                        except Exception as e:
                            logger.warning(f"Individual request failed for {symbol}: {e}")
                    
                    individual_time = time.time() - individual_start
                    
                    logger.info(f"⏱️  Individual requests time: {individual_time:.2f}s")
                    logger.info(f"🚀 Speed improvement: {individual_time/batch_time:.1f}x faster")
                    
                    return {
                        "status": "success",
                        "batch_time": batch_time,
                        "individual_time": individual_time,
                        "speed_improvement": individual_time / batch_time,
                        "successful_symbols": batch_data['successful'],
                        "total_symbols": len(test_symbols)
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Batch API failed: {response.status} - {error_text}")
                    return {"status": "error", "message": error_text}
                    
        except Exception as e:
            logger.error(f"❌ Batch API test failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def test_caching_ttl(self) -> Dict[str, Any]:
        """Test the 30-second TTL caching."""
        logger.info("🔄 Testing 30-second TTL Caching...")
        
        symbol = "BTCUSDT"
        
        try:
            # First request
            start1 = time.time()
            async with self.session.get(
                f"{self.base_url}/api/market/ticker/{symbol}?exchange_id=bybit"
            ) as response1:
                if response1.status == 200:
                    data1 = await response1.json()
                    time1 = time.time() - start1
                    
                    # Immediate second request (should be cached)
                    start2 = time.time()
                    async with self.session.get(
                        f"{self.base_url}/api/market/ticker/{symbol}?exchange_id=bybit"
                    ) as response2:
                        if response2.status == 200:
                            data2 = await response2.json()
                            time2 = time.time() - start2
                            
                            # Check if second request was faster (cached)
                            cache_speedup = time1 / time2 if time2 > 0 else float('inf')
                            
                            logger.info(f"⏱️  First request: {time1:.3f}s")
                            logger.info(f"⏱️  Second request: {time2:.3f}s")
                            logger.info(f"🚀 Cache speedup: {cache_speedup:.1f}x")
                            
                            # Wait 35 seconds to test TTL expiration
                            logger.info("⏳ Waiting 35 seconds to test TTL expiration...")
                            await asyncio.sleep(35)
                            
                            # Third request (should not be cached)
                            start3 = time.time()
                            async with self.session.get(
                                f"{self.base_url}/api/market/ticker/{symbol}?exchange_id=bybit"
                            ) as response3:
                                if response3.status == 200:
                                    data3 = await response3.json()
                                    time3 = time.time() - start3
                                    
                                    logger.info(f"⏱️  Third request (after TTL): {time3:.3f}s")
                                    
                                    return {
                                        "status": "success",
                                        "first_request_time": time1,
                                        "cached_request_time": time2,
                                        "expired_request_time": time3,
                                        "cache_speedup": cache_speedup,
                                        "ttl_working": time3 > time2 * 2  # Should be slower after TTL
                                    }
                                    
            return {"status": "error", "message": "Failed to complete caching test"}
            
        except Exception as e:
            logger.error(f"❌ Caching test failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def test_smart_intervals(self) -> Dict[str, Any]:
        """Test the smart intervals functionality."""
        logger.info("🔄 Testing Smart Intervals...")
        
        try:
            async with self.session.get(
                f"{self.base_url}/api/market/smart-intervals/status"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("status") == "active":
                        smart_intervals = data.get("smart_intervals", {})
                        current_intervals = data.get("current_intervals", {})
                        
                        logger.info(f"✅ Smart intervals active")
                        logger.info(f"📊 Activity level: {smart_intervals.get('activity_level', 'unknown')}")
                        logger.info(f"⏱️  Current interval: {smart_intervals.get('current_interval', 'unknown')}s")
                        logger.info(f"📈 Volume ratio: {smart_intervals.get('avg_volume_ratio', 'unknown')}")
                        logger.info(f"📉 Volatility: {smart_intervals.get('avg_volatility', 'unknown')}")
                        
                        # Check if intervals are within expected range (30-60s)
                        ticker_interval = current_intervals.get('ticker', 0)
                        intervals_valid = 30 <= ticker_interval <= 60
                        
                        logger.info(f"🎯 Ticker interval: {ticker_interval}s (valid: {intervals_valid})")
                        
                        return {
                            "status": "success",
                            "smart_intervals_active": True,
                            "activity_level": smart_intervals.get('activity_level'),
                            "current_interval": smart_intervals.get('current_interval'),
                            "ticker_interval": ticker_interval,
                            "intervals_valid": intervals_valid,
                            "stats": smart_intervals.get('stats', {})
                        }
                    else:
                        logger.warning("⚠️  Smart intervals not active")
                        return {
                            "status": "inactive",
                            "smart_intervals_active": False,
                            "message": data.get("smart_intervals", {}).get("message", "Unknown")
                        }
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Smart intervals API failed: {response.status} - {error_text}")
                    return {"status": "error", "message": error_text}
                    
        except Exception as e:
            logger.error(f"❌ Smart intervals test failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all optimization tests."""
        logger.info("🚀 Starting API Optimization Tests")
        logger.info("=" * 50)
        
        results = {}
        
        # Test 1: Batch Ticker API
        results["batch_api"] = await self.test_batch_ticker_api()
        logger.info("")
        
        # Test 2: Caching TTL
        results["caching"] = await self.test_caching_ttl()
        logger.info("")
        
        # Test 3: Smart Intervals
        results["smart_intervals"] = await self.test_smart_intervals()
        logger.info("")
        
        # Summary
        logger.info("📋 Test Summary")
        logger.info("=" * 50)
        
        for test_name, result in results.items():
            status = result.get("status", "unknown")
            if status == "success":
                logger.info(f"✅ {test_name.replace('_', ' ').title()}: PASSED")
            else:
                logger.info(f"❌ {test_name.replace('_', ' ').title()}: FAILED - {result.get('message', 'Unknown error')}")
        
        return results

async def main():
    """Main test function."""
    async with APIOptimizationTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results to file
        with open("api_optimization_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        logger.info("📁 Results saved to api_optimization_test_results.json")

if __name__ == "__main__":
    asyncio.run(main()) 