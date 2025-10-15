#!/usr/bin/env python3
"""
Comprehensive AsyncIO Session Management Validation Test

Validates the fixes for:
1. AsyncIO Session/Connector Lifecycle Leaks in BybitExchange
2. Empty Signals Cache Reads
3. Session recreation and recovery scenarios
"""

import asyncio
import logging
import time
import json
import sys
import os
from typing import Dict, Any, List
import warnings
import gc
import tracemalloc
from contextlib import redirect_stderr
from io import StringIO

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.exchanges.bybit import BybitExchange
from src.api.cache_adapter_direct import DirectCacheAdapter
from src.main import aggregate_confluence_signals
import aiomcache

# Configure logging to capture warnings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('validation_session_test.log')
    ]
)

logger = logging.getLogger(__name__)

class SessionLeakDetector:
    """Detect asyncio session and connector leaks"""

    def __init__(self):
        self.warnings_captured = []
        self.initial_objects = None
        self.initial_memory = None

    def start_monitoring(self):
        """Start monitoring for leaks"""
        # Capture warnings
        warnings.filterwarnings("always")
        self.original_showwarning = warnings.showwarning
        warnings.showwarning = self._capture_warning

        # Start memory tracing
        tracemalloc.start()
        self.initial_memory = tracemalloc.take_snapshot()

        # Count initial asyncio objects
        gc.collect()
        self.initial_objects = self._count_asyncio_objects()

    def stop_monitoring(self):
        """Stop monitoring and return results"""
        # Restore warnings
        warnings.showwarning = self.original_showwarning

        # Get memory snapshot
        final_memory = tracemalloc.take_snapshot()

        # Count final objects
        gc.collect()
        final_objects = self._count_asyncio_objects()

        # Analyze memory growth
        top_stats = final_memory.compare_to(self.initial_memory, 'lineno')

        return {
            'warnings': self.warnings_captured,
            'memory_leaks': top_stats[:10],
            'object_counts': {
                'initial': self.initial_objects,
                'final': final_objects,
                'growth': {k: final_objects[k] - self.initial_objects.get(k, 0)
                          for k in final_objects}
            }
        }

    def _capture_warning(self, message, category, filename, lineno, file=None, line=None):
        """Capture warnings for analysis"""
        warning_info = {
            'message': str(message),
            'category': category.__name__,
            'filename': filename,
            'lineno': lineno,
            'timestamp': time.time()
        }
        self.warnings_captured.append(warning_info)
        logger.warning(f"CAPTURED WARNING: {warning_info}")

    def _count_asyncio_objects(self):
        """Count asyncio-related objects"""
        import aiohttp
        counts = {
            'ClientSession': 0,
            'TCPConnector': 0,
            'ClientTimeout': 0,
            'total_objects': len(gc.get_objects())
        }

        for obj in gc.get_objects():
            if isinstance(obj, aiohttp.ClientSession):
                counts['ClientSession'] += 1
            elif isinstance(obj, aiohttp.TCPConnector):
                counts['TCPConnector'] += 1
            elif isinstance(obj, aiohttp.ClientTimeout):
                counts['ClientTimeout'] += 1

        return counts

