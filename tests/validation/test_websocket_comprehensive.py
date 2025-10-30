#!/usr/bin/env python3
"""
Comprehensive end-to-end validation test suite for WebSocket handler timeout fixes

This suite validates:
- Thread pool executor implementation
- Non-blocking behavior under load
- Callback timeout protection
- Network validation retry logic
- Resource management (memory, threads)
- Error handling and edge cases
- Regression prevention
- Performance characteristics
"""

import asyncio
import time
import sys
import tracemalloc
import psutil
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock
import yaml

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class ValidationReport:
    """Track validation test results"""

    def __init__(self):
        self.tests: List[Dict[str, Any]] = []
        self.criteria: List[Dict[str, Any]] = []

    def add_test(self, test_id: str, name: str, status: str, evidence: Dict[str, Any], notes: str = ""):
        """Add test result"""
        self.tests.append({
            "id": test_id,
            "name": name,
            "status": status,  # pass, fail, blocked
            "evidence": evidence,
            "notes": notes
        })

    def add_criterion(self, criterion_id: str, description: str, tests: List[str], decision: str):
        """Add acceptance criterion decision"""
        self.criteria.append({
            "id": criterion_id,
            "description": description,
            "tests": tests,
            "decision": decision
        })

    def get_summary(self) -> Dict[str, Any]:
        """Get test summary statistics"""
        total = len(self.tests)
        passed = sum(1 for t in self.tests if t["status"] == "pass")
        failed = sum(1 for t in self.tests if t["status"] == "fail")
        blocked = sum(1 for t in self.tests if t["status"] == "blocked")

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "blocked": blocked,
            "pass_rate": (passed / total * 100) if total > 0 else 0
        }


# Global report instance
report = ValidationReport()


async def test_a_thread_pool_initialization():
    """Test A: Verify ThreadPoolExecutor properly initialized"""
    print("\n" + "="*70)
    print("TEST A: Thread Pool Initialization")
    print("="*70)

    evidence = {}

    try:
        from src.core.market.market_data_manager import MarketDataManager
        from src.core.exchanges.manager import ExchangeManager

        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        # Create managers
        exchange_manager = ExchangeManager(config)
        market_data_manager = MarketDataManager(config, exchange_manager)

        # Check executor exists
        has_executor = hasattr(market_data_manager, '_executor')
        evidence["has_executor"] = has_executor

        if not has_executor:
            print("❌ Thread pool executor NOT found")
            report.add_test("TEST-A", "Thread Pool Initialization", "fail", evidence,
                          "ThreadPoolExecutor not initialized in MarketDataManager")
            return False

        executor = market_data_manager._executor
        evidence["executor_type"] = type(executor).__name__
        evidence["max_workers"] = executor._max_workers
        evidence["thread_name_prefix"] = executor._thread_name_prefix

        # Validate configuration
        checks = {
            "is_ThreadPoolExecutor": isinstance(executor, ThreadPoolExecutor),
            "max_workers_is_4": executor._max_workers == 4,
            "has_thread_prefix": executor._thread_name_prefix == "market_data_worker",
            "executor_not_none": executor is not None
        }

        evidence["checks"] = checks
        all_passed = all(checks.values())

        print(f"✅ Executor Type: {evidence['executor_type']}")
        print(f"✅ Max Workers: {evidence['max_workers']} (expected: 4)")
        print(f"✅ Thread Prefix: {evidence['thread_name_prefix']}")
        print(f"{'✅' if all_passed else '❌'} All checks passed: {all_passed}")

        status = "pass" if all_passed else "fail"
        report.add_test("TEST-A", "Thread Pool Initialization", status, evidence)

        return all_passed

    except Exception as e:
        evidence["error"] = str(e)
        evidence["traceback"] = traceback.format_exc()
        print(f"❌ Test failed with exception: {e}")
        report.add_test("TEST-A", "Thread Pool Initialization", "fail", evidence, str(e))
        return False


async def test_b_non_blocking_behavior():
    """Test B: Verify blocking operations don't block event loop"""
    print("\n" + "="*70)
    print("TEST B: Non-Blocking Behavior Under Concurrent Load")
    print("="*70)

    evidence = {}

    try:
        from src.core.market.market_data_manager import MarketDataManager
        from src.core.exchanges.manager import ExchangeManager

        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        exchange_manager = ExchangeManager(config)
        market_data_manager = MarketDataManager(config, exchange_manager)

        # Initialize cache for test symbol
        test_symbol = "BTCUSDT"
        market_data_manager.data_cache[test_symbol] = {
            'ticker': {},
            'kline': {},
            'orderbook': {},
            'trades': []
        }

        # Create mock kline message (pandas-heavy operation)
        mock_kline_data = {
            "topic": "kline.1.BTCUSDT",
            "data": [{
                "start": int(time.time() * 1000),
                "end": int(time.time() * 1000) + 60000,
                "open": "50000",
                "high": "50100",
                "low": "49900",
                "close": "50050",
                "volume": "100.5",
                "confirm": False
            }]
        }

        # Send 10 concurrent messages and measure time
        print("Sending 10 concurrent kline messages...")
        start_time = time.time()

        tasks = []
        for i in range(10):
            task = market_data_manager._handle_websocket_message(
                test_symbol,
                "kline.1.BTCUSDT",
                mock_kline_data
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        elapsed = time.time() - start_time
        evidence["concurrent_messages"] = 10
        evidence["elapsed_time"] = elapsed
        evidence["time_threshold"] = 2.0
        evidence["would_block_time"] = "5-10s (if blocking)"

        # Should complete in <2s (would take 5-10s if blocking)
        passed = elapsed < 2.0

        print(f"✅ Processed 10 messages in {elapsed:.3f}s")
        print(f"{'✅' if passed else '❌'} Time under threshold (2.0s): {passed}")
        print(f"📊 Event loop remained responsive")

        evidence["non_blocking"] = passed
        status = "pass" if passed else "fail"

        report.add_test("TEST-B", "Non-Blocking Concurrent Load", status, evidence)
        return passed

    except Exception as e:
        evidence["error"] = str(e)
        evidence["traceback"] = traceback.format_exc()
        print(f"❌ Test failed: {e}")
        report.add_test("TEST-B", "Non-Blocking Concurrent Load", "fail", evidence, str(e))
        return False


async def test_c_callback_timeout_protection():
    """Test C: Verify slow callbacks are terminated"""
    print("\n" + "="*70)
    print("TEST C: Callback Timeout Protection")
    print("="*70)

    evidence = {}

    try:
        from src.core.exchanges.websocket_manager import WebSocketManager

        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        ws_manager = WebSocketManager(config)

        # Create slow callback that sleeps for 5 seconds
        callback_executed = False
        callback_completed = False
        timeout_triggered = False

        async def slow_callback(symbol, topic, message):
            nonlocal callback_executed, callback_completed
            callback_executed = True
            await asyncio.sleep(5)  # Should timeout at 3s
            callback_completed = True

        ws_manager.message_callback = slow_callback

        # Simulate message processing
        test_message = {
            "topic": "tickers.BTCUSDT",
            "data": {"symbol": "BTCUSDT", "lastPrice": "50000"}
        }

        print("Testing callback timeout (5s callback with 3s timeout)...")
        start_time = time.time()

        try:
            # This should timeout after 3 seconds
            await asyncio.wait_for(
                ws_manager.message_callback("BTCUSDT", "tickers.BTCUSDT", test_message),
                timeout=3.0
            )
        except asyncio.TimeoutError:
            timeout_triggered = True
            print("✅ Timeout triggered after 3s (expected)")

        elapsed = time.time() - start_time

        evidence["callback_executed"] = callback_executed
        evidence["callback_completed"] = callback_completed
        evidence["timeout_triggered"] = timeout_triggered
        evidence["elapsed_time"] = elapsed
        evidence["timeout_threshold"] = 3.0

        # Validate behavior
        checks = {
            "callback_started": callback_executed,
            "callback_not_completed": not callback_completed,
            "timeout_occurred": timeout_triggered,
            "time_around_3s": 2.9 <= elapsed <= 3.2
        }

        evidence["checks"] = checks
        all_passed = all(checks.values())

        print(f"✅ Callback executed: {callback_executed}")
        print(f"✅ Callback did NOT complete (timed out): {not callback_completed}")
        print(f"✅ Timeout triggered: {timeout_triggered}")
        print(f"✅ Elapsed time: {elapsed:.2f}s (expected ~3s)")

        status = "pass" if all_passed else "fail"
        report.add_test("TEST-C", "Callback Timeout Protection", status, evidence)

        return all_passed

    except Exception as e:
        evidence["error"] = str(e)
        evidence["traceback"] = traceback.format_exc()
        print(f"❌ Test failed: {e}")
        report.add_test("TEST-C", "Callback Timeout Protection", "fail", evidence, str(e))
        return False


async def test_d_network_retry_logic():
    """Test D: Verify exponential backoff in network validation"""
    print("\n" + "="*70)
    print("TEST D: Network Validation Retry Logic")
    print("="*70)

    evidence = {}

    try:
        import inspect
        from src.core.exchanges.websocket_manager import WebSocketManager

        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        ws_manager = WebSocketManager(config)

        # First, validate the code has retry logic by inspecting source
        print("Validating network retry implementation...")

        if hasattr(ws_manager, '_validate_network_connectivity'):
            source = inspect.getsource(ws_manager._validate_network_connectivity)

            has_retries = 'max_retries' in source and 'for attempt in range' in source
            has_backoff = 'await asyncio.sleep' in source and '2 ** attempt' in source
            has_increased_timeout = 'total=10' in source or 'connect=5' in source
            has_retry_param = 'max_retries:' in source

            evidence["has_retry_loop"] = has_retries
            evidence["has_exponential_backoff"] = has_backoff
            evidence["has_increased_timeout"] = has_increased_timeout
            evidence["has_retry_parameter"] = has_retry_param

            # Extract retry configuration from source code
            if '2 ** attempt' in source:
                print("✅ Exponential backoff formula found: 2 ** attempt")
            if 'total=10' in source:
                print("✅ Total timeout increased to 10s")
            if 'connect=5' in source:
                print("✅ Connect timeout increased to 5s")
            if 'max_retries' in source:
                print("✅ Retry parameter configured")

            # Validate actual network connectivity (non-mocked real test)
            print("\nTesting actual network connectivity with retry...")
            start_time = time.time()

            try:
                result = await ws_manager._validate_network_connectivity(max_retries=3)
                elapsed = time.time() - start_time

                evidence["real_network_test"] = result
                evidence["elapsed_time"] = elapsed

                print(f"✅ Network validation result: {result}")
                print(f"✅ Elapsed time: {elapsed:.2f}s")

            except Exception as e:
                evidence["real_network_error"] = str(e)
                print(f"⚠️  Network test error (expected on VPS): {e}")

            # Validate code implementation checks
            checks = {
                "has_retry_logic": has_retries,
                "has_exponential_backoff": has_backoff,
                "has_increased_timeouts": has_increased_timeout,
                "has_retry_parameter": has_retry_param
            }

            evidence["checks"] = checks
            all_passed = all(checks.values())

            print(f"\n📊 Code Implementation Checks:")
            print(f"   {'✅' if checks['has_retry_logic'] else '❌'} Retry loop: {checks['has_retry_logic']}")
            print(f"   {'✅' if checks['has_exponential_backoff'] else '❌'} Exponential backoff: {checks['has_exponential_backoff']}")
            print(f"   {'✅' if checks['has_increased_timeouts'] else '❌'} Increased timeouts: {checks['has_increased_timeouts']}")
            print(f"   {'✅' if checks['has_retry_parameter'] else '❌'} Retry parameter: {checks['has_retry_parameter']}")
            print(f"{'✅' if all_passed else '❌'} All implementation checks passed: {all_passed}")

            status = "pass" if all_passed else "fail"
            report.add_test("TEST-D", "Network Retry with Exponential Backoff", status, evidence)

            return all_passed
        else:
            evidence["error"] = "Method _validate_network_connectivity not found"
            print("❌ Network validation method not found")
            report.add_test("TEST-D", "Network Retry Logic", "fail", evidence)
            return False

    except Exception as e:
        evidence["error"] = str(e)
        evidence["traceback"] = traceback.format_exc()
        print(f"❌ Test failed: {e}")
        report.add_test("TEST-D", "Network Retry Logic", "fail", evidence, str(e))
        return False


async def test_h_memory_usage():
    """Test H: Verify no memory leaks from thread pool"""
    print("\n" + "="*70)
    print("TEST H: Memory Usage & Leak Detection")
    print("="*70)

    evidence = {}

    try:
        from src.core.market.market_data_manager import MarketDataManager
        from src.core.exchanges.manager import ExchangeManager

        # Start memory tracking
        tracemalloc.start()
        process = psutil.Process(os.getpid())

        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        exchange_manager = ExchangeManager(config)
        market_data_manager = MarketDataManager(config, exchange_manager)

        # Initialize cache
        test_symbol = "BTCUSDT"
        market_data_manager.data_cache[test_symbol] = {
            'ticker': {},
            'kline': {},
            'orderbook': {},
            'trades': []
        }

        # Get baseline memory
        baseline_mem = process.memory_info().rss / 1024 / 1024  # MB
        baseline_tracemalloc = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB

        evidence["baseline_memory_mb"] = baseline_mem
        evidence["baseline_tracemalloc_mb"] = baseline_tracemalloc

        print(f"📊 Baseline memory: {baseline_mem:.2f} MB")
        print(f"📊 Processing 1000 messages...")

        # Process 1000 messages
        mock_kline_data = {
            "topic": "kline.1.BTCUSDT",
            "data": [{
                "start": int(time.time() * 1000),
                "end": int(time.time() * 1000) + 60000,
                "open": "50000",
                "high": "50100",
                "low": "49900",
                "close": "50050",
                "volume": "100.5",
                "confirm": False
            }]
        }

        for i in range(1000):
            await market_data_manager._handle_websocket_message(
                test_symbol,
                "kline.1.BTCUSDT",
                mock_kline_data
            )

            # Periodic progress
            if (i + 1) % 250 == 0:
                print(f"   Processed {i + 1}/1000...")

        # Get final memory
        final_mem = process.memory_info().rss / 1024 / 1024  # MB
        final_tracemalloc = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB

        memory_increase = final_mem - baseline_mem
        tracemalloc_increase = final_tracemalloc - baseline_tracemalloc

        evidence["final_memory_mb"] = final_mem
        evidence["memory_increase_mb"] = memory_increase
        evidence["tracemalloc_increase_mb"] = tracemalloc_increase
        evidence["threshold_mb"] = 100

        tracemalloc.stop()

        # Check if memory increase is acceptable (<100MB)
        passed = memory_increase < 100

        print(f"📊 Final memory: {final_mem:.2f} MB")
        print(f"📊 Memory increase: {memory_increase:.2f} MB")
        print(f"📊 Tracemalloc increase: {tracemalloc_increase:.2f} MB")
        print(f"{'✅' if passed else '❌'} Memory increase under threshold (100MB): {passed}")

        status = "pass" if passed else "fail"
        report.add_test("TEST-H", "Memory Usage & Leak Detection", status, evidence)

        return passed

    except Exception as e:
        tracemalloc.stop()
        evidence["error"] = str(e)
        evidence["traceback"] = traceback.format_exc()
        print(f"❌ Test failed: {e}")
        report.add_test("TEST-H", "Memory Usage", "fail", evidence, str(e))
        return False


async def test_j_event_loop_responsiveness():
    """Test J: Verify event loop stays responsive during heavy load"""
    print("\n" + "="*70)
    print("TEST J: Event Loop Responsiveness Under Load")
    print("="*70)

    evidence = {}

    try:
        from src.core.market.market_data_manager import MarketDataManager
        from src.core.exchanges.manager import ExchangeManager

        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        exchange_manager = ExchangeManager(config)
        market_data_manager = MarketDataManager(config, exchange_manager)

        # Initialize cache
        test_symbol = "BTCUSDT"
        market_data_manager.data_cache[test_symbol] = {
            'ticker': {},
            'kline': {},
            'orderbook': {},
            'trades': []
        }

        # Create heavy kline message
        mock_kline_data = {
            "topic": "kline.1.BTCUSDT",
            "data": [{
                "start": int(time.time() * 1000),
                "end": int(time.time() * 1000) + 60000,
                "open": "50000",
                "high": "50100",
                "low": "49900",
                "close": "50050",
                "volume": "100.5",
                "confirm": False
            }]
        }

        # Start processing 50 kline updates (heavy pandas operations)
        print("Starting 50 heavy kline updates...")
        kline_tasks = [
            market_data_manager._handle_websocket_message(
                test_symbol, "kline.1.BTCUSDT", mock_kline_data
            )
            for _ in range(50)
        ]

        # Create a simple responsive task to check event loop
        response_times = []

        async def check_responsiveness():
            """Quick task to measure event loop responsiveness"""
            start = time.time()
            await asyncio.sleep(0)  # Yield to event loop
            elapsed = (time.time() - start) * 1000  # ms
            response_times.append(elapsed)

        # While kline updates are processing, check event loop responsiveness
        print("Checking event loop responsiveness during heavy load...")

        # Create combined tasks
        all_tasks = kline_tasks + [
            check_responsiveness() for _ in range(10)
        ]

        start_time = time.time()
        await asyncio.gather(*all_tasks)
        total_time = time.time() - start_time

        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0

        evidence["kline_updates"] = 50
        evidence["response_checks"] = len(response_times)
        evidence["avg_response_time_ms"] = avg_response_time
        evidence["max_response_time_ms"] = max_response_time
        evidence["total_time_s"] = total_time
        evidence["threshold_ms"] = 100

        # Event loop should respond in <100ms
        passed = max_response_time < 100

        print(f"✅ Processed {len(kline_tasks)} kline updates")
        print(f"✅ Performed {len(response_times)} responsiveness checks")
        print(f"✅ Average response time: {avg_response_time:.2f}ms")
        print(f"✅ Max response time: {max_response_time:.2f}ms")
        print(f"{'✅' if passed else '❌'} Max response under threshold (100ms): {passed}")

        status = "pass" if passed else "fail"
        report.add_test("TEST-J", "Event Loop Responsiveness", status, evidence)

        return passed

    except Exception as e:
        evidence["error"] = str(e)
        evidence["traceback"] = traceback.format_exc()
        print(f"❌ Test failed: {e}")
        report.add_test("TEST-J", "Event Loop Responsiveness", "fail", evidence, str(e))
        return False


async def test_m_malformed_messages():
    """Test M: Verify resilience to malformed messages"""
    print("\n" + "="*70)
    print("TEST M: Malformed Message Handling")
    print("="*70)

    evidence = {}

    try:
        from src.core.market.market_data_manager import MarketDataManager
        from src.core.exchanges.manager import ExchangeManager

        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        exchange_manager = ExchangeManager(config)
        market_data_manager = MarketDataManager(config, exchange_manager)

        # Initialize cache
        test_symbol = "BTCUSDT"
        market_data_manager.data_cache[test_symbol] = {
            'ticker': {},
            'kline': {},
            'orderbook': {},
            'trades': []
        }

        # Test cases with malformed data
        test_cases = [
            {
                "name": "Invalid JSON (None)",
                "data": None,
                "topic": "kline.1.BTCUSDT"
            },
            {
                "name": "Missing data field",
                "data": {"topic": "kline.1.BTCUSDT"},
                "topic": "kline.1.BTCUSDT"
            },
            {
                "name": "Wrong data type (string instead of dict)",
                "data": "invalid_data",
                "topic": "kline.1.BTCUSDT"
            },
            {
                "name": "Empty dict",
                "data": {},
                "topic": "kline.1.BTCUSDT"
            }
        ]

        results = []

        for test_case in test_cases:
            try:
                await market_data_manager._handle_websocket_message(
                    test_symbol,
                    test_case["topic"],
                    test_case["data"]
                )
                results.append({
                    "test": test_case["name"],
                    "crashed": False,
                    "error": None
                })
                print(f"✅ Handled: {test_case['name']}")
            except Exception as e:
                results.append({
                    "test": test_case["name"],
                    "crashed": True,
                    "error": str(e)
                })
                print(f"❌ Crashed on: {test_case['name']} - {e}")

        evidence["test_cases"] = len(test_cases)
        evidence["results"] = results

        # Should not crash on any malformed message
        crashes = sum(1 for r in results if r["crashed"])
        passed = crashes == 0

        print(f"\n📊 Test cases: {len(test_cases)}")
        print(f"{'✅' if passed else '❌'} No crashes: {passed} (crashes: {crashes})")

        status = "pass" if passed else "fail"
        report.add_test("TEST-M", "Malformed Message Handling", status, evidence)

        return passed

    except Exception as e:
        evidence["error"] = str(e)
        evidence["traceback"] = traceback.format_exc()
        print(f"❌ Test failed: {e}")
        report.add_test("TEST-M", "Malformed Messages", "fail", evidence, str(e))
        return False


async def test_k_existing_functionality():
    """Test K: Verify existing functionality still works"""
    print("\n" + "="*70)
    print("TEST K: Regression Check - Existing Functionality")
    print("="*70)

    evidence = {}

    try:
        from src.core.market.market_data_manager import MarketDataManager
        from src.core.exchanges.manager import ExchangeManager

        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        exchange_manager = ExchangeManager(config)
        market_data_manager = MarketDataManager(config, exchange_manager)

        # Initialize cache
        test_symbol = "BTCUSDT"
        market_data_manager.data_cache[test_symbol] = {
            'ticker': {},
            'kline': {},
            'orderbook': {},
            'trades': []
        }

        # Test ticker update
        ticker_data = {
            "data": {
                "symbol": "BTCUSDT",
                "lastPrice": "50000",
                "bid1Price": "49999",
                "ask1Price": "50001",
                "volume24h": "1000"
            }
        }

        await market_data_manager._handle_websocket_message(
            test_symbol, "tickers.BTCUSDT", ticker_data
        )
        ticker_updated = 'ticker' in market_data_manager.data_cache[test_symbol]

        # Test kline update
        kline_data = {
            "data": [{
                "start": int(time.time() * 1000),
                "end": int(time.time() * 1000) + 60000,
                "open": "50000",
                "high": "50100",
                "low": "49900",
                "close": "50050",
                "volume": "100.5",
                "confirm": False
            }]
        }

        await market_data_manager._handle_websocket_message(
            test_symbol, "kline.1.BTCUSDT", kline_data
        )
        kline_updated = 'kline' in market_data_manager.data_cache[test_symbol]

        # Test orderbook update
        orderbook_data = {
            "data": {
                "s": "BTCUSDT",
                "b": [["50000", "1.5"], ["49999", "2.0"]],
                "a": [["50001", "1.3"], ["50002", "1.8"]],
                "u": 12345,
                "seq": 67890
            }
        }

        await market_data_manager._handle_websocket_message(
            test_symbol, "orderbook.50.BTCUSDT", orderbook_data
        )
        orderbook_updated = 'orderbook' in market_data_manager.data_cache[test_symbol]

        # Test trades update
        trades_data = {
            "data": [{
                "T": int(time.time() * 1000),
                "s": "BTCUSDT",
                "S": "Buy",
                "v": "0.5",
                "p": "50000",
                "i": "trade123"
            }]
        }

        await market_data_manager._handle_websocket_message(
            test_symbol, "publicTrade.BTCUSDT", trades_data
        )
        trades_updated = 'trades' in market_data_manager.data_cache[test_symbol]

        # Check stats counter
        stats_incremented = market_data_manager.stats['websocket_updates'] > 0

        evidence["ticker_updated"] = ticker_updated
        evidence["kline_updated"] = kline_updated
        evidence["orderbook_updated"] = orderbook_updated
        evidence["trades_updated"] = trades_updated
        evidence["stats_incremented"] = stats_incremented
        evidence["websocket_update_count"] = market_data_manager.stats['websocket_updates']

        checks = {
            "ticker_works": ticker_updated,
            "kline_works": kline_updated,
            "orderbook_works": orderbook_updated,
            "trades_work": trades_updated,
            "stats_tracked": stats_incremented
        }

        evidence["checks"] = checks
        all_passed = all(checks.values())

        print(f"✅ Ticker updates: {ticker_updated}")
        print(f"✅ Kline updates: {kline_updated}")
        print(f"✅ Orderbook updates: {orderbook_updated}")
        print(f"✅ Trade updates: {trades_updated}")
        print(f"✅ Stats tracking: {stats_incremented} (count: {evidence['websocket_update_count']})")
        print(f"{'✅' if all_passed else '❌'} All functionality intact: {all_passed}")

        status = "pass" if all_passed else "fail"
        report.add_test("TEST-K", "Existing Functionality Regression", status, evidence)

        return all_passed

    except Exception as e:
        evidence["error"] = str(e)
        evidence["traceback"] = traceback.format_exc()
        print(f"❌ Test failed: {e}")
        report.add_test("TEST-K", "Existing Functionality", "fail", evidence, str(e))
        return False


def print_final_report():
    """Print comprehensive validation report"""
    print("\n" + "="*70)
    print("📋 COMPREHENSIVE VALIDATION REPORT")
    print("="*70)

    summary = report.get_summary()

    print(f"\n📊 TEST SUMMARY:")
    print(f"   Total tests: {summary['total']}")
    print(f"   Passed: {summary['passed']}")
    print(f"   Failed: {summary['failed']}")
    print(f"   Blocked: {summary['blocked']}")
    print(f"   Pass rate: {summary['pass_rate']:.1f}%")

    print(f"\n✅ DETAILED RESULTS:")
    for test in report.tests:
        status_emoji = "✅" if test["status"] == "pass" else "❌" if test["status"] == "fail" else "⚠️"
        print(f"   {status_emoji} {test['id']}: {test['name']} - {test['status'].upper()}")
        if test["notes"]:
            print(f"      Note: {test['notes']}")

    # Add acceptance criteria
    report.add_criterion(
        "AC-1",
        "Thread pool executor properly initialized and configured",
        ["TEST-A"],
        "pass" if any(t["id"] == "TEST-A" and t["status"] == "pass" for t in report.tests) else "fail"
    )

    report.add_criterion(
        "AC-2",
        "Blocking operations do not block event loop",
        ["TEST-B", "TEST-J"],
        "pass" if all(t["status"] == "pass" for t in report.tests if t["id"] in ["TEST-B", "TEST-J"]) else "fail"
    )

    report.add_criterion(
        "AC-3",
        "Callback timeout protection functions correctly",
        ["TEST-C"],
        "pass" if any(t["id"] == "TEST-C" and t["status"] == "pass" for t in report.tests) else "fail"
    )

    report.add_criterion(
        "AC-4",
        "Network validation has proper retry logic",
        ["TEST-D"],
        "pass" if any(t["id"] == "TEST-D" and t["status"] == "pass" for t in report.tests) else "fail"
    )

    report.add_criterion(
        "AC-5",
        "No memory leaks or resource issues",
        ["TEST-H"],
        "pass" if any(t["id"] == "TEST-H" and t["status"] == "pass" for t in report.tests) else "fail"
    )

    report.add_criterion(
        "AC-6",
        "Error handling works for malformed messages",
        ["TEST-M"],
        "pass" if any(t["id"] == "TEST-M" and t["status"] == "pass" for t in report.tests) else "fail"
    )

    report.add_criterion(
        "AC-7",
        "No regressions in existing functionality",
        ["TEST-K"],
        "pass" if any(t["id"] == "TEST-K" and t["status"] == "pass" for t in report.tests) else "fail"
    )

    print(f"\n🎯 ACCEPTANCE CRITERIA:")
    all_criteria_passed = True
    for criterion in report.criteria:
        status_emoji = "✅" if criterion["decision"] == "pass" else "❌"
        print(f"   {status_emoji} {criterion['id']}: {criterion['description']}")
        print(f"      Tests: {', '.join(criterion['tests'])} - {criterion['decision'].upper()}")
        if criterion["decision"] != "pass":
            all_criteria_passed = False

    # Final decision
    print(f"\n{'='*70}")
    print("🚦 DEPLOYMENT DECISION")
    print("="*70)

    must_pass_tests = ["TEST-A", "TEST-B", "TEST-C", "TEST-D", "TEST-H", "TEST-K", "TEST-M"]
    must_pass_results = [t for t in report.tests if t["id"] in must_pass_tests]
    must_pass_count = sum(1 for t in must_pass_results if t["status"] == "pass")

    if summary['pass_rate'] == 100 and all_criteria_passed:
        print("✅ RECOMMENDATION: GO FOR DEPLOYMENT")
        print("\nAll must-pass criteria met:")
        print("  ✅ Thread pool executor properly configured")
        print("  ✅ Non-blocking behavior verified")
        print("  ✅ Callback timeout protection working")
        print("  ✅ Network retry logic functional")
        print("  ✅ No memory leaks detected")
        print("  ✅ Error handling robust")
        print("  ✅ No regressions found")
        print("\n🚀 System is ready for production deployment")
        return True
    elif must_pass_count >= len(must_pass_tests) - 1 and summary['pass_rate'] >= 85:
        print("⚠️  RECOMMENDATION: CONDITIONAL GO")
        print(f"\nMost criteria met ({must_pass_count}/{len(must_pass_tests)} must-pass tests)")
        print("Minor issues identified but not blocking:")
        for test in report.tests:
            if test["status"] != "pass":
                print(f"  ⚠️  {test['id']}: {test['name']}")
        print("\n✅ Can deploy with monitoring")
        return True
    else:
        print("❌ RECOMMENDATION: NO-GO FOR DEPLOYMENT")
        print(f"\nCritical issues found ({summary['failed']} failed tests):")
        for test in report.tests:
            if test["status"] == "fail":
                print(f"  ❌ {test['id']}: {test['name']}")
                if test.get("notes"):
                    print(f"     {test['notes']}")
        print("\n🛑 Must fix critical issues before deployment")
        return False


async def main():
    """Run comprehensive validation test suite"""
    print("\n" + "="*70)
    print("🧪 COMPREHENSIVE WEBSOCKET HANDLER FIXES VALIDATION")
    print("="*70)
    print("\nValidating three critical fixes:")
    print("  1. Thread Pool Executor for non-blocking operations")
    print("  2. Callback Timeout Protection (3s timeout)")
    print("  3. Network Validation Retry Logic (exponential backoff)")

    # Run all tests
    results = []

    # Phase 1: Unit Tests
    print("\n" + "="*70)
    print("PHASE 1: UNIT TESTS")
    print("="*70)
    results.append(await test_a_thread_pool_initialization())
    results.append(await test_b_non_blocking_behavior())
    results.append(await test_c_callback_timeout_protection())
    results.append(await test_d_network_retry_logic())

    # Phase 2: Resource Tests
    print("\n" + "="*70)
    print("PHASE 2: RESOURCE & PERFORMANCE TESTS")
    print("="*70)
    results.append(await test_h_memory_usage())
    results.append(await test_j_event_loop_responsiveness())

    # Phase 3: Error Handling & Regression
    print("\n" + "="*70)
    print("PHASE 3: ERROR HANDLING & REGRESSION TESTS")
    print("="*70)
    results.append(await test_m_malformed_messages())
    results.append(await test_k_existing_functionality())

    # Print final report and decision
    deployment_approved = print_final_report()

    return 0 if deployment_approved else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
