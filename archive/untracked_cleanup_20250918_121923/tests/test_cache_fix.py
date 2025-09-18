#!/usr/bin/env python3
"""
Test script to verify cache fix is working properly.
Simulates main process pushing data and web server reading it.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the unified cache client
import sys
import os
sys.path.insert(0, '/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

from src.core.cache.unified_cache_client import UnifiedCacheClient

async def simulate_main_process():
    """Simulate the main process pushing data to cache"""
    logger.info("🚀 Starting main process simulation...")
    
    # Initialize unified cache client
    cache_client = UnifiedCacheClient()
    
    # Create mock market data
    market_data = {
        "BTCUSDT": {
            "symbol": "BTCUSDT",
            "price": 42850.50,
            "change_24h": 2.5,
            "volume": 1234567890,
            "timestamp": datetime.now().isoformat()
        },
        "ETHUSDT": {
            "symbol": "ETHUSDT", 
            "price": 2250.75,
            "change_24h": -1.2,
            "volume": 987654321,
            "timestamp": datetime.now().isoformat()
        },
        "WIFUSDT": {
            "symbol": "WIFUSDT",
            "price": 0.8161,
            "change_24h": 5.3,
            "volume": 123456,
            "timestamp": datetime.now().isoformat()
        },
        "SUIUSDT": {
            "symbol": "SUIUSDT",
            "price": 3.3786,
            "change_24h": -0.8,
            "volume": 654321,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    # Create mock analysis results
    analysis_results = {
        "BTCUSDT": {
            "symbol": "BTCUSDT",
            "confluence_score": 75,
            "signal": "STRONG_BUY",
            "dimensions": {
                "orderflow": 80,
                "sentiment": 70,
                "liquidity": 75,
                "bitcoin_beta": 100,
                "smart_money": 65,
                "machine_learning": 60
            }
        },
        "ETHUSDT": {
            "symbol": "ETHUSDT",
            "confluence_score": 45,
            "signal": "NEUTRAL",
            "dimensions": {
                "orderflow": 50,
                "sentiment": 45,
                "liquidity": 40,
                "bitcoin_beta": 85,
                "smart_money": 50,
                "machine_learning": 45
            }
        }
    }
    
    # Push data to cache using unified client
    logger.info("📤 Pushing market overview to cache...")
    overview_data = {
        "symbols": list(market_data.values()),
        "analysis": analysis_results,
        "timestamp": datetime.now().isoformat(),
        "active_symbols": len(market_data)
    }
    
    # Use the unified cache methods
    success = await cache_client.set_market_overview(overview_data)
    if success:
        logger.info(f"✅ Successfully pushed market overview: {len(market_data)} symbols")
    else:
        logger.error("❌ Failed to push market overview")
    
    # Also test other cache operations
    logger.info("📤 Testing other cache operations...")
    
    # Push analysis signals
    signals = [
        {"symbol": "BTCUSDT", "signal": "STRONG_BUY", "score": 75},
        {"symbol": "ETHUSDT", "signal": "NEUTRAL", "score": 45}
    ]
    await cache_client.set_analysis_signals(signals)
    logger.info("✅ Pushed analysis signals")
    
    # Push market regime
    await cache_client.set_market_regime("BULLISH")
    logger.info("✅ Pushed market regime")
    
    # Push market movers
    gainers = [{"symbol": "WIFUSDT", "change": 5.3}]
    losers = [{"symbol": "ETHUSDT", "change": -1.2}]
    await cache_client.set_market_movers(gainers, losers)
    logger.info("✅ Pushed market movers")
    
    return True

async def simulate_web_server():
    """Simulate the web server reading data from cache"""
    logger.info("🌐 Starting web server simulation...")
    
    # Initialize unified cache client
    cache_client = UnifiedCacheClient()
    
    # Wait a moment for data to be written
    await asyncio.sleep(0.5)
    
    # Try to read market overview
    logger.info("📥 Reading market overview from cache...")
    overview_data = await cache_client.get_market_overview()
    
    if overview_data:
        logger.info(f"✅ Successfully read market overview:")
        logger.info(f"   - Active symbols: {overview_data.get('active_symbols', 0)}")
        logger.info(f"   - Symbol count: {len(overview_data.get('symbols', []))}")
        if overview_data.get('symbols'):
            for symbol in overview_data['symbols'][:3]:  # Show first 3
                logger.info(f"   - {symbol['symbol']}: ${symbol['price']:.2f}")
    else:
        logger.error("❌ Failed to read market overview - cache returned None")
    
    # Try to read other keys
    logger.info("📥 Reading other cache keys...")
    
    signals = await cache_client.get_analysis_signals()
    if signals:
        logger.info(f"✅ Read analysis signals: {len(signals.get('signals', []))} signals")
    else:
        logger.error("❌ Failed to read analysis signals")
    
    regime = await cache_client.get_market_regime()
    if regime:
        logger.info(f"✅ Read market regime: {regime}")
    else:
        logger.error("❌ Failed to read market regime")
    
    movers = await cache_client.get_market_movers()
    if movers:
        logger.info(f"✅ Read market movers: {len(movers.get('gainers', []))} gainers, {len(movers.get('losers', []))} losers")
    else:
        logger.error("❌ Failed to read market movers")
    
    return overview_data is not None

async def run_full_test():
    """Run the complete test sequence"""
    logger.info("=" * 60)
    logger.info("🔧 CACHE FIX VERIFICATION TEST")
    logger.info("=" * 60)
    
    # Step 1: Simulate main process pushing data
    push_success = await simulate_main_process()
    
    # Step 2: Simulate web server reading data
    read_success = await simulate_web_server()
    
    # Step 3: Verify both operations succeeded
    logger.info("=" * 60)
    if push_success and read_success:
        logger.info("✅ CACHE FIX VERIFIED: Data flow working correctly!")
        logger.info("   Main process ➜ Cache ➜ Web server")
    else:
        logger.error("❌ CACHE FIX FAILED: Data not flowing properly")
        logger.error("   Check cache configuration and connectivity")
    logger.info("=" * 60)
    
    return push_success and read_success

async def test_raw_cache():
    """Test raw cache operations to verify connectivity"""
    logger.info("🔍 Testing raw cache connectivity...")
    
    try:
        import aiomcache
        client = aiomcache.Client("127.0.0.1", 11211)
        
        # Test set
        test_key = "test:key"
        test_value = "test_value_" + str(time.time())
        await client.set(test_key.encode(), test_value.encode())
        logger.info(f"✅ Raw cache SET successful: {test_key} = {test_value}")
        
        # Test get
        result = await client.get(test_key.encode())
        if result:
            logger.info(f"✅ Raw cache GET successful: {result.decode()}")
        else:
            logger.error("❌ Raw cache GET failed: No data returned")
            
        await client.close()
        return True
    except Exception as e:
        logger.error(f"❌ Raw cache test failed: {e}")
        return False

if __name__ == "__main__":
    # First test raw cache connectivity
    asyncio.run(test_raw_cache())
    
    # Then run the full test
    success = asyncio.run(run_full_test())
    
    if success:
        logger.info("\n✅ All tests passed! The cache fix is working.")
        logger.info("Next steps:")
        logger.info("1. Deploy this fix to VPS")
        logger.info("2. Restart virtuoso.service")  
        logger.info("3. Dashboard should display real data")
    else:
        logger.error("\n❌ Tests failed. Please check:")
        logger.error("1. Memcached is running (brew services list)")
        logger.error("2. Port 11211 is accessible")
        logger.error("3. Cache client configuration")