async def test_session_lifecycle():
    """Test BybitExchange session lifecycle management"""
    logger.info("=== Testing BybitExchange Session Lifecycle ===")

    detector = SessionLeakDetector()
    detector.start_monitoring()

    results = {
        'test_name': 'session_lifecycle',
        'status': 'PASS',
        'issues': [],
        'metrics': {}
    }

    try:
        # Test 1: Normal initialization and cleanup
        logger.info("Test 1: Normal session initialization")
        exchange = BybitExchange('bybit')

        # Initialize the exchange
        init_success = await exchange.initialize()
        if not init_success:
            results['issues'].append("Exchange initialization failed")
            results['status'] = 'FAIL'

        # Verify session is created
        if not exchange.session:
            results['issues'].append("Session not created after initialization")
            results['status'] = 'FAIL'

        if not exchange.connector:
            results['issues'].append("Connector not created after initialization")
            results['status'] = 'FAIL'

        # Test 2: Session recreation scenario
        logger.info("Test 2: Session recreation under load")
        original_session_id = id(exchange.session)

        # Force session recreation
        await exchange._ensure_healthy_session()

        # Should have same session if healthy
        if id(exchange.session) != original_session_id:
            logger.info("Session was recreated (expected if unhealthy)")

        # Test 3: Connector closed error simulation
        logger.info("Test 3: Simulating connector closed error")

        # Close connector manually to simulate error
        if exchange.connector and not exchange.connector.closed:
            await exchange.connector.close()

        # This should trigger recreation
        healthy = await exchange._ensure_healthy_session()
        if not healthy:
            results['issues'].append("Session recreation failed after connector close")
            results['status'] = 'FAIL'

        # Test 4: Multiple API requests to test session stability
        logger.info("Test 4: Multiple API requests")

        for i in range(5):
            try:
                response = await exchange._make_request('GET', '/v5/market/time')
                if not response or response.get('retCode') != 0:
                    results['issues'].append(f"API request {i+1} failed: {response}")

            except Exception as e:
                results['issues'].append(f"API request {i+1} exception: {str(e)}")

        # Test 5: Proper cleanup
        logger.info("Test 5: Testing cleanup")
        await exchange.close()

        # Verify session is closed
        if exchange.session and not exchange.session.closed:
            results['issues'].append("Session not properly closed")
            results['status'] = 'FAIL'

        if exchange.connector and not exchange.connector.closed:
            results['issues'].append("Connector not properly closed")
            results['status'] = 'FAIL'

        # Wait for cleanup
        await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Session lifecycle test error: {e}")
        results['issues'].append(f"Test exception: {str(e)}")
        results['status'] = 'FAIL'

    # Stop monitoring and get results
    leak_results = detector.stop_monitoring()
    results['leak_detection'] = leak_results

    # Analyze results
    session_warnings = [w for w in leak_results['warnings']
                       if 'session' in w['message'].lower() or 'connector' in w['message'].lower()]

    if session_warnings:
        results['issues'].extend([w['message'] for w in session_warnings])
        if any('unclosed' in w['message'].lower() for w in session_warnings):
            results['status'] = 'FAIL'

    results['metrics'] = {
        'total_warnings': len(leak_results['warnings']),
        'session_warnings': len(session_warnings),
        'object_growth': leak_results['object_counts']['growth']
    }

    logger.info(f"Session lifecycle test: {results['status']}")
    return results

async def test_signals_cache_behavior():
    """Test signals cache population and reading"""
    logger.info("=== Testing Signals Cache Behavior ===")

    results = {
        'test_name': 'signals_cache',
        'status': 'PASS',
        'issues': [],
        'metrics': {}
    }

    try:
        # Test 1: DirectCacheAdapter signals reading
        logger.info("Test 1: DirectCacheAdapter.get_signals()")
        cache_adapter = DirectCacheAdapter()

        # Get signals before aggregation
        initial_signals = await cache_adapter.get_signals()
        initial_count = initial_signals.get('count', 0)

        logger.info(f"Initial signals count: {initial_count}")

        # Test 2: Run signals aggregation
        logger.info("Test 2: Running aggregate_confluence_signals()")
        await aggregate_confluence_signals()

        # Wait for cache to propagate
        await asyncio.sleep(2)

        # Test 3: Check signals after aggregation
        logger.info("Test 3: Checking signals after aggregation")
        post_aggregation_signals = await cache_adapter.get_signals()
        post_count = post_aggregation_signals.get('count', 0)

        logger.info(f"Post-aggregation signals count: {post_count}")

        if post_count == 0:
            results['issues'].append("No signals found after aggregation")
            results['status'] = 'FAIL'

        # Test 4: Direct cache access
        logger.info("Test 4: Direct memcache access")
        client = aiomcache.Client('localhost', 11211)

        raw_signals_data = await client.get(b'analysis:signals')
        await client.close()

        if not raw_signals_data:
            results['issues'].append("No raw signals data in cache")
            results['status'] = 'FAIL'
        else:
            try:
                signals_obj = json.loads(raw_signals_data.decode())
                raw_count = len(signals_obj.get('signals', []))
                logger.info(f"Raw cache signals count: {raw_count}")

                if raw_count != post_count:
                    results['issues'].append(f"Signal count mismatch: cache={raw_count}, adapter={post_count}")

            except Exception as e:
                results['issues'].append(f"Error parsing raw signals data: {e}")

        # Test 5: Cache TTL behavior
        logger.info("Test 5: Testing cache TTL")

        # Record current timestamp
        current_timestamp = post_aggregation_signals.get('timestamp', 0)

        # Wait and check if data is still fresh
        await asyncio.sleep(5)

        ttl_signals = await cache_adapter.get_signals()
        ttl_timestamp = ttl_signals.get('timestamp', 0)
        ttl_count = ttl_signals.get('count', 0)

        if ttl_timestamp == current_timestamp and ttl_count > 0:
            logger.info("Cache TTL working correctly - data still fresh")
        elif ttl_count == 0:
            results['issues'].append("Signals expired too quickly or cache miss")

        results['metrics'] = {
            'initial_count': initial_count,
            'post_aggregation_count': post_count,
            'final_count': ttl_count,
            'cache_ttl_test': ttl_timestamp == current_timestamp
        }

    except Exception as e:
        logger.error(f"Signals cache test error: {e}")
        results['issues'].append(f"Test exception: {str(e)}")
        results['status'] = 'FAIL'

    logger.info(f"Signals cache test: {results['status']}")
    return results

