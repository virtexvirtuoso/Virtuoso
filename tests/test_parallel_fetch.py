#!/usr/bin/env python3
"""
Test script for parallel and bulk ticker fetching optimizations
"""

import asyncio
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_parallel_fetch():
    """Test the parallel fetch optimization"""
    print("\n" + "="*60)
    print("TESTING PARALLEL FETCH OPTIMIZATION")
    print("="*60)
    
    try:
        from src.core.market.top_symbols import TopSymbolsManager
        from src.core.exchanges.manager import ExchangeManager
        from src.core.di.container import DIContainer
        
        # Initialize DI container
        container = DIContainer()
        
        # Get exchange manager
        exchange_manager = await container.resolve(ExchangeManager)
        await exchange_manager.initialize()
        
        # Create top symbols manager
        top_symbols_manager = TopSymbolsManager(exchange_manager, {})
        
        # Test parallel fetch (new optimized version)
        print("\n📊 Testing PARALLEL fetch (optimized)...")
        start_time = time.time()
        
        symbols = await top_symbols_manager.get_top_symbols(limit=10)
        
        duration = time.time() - start_time
        print(f"✅ Parallel fetch completed in {duration:.2f} seconds")
        print(f"📈 Retrieved {len(symbols)} symbols")
        
        if symbols:
            print("\nTop 3 symbols:")
            for i, symbol_data in enumerate(symbols[:3], 1):
                print(f"  {i}. {symbol_data['symbol']}: "
                      f"${symbol_data['price']:.2f} "
                      f"({symbol_data['change_24h']:.2f}%)")
        
        return duration
        
    except Exception as e:
        print(f"❌ Error in parallel fetch test: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_bulk_fetch():
    """Test the bulk ticker fetch optimization"""
    print("\n" + "="*60)
    print("TESTING BULK TICKER FETCH OPTIMIZATION")
    print("="*60)
    
    try:
        from src.core.market.top_symbols import TopSymbolsManager
        from src.core.exchanges.manager import ExchangeManager
        from src.core.di.container import DIContainer
        
        # Initialize DI container
        container = DIContainer()
        
        # Get exchange manager
        exchange_manager = await container.resolve(ExchangeManager)
        await exchange_manager.initialize()
        
        # Create top symbols manager
        top_symbols_manager = TopSymbolsManager(exchange_manager, {})
        
        # Test bulk fetch (ultra-fast version)
        print("\n🚀 Testing BULK fetch (ultra-fast)...")
        start_time = time.time()
        
        symbols = await top_symbols_manager.get_top_symbols_bulk(limit=10)
        
        duration = time.time() - start_time
        print(f"✅ Bulk fetch completed in {duration:.2f} seconds")
        print(f"📈 Retrieved {len(symbols)} symbols")
        
        if symbols:
            print("\nTop 3 symbols:")
            for i, symbol_data in enumerate(symbols[:3], 1):
                print(f"  {i}. {symbol_data['symbol']}: "
                      f"${symbol_data['price']:.2f} "
                      f"({symbol_data['change_24h']:.2f}%)")
        
        return duration
        
    except Exception as e:
        print(f"❌ Error in bulk fetch test: {e}")
        import traceback
        traceback.print_exc()
        return None

async def compare_methods():
    """Compare all fetch methods"""
    print("\n" + "="*60)
    print("PERFORMANCE COMPARISON")
    print("="*60)
    
    # Test parallel fetch
    parallel_time = await test_parallel_fetch()
    
    # Test bulk fetch
    bulk_time = await test_bulk_fetch()
    
    # Summary
    print("\n" + "="*60)
    print("PERFORMANCE SUMMARY")
    print("="*60)
    
    if parallel_time:
        print(f"⚡ Parallel Fetch: {parallel_time:.2f} seconds")
    else:
        print("❌ Parallel Fetch: FAILED")
    
    if bulk_time:
        print(f"🚀 Bulk Fetch: {bulk_time:.2f} seconds")
    else:
        print("❌ Bulk Fetch: FAILED")
    
    if parallel_time and bulk_time:
        if bulk_time < parallel_time:
            improvement = ((parallel_time - bulk_time) / parallel_time) * 100
            print(f"\n✨ Bulk fetch is {improvement:.1f}% faster than parallel fetch!")
        else:
            print(f"\n⚠️ Parallel fetch performed better in this test")
    
    # Expected vs actual
    print("\n📊 Expected Performance:")
    print("  • Sequential (old): 15-30 seconds")
    print("  • Parallel (new): 2-3 seconds")
    print("  • Bulk (best): <1 second")

if __name__ == "__main__":
    print("\n🔧 Mobile Dashboard Performance Optimization Test")
    print("Testing parallel and bulk ticker fetching...")
    
    # Activate virtual environment reminder
    if not sys.prefix.endswith('venv311'):
        print("\n⚠️  WARNING: Not running in venv311")
        print("Run: source venv311/bin/activate")
    
    # Run tests
    asyncio.run(compare_methods())
    
    print("\n✅ Test complete!")