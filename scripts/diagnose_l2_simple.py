"""
Simple L2 Cache Write Diagnostic
=================================

Minimal diagnostic script to test memcached writes without complex dependencies.
"""

import asyncio
import json
import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import aiomcache
except ImportError:
    logger.error("aiomcache not installed: pip install aiomcache")
    sys.exit(1)


async def test_memcached_basic():
    """Test basic memcached read/write"""
    print("\n" + "="*70)
    print("TEST 1: Basic Memcached Write/Read")
    print("="*70)

    try:
        client = aiomcache.Client('localhost', 11211)

        # Write test data
        test_key = b'test:diagnostic'
        test_data = {"test": "diagnostic", "timestamp": 12345}
        json_data = json.dumps(test_data).encode()

        logger.info(f"Writing to memcached...")
        await client.set(test_key, json_data, exptime=60)
        logger.info("✅ Write successful")

        # Read it back
        logger.info(f"Reading from memcached...")
        read_data = await client.get(test_key)

        if read_data:
            decoded = json.loads(read_data.decode())
            logger.info(f"✅ Read successful: {decoded}")
            return decoded == test_data
        else:
            logger.error("❌ No data read back")
            return False

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


async def test_analysis_signals_key():
    """Test reading analysis:signals key"""
    print("\n" + "="*70)
    print("TEST 2: Read Existing analysis:signals")
    print("="*70)

    try:
        client = aiomcache.Client('localhost', 11211)

        logger.info("Checking analysis:signals...")
        data = await client.get(b'analysis:signals')

        if data:
            try:
                decoded = json.loads(data.decode())
                signals = decoded.get('signals', decoded.get('recent_signals', []))
                logger.info(f"✅ Found analysis:signals with {len(signals)} signals")
                logger.info(f"   Keys: {list(decoded.keys())}")
                logger.info(f"   Status: {decoded.get('status', 'N/A')}")
                return True
            except Exception as e:
                logger.error(f"❌ Error decoding: {e}")
                logger.error(f"   Raw data (first 200 chars): {data[:200]}")
                return False
        else:
            logger.warning("⚠️  No data found for analysis:signals")
            return False

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


async def test_write_analysis_signals():
    """Test writing to analysis:signals key"""
    print("\n" + "="*70)
    print("TEST 3: Write to analysis:signals")
    print("="*70)

    try:
        client = aiomcache.Client('localhost', 11211)

        # Create test signal data in expected format
        test_data = {
            "signals": [
                {
                    "symbol": "TESTUSDT",
                    "confluence_score": 75.5,
                    "price": 999.99,
                    "sentiment": "BULLISH"
                }
            ],
            "total_signals": 1,
            "avg_score": 75.5,
            "timestamp": 1234567890,
            "status": "diagnostic_test"
        }

        json_data = json.dumps(test_data).encode()

        logger.info("Writing test data to analysis:signals...")
        await client.set(b'analysis:signals', json_data, exptime=120)
        logger.info("✅ Write successful")

        # Wait a moment
        await asyncio.sleep(0.2)

        # Read it back
        logger.info("Reading back analysis:signals...")
        read_data = await client.get(b'analysis:signals')

        if read_data:
            decoded = json.loads(read_data.decode())
            logger.info(f"✅ Read successful: {len(decoded.get('signals', []))} signals")
            logger.info(f"   Status: {decoded.get('status')}")
            return decoded.get('status') == 'diagnostic_test'
        else:
            logger.error("❌ No data read back")
            return False

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


async def test_memcached_stats():
    """Get memcached stats"""
    print("\n" + "="*70)
    print("TEST 4: Memcached Stats")
    print("="*70)

    try:
        client = aiomcache.Client('localhost', 11211)

        # Try to get stats (if supported)
        logger.info("Attempting to get memcached stats...")

        # Just check connection by doing a simple get
        await client.get(b'_health_check')
        logger.info("✅ Connection to memcached working")

        return True

    except Exception as e:
        logger.error(f"❌ Connection test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("SIMPLE L2 CACHE DIAGNOSTIC")
    print("="*70)

    results = []

    results.append(("Basic Memcached", await test_memcached_basic()))
    results.append(("Read analysis:signals", await test_analysis_signals_key()))
    results.append(("Write analysis:signals", await test_write_analysis_signals()))
    results.append(("Memcached Connection", await test_memcached_stats()))

    # Summary
    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print("="*70)
    print(f"TOTAL: {passed_count}/{total_count} tests passed")
    print("="*70)


if __name__ == '__main__':
    asyncio.run(main())