async def test_integration_pipeline():
    """Test full data flow integration"""
    logger.info("=== Testing Integration Pipeline ===")

    results = {
        'test_name': 'integration_pipeline',
        'status': 'PASS',
        'issues': [],
        'metrics': {}
    }

    try:
        # Test full pipeline: tickers → breakdowns → signals → cache
        logger.info("Test 1: Full pipeline integration")

        cache_adapter = DirectCacheAdapter()

        # Check initial state
        initial_overview = await cache_adapter.get_market_overview()
        initial_signals = await cache_adapter.get_signals()
        initial_movers = await cache_adapter.get_market_movers()

        # Run aggregation
        await aggregate_confluence_signals()
        await asyncio.sleep(3)

        # Check post-aggregation state
        final_overview = await cache_adapter.get_market_overview()
        final_signals = await cache_adapter.get_signals()
        final_movers = await cache_adapter.get_market_movers()

        # Validate data flow
        if final_signals.get('count', 0) == 0:
            results['issues'].append("Pipeline failed to populate signals")
            results['status'] = 'FAIL'

        if not final_overview.get('total_symbols'):
            results['issues'].append("Pipeline failed to populate market overview")

        if not final_movers.get('gainers') and not final_movers.get('losers'):
            results['issues'].append("Pipeline failed to populate market movers")

        # Test dashboard data consistency
        dashboard_data = await cache_adapter.get_dashboard_overview()

        if dashboard_data.get('data_source') == 'no_data':
            results['issues'].append("Dashboard shows no data after pipeline run")
            results['status'] = 'FAIL'

        results['metrics'] = {
            'initial_signals': initial_signals.get('count', 0),
            'final_signals': final_signals.get('count', 0),
            'dashboard_symbols': dashboard_data.get('summary', {}).get('total_symbols', 0),
            'gainers': len(final_movers.get('gainers', [])),
            'losers': len(final_movers.get('losers', [])),
            'data_source': dashboard_data.get('data_source')
        }

    except Exception as e:
        logger.error(f"Integration pipeline test error: {e}")
        results['issues'].append(f"Test exception: {str(e)}")
        results['status'] = 'FAIL'

    logger.info(f"Integration pipeline test: {results['status']}")
    return results

