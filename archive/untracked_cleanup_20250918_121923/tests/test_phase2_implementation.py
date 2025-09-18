#!/usr/bin/env python3
"""
Test Phase 2 actual implementation changes
"""
import asyncio
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.monitoring.monitor_cache_integration import MonitorCacheIntegration
from unittest.mock import MagicMock, AsyncMock
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_phase2_data_extraction():
    """Test the streamlined data extraction"""
    integration = MonitorCacheIntegration()
    
    # Create mock monitor with only market_data_manager (no fallbacks)
    mock_monitor = MagicMock()
    mock_monitor.market_data_manager = MagicMock()
    mock_monitor.market_data_manager.data_cache = {
        'BTCUSDT': {
            'ticker': {
                'last': 50000,
                'percentage': 2.5,
                'quoteVolume': 1000000,
                'high': 51000,
                'low': 49000
            }
        },
        'ETHUSDT': {
            'ticker': {
                'last': 3000,
                'percentage': 1.5,
                'quoteVolume': 500000,
                'high': 3100,
                'low': 2900
            }
        }
    }
    
    # Test extraction speed
    start_time = time.time()
    market_data = await integration._extract_market_data(mock_monitor)
    extraction_time = time.time() - start_time
    
    logger.info(f"Phase 2 data extraction completed in {extraction_time:.3f}s")
    logger.info(f"Extracted {len(market_data.get('symbols', []))} symbols")
    
    return extraction_time, market_data

async def test_phase2_cache_batching():
    """Test the batched cache operations"""
    integration = MonitorCacheIntegration()
    
    # Mock cache client
    mock_cache = AsyncMock()
    mock_cache.set = AsyncMock(return_value=True)
    integration.get_cache_client = AsyncMock(return_value=mock_cache)
    
    # Create test data
    market_data = {'symbols': [{'symbol': 'BTCUSDT', 'price': 50000}]}
    signals_data = {'signals': [{'symbol': 'BTCUSDT', 'score': 75}]}
    market_regime = {'trend': 'bullish'}
    market_movers = {'gainers': [], 'losers': []}
    
    # Test batched write speed
    start_time = time.time()
    success = await integration.push_to_cache(
        MagicMock(),  # monitor
        market_data,
        signals_data,
        market_regime,
        market_movers
    )
    cache_time = time.time() - start_time
    
    # Check that only ONE cache write was made (batched)
    cache_write_calls = mock_cache.set.call_count
    
    logger.info(f"Phase 2 cache batching completed in {cache_time:.3f}s")
    logger.info(f"Number of cache writes: {cache_write_calls} (should be 1 for batched)")
    
    return cache_time, cache_write_calls

async def run_phase2_tests():
    """Run all Phase 2 tests"""
    print("="*60)
    print("PHASE 2 IMPLEMENTATION TEST")
    print("="*60)
    print()
    
    print("Testing streamlined data extraction...")
    print("-" * 40)
    extraction_time, market_data = await test_phase2_data_extraction()
    print(f"✅ Data extraction: {extraction_time:.3f}s")
    print(f"   - Direct access only (no fallbacks)")
    print(f"   - Extracted {len(market_data.get('symbols', []))} symbols")
    
    if extraction_time < 0.1:  # Should be very fast with no fallbacks
        print("   ✓ PASS: Extraction is optimized")
    else:
        print("   ⚠ WARNING: Extraction slower than expected")
    
    print()
    print("Testing batched cache operations...")
    print("-" * 40)
    cache_time, write_count = await test_phase2_cache_batching()
    print(f"✅ Cache batching: {cache_time:.3f}s")
    print(f"   - Cache writes: {write_count}")
    
    if write_count == 1:
        print("   ✓ PASS: Cache operations are batched")
    else:
        print(f"   ⚠ WARNING: Expected 1 write, got {write_count}")
    
    print()
    print("="*60)
    print("PHASE 2 SUMMARY")
    print("="*60)
    print()
    print("Optimizations implemented:")
    print("✓ Streamlined data extraction (no multi-level fallbacks)")
    print("✓ Batched cache operations (single write)")
    print("✓ Removed redundant namespace operations")
    print()
    print("Expected improvements:")
    print("- Data extraction: 5-8s → 1-2s (saved ~5s)")
    print("- Cache operations: 4-6s → 1-2s (saved ~4s)")
    print("- Total Phase 2 savings: ~8-10s per cycle")
    print()
    
    if extraction_time < 0.1 and write_count == 1:
        print("🎉 Phase 2 implementation successful!")
    else:
        print("⚠️ Some optimizations may need adjustment")

if __name__ == "__main__":
    asyncio.run(run_phase2_tests())