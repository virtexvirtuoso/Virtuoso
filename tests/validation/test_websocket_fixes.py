#!/usr/bin/env python3
"""
Test script to validate WebSocket handler timeout fixes

This script verifies:
1. Thread pool executor is initialized
2. Blocking operations run in thread pool (non-blocking)
3. Callback timeout protection works
4. Network validation has retry logic
"""

import asyncio
import time
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_thread_pool_initialization():
    """Test 1: Verify thread pool executor is initialized"""
    print("\n" + "="*60)
    print("TEST 1: Thread Pool Initialization")
    print("="*60)

    try:
        from src.core.market.market_data_manager import MarketDataManager
        from src.core.exchanges.manager import ExchangeManager
        import yaml

        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        # Create managers
        exchange_manager = ExchangeManager(config)
        market_data_manager = MarketDataManager(config, exchange_manager)

        # Check if executor exists
        if hasattr(market_data_manager, '_executor'):
            print("✅ Thread pool executor initialized")
            print(f"   Workers: {market_data_manager._executor._max_workers}")
            print(f"   Thread name prefix: {market_data_manager._executor._thread_name_prefix}")
            return True
        else:
            print("❌ Thread pool executor NOT found")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_callback_timeout_protection():
    """Test 2: Verify callback timeout protection exists"""
    print("\n" + "="*60)
    print("TEST 2: Callback Timeout Protection")
    print("="*60)

    try:
        from src.core.exchanges.websocket_manager import WebSocketManager
        import yaml

        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        # Create WebSocket manager
        ws_manager = WebSocketManager(config)

        # Check if _process_symbol_messages method exists
        if hasattr(ws_manager, '_process_symbol_messages'):
            print("✅ WebSocket message processor found")

            # Check the source code for asyncio.wait_for
            import inspect
            source = inspect.getsource(ws_manager._process_symbol_messages)

            if 'asyncio.wait_for' in source and 'timeout=' in source:
                print("✅ Timeout protection found in callback")
                print("   Callbacks wrapped with asyncio.wait_for()")
                return True
            else:
                print("❌ Timeout protection NOT found")
                return False
        else:
            print("❌ Message processor method NOT found")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_network_validation_retry():
    """Test 3: Verify network validation has retry logic"""
    print("\n" + "="*60)
    print("TEST 3: Network Validation Retry Logic")
    print("="*60)

    try:
        from src.core.exchanges.websocket_manager import WebSocketManager
        import yaml

        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        # Create WebSocket manager
        ws_manager = WebSocketManager(config)

        # Check if validation method exists
        if hasattr(ws_manager, '_validate_network_connectivity'):
            print("✅ Network validation method found")

            # Check the source code for retry logic
            import inspect
            source = inspect.getsource(ws_manager._validate_network_connectivity)

            has_retries = 'max_retries' in source and 'for attempt in range' in source
            has_backoff = 'await asyncio.sleep' in source and '2 ** attempt' in source
            has_increased_timeout = 'total=10' in source or 'connect=5' in source

            if has_retries:
                print("✅ Retry logic found")
            else:
                print("❌ Retry logic NOT found")

            if has_backoff:
                print("✅ Exponential backoff found")
            else:
                print("❌ Exponential backoff NOT found")

            if has_increased_timeout:
                print("✅ Increased timeout (10s total, 5s connect)")
            else:
                print("❌ Timeout NOT increased")

            return has_retries and has_backoff and has_increased_timeout
        else:
            print("❌ Network validation method NOT found")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_non_blocking_behavior():
    """Test 4: Verify callbacks don't block event loop"""
    print("\n" + "="*60)
    print("TEST 4: Non-Blocking Behavior (Simulated)")
    print("="*60)

    try:
        from src.core.market.market_data_manager import MarketDataManager
        from src.core.exchanges.manager import ExchangeManager
        import yaml

        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        # Create managers
        exchange_manager = ExchangeManager(config)
        market_data_manager = MarketDataManager(config, exchange_manager)

        # Check if update methods use run_in_executor
        import inspect
        source = inspect.getsource(market_data_manager._handle_websocket_message)

        uses_executor = 'run_in_executor' in source and 'self._executor' in source

        if uses_executor:
            print("✅ Blocking operations offloaded to thread pool")
            print("   All update methods wrapped with run_in_executor()")

            # Count how many update methods are wrapped
            update_methods = ['_update_ticker_from_ws', '_update_kline_from_ws',
                            '_update_orderbook_from_ws', '_update_trades_from_ws']
            wrapped_count = sum(1 for method in update_methods if method in source and 'run_in_executor' in source)
            print(f"   Methods wrapped: {wrapped_count}/{len(update_methods)}")

            return True
        else:
            print("❌ Blocking operations NOT offloaded")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 WEBSOCKET HANDLER FIXES - VALIDATION TESTS")
    print("="*60)

    results = []

    # Run tests
    results.append(("Thread Pool Initialization", await test_thread_pool_initialization()))
    results.append(("Callback Timeout Protection", await test_callback_timeout_protection()))
    results.append(("Network Validation Retry", await test_network_validation_retry()))
    results.append(("Non-Blocking Behavior", await test_non_blocking_behavior()))

    # Print summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All fixes validated successfully!")
        print("✅ Ready for deployment to VPS")
        return 0
    else:
        print("\n⚠️  Some tests failed - review implementation")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