async def test_load_conditions():
    """Test under load conditions to ensure stability"""
    logger.info("=== Testing Load Conditions ===")

    detector = SessionLeakDetector()
    detector.start_monitoring()

    results = {
        'test_name': 'load_conditions',
        'status': 'PASS',
        'issues': [],
        'metrics': {}
    }

    try:
        exchange = BybitExchange('bybit')
        await exchange.initialize()

        # Simulate load with rapid requests
        tasks = []
        for i in range(20):
            task = exchange._make_request('GET', '/v5/market/time')
            tasks.append(task)

        # Execute concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze responses
        successful = 0
        errors = 0
        exceptions = 0

        for response in responses:
            if isinstance(response, Exception):
                exceptions += 1
                logger.error(f"Request exception: {response}")
            elif isinstance(response, dict) and response.get('retCode') == 0:
                successful += 1
            else:
                errors += 1

        # Check for "Request cancelled" events
        cancelled_events = sum(1 for r in responses
                             if isinstance(r, dict) and 'cancelled' in str(r).lower())

        if cancelled_events > 5:  # Allow some cancellations under extreme load
            results['issues'].append(f"Too many cancelled requests: {cancelled_events}")
            results['status'] = 'FAIL'

        if exceptions > 3:  # Allow few exceptions
            results['issues'].append(f"Too many request exceptions: {exceptions}")
            results['status'] = 'FAIL'

        # Test session stability after load
        await exchange._ensure_healthy_session()

        if not exchange.session or exchange.session.closed:
            results['issues'].append("Session not healthy after load test")
            results['status'] = 'FAIL'

        await exchange.close()

        # Check for leaks after load test
        leak_results = detector.stop_monitoring()

        session_leaks = [w for w in leak_results['warnings']
                        if 'unclosed' in w['message'].lower()]

        if len(session_leaks) > 1:  # Allow one potential leak
            results['issues'].append(f"Session leaks detected: {len(session_leaks)}")
            results['status'] = 'FAIL'

        results['metrics'] = {
            'total_requests': len(responses),
            'successful': successful,
            'errors': errors,
            'exceptions': exceptions,
            'cancelled': cancelled_events,
            'warnings': len(leak_results['warnings']),
            'session_leaks': len(session_leaks)
        }

    except Exception as e:
        logger.error(f"Load conditions test error: {e}")
        results['issues'].append(f"Test exception: {str(e)}")
        results['status'] = 'FAIL'

    logger.info(f"Load conditions test: {results['status']}")
    return results

async def main():
    """Run all validation tests"""
    logger.info("Starting Comprehensive AsyncIO Session Management Validation")

    # Suppress less important warnings for cleaner output
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    test_results = []

    try:
        # Run all tests
        tests = [
            test_session_lifecycle(),
            test_signals_cache_behavior(),
            test_integration_pipeline(),
            test_load_conditions()
        ]

        results = await asyncio.gather(*tests, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Test failed with exception: {result}")
                test_results.append({
                    'test_name': 'unknown',
                    'status': 'ERROR',
                    'issues': [str(result)]
                })
            else:
                test_results.append(result)

    except Exception as e:
        logger.error(f"Test suite error: {e}")

    # Generate summary report
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r['status'] == 'PASS')
    failed_tests = sum(1 for r in test_results if r['status'] == 'FAIL')
    error_tests = sum(1 for r in test_results if r['status'] == 'ERROR')

    logger.info("=" * 60)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Tests: {total_tests}")
    logger.info(f"Passed: {passed_tests}")
    logger.info(f"Failed: {failed_tests}")
    logger.info(f"Errors: {error_tests}")
    logger.info("=" * 60)

    for result in test_results:
        status_icon = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "⚠️"
        logger.info(f"{status_icon} {result['test_name']}: {result['status']}")

        if result.get('issues'):
            for issue in result['issues']:
                logger.info(f"   - {issue}")

        if result.get('metrics'):
            logger.info(f"   Metrics: {result['metrics']}")

    # Overall status
    overall_status = "PASS" if failed_tests == 0 and error_tests == 0 else "FAIL"
    logger.info("=" * 60)
    logger.info(f"OVERALL VALIDATION STATUS: {overall_status}")
    logger.info("=" * 60)

    # Save detailed results
    detailed_results = {
        'validation_timestamp': time.time(),
        'overall_status': overall_status,
        'summary': {
            'total_tests': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'errors': error_tests
        },
        'test_results': test_results
    }

    with open('validation_results.json', 'w') as f:
        json.dump(detailed_results, f, indent=2, default=str)

    logger.info("Detailed results saved to validation_results.json")

    return overall_status == "PASS"

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)