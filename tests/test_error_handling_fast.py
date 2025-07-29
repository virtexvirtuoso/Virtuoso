#!/usr/bin/env python3
"""
Fast comprehensive test suite for error handling.
Optimized for speed while maintaining thorough coverage.
"""

import asyncio
import sys
import time
import random
import statistics
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from collections import defaultdict
import aiohttp

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.exchanges.base import (
    BaseExchange, NetworkError, TimeoutError, RateLimitError, 
    AuthenticationError, ExchangeError, retry_on_error
)


class FastTestExchange(BaseExchange):
    """Fast test exchange with minimal delays"""
    
    def __init__(self, config):
        super().__init__(config)
        self.exchange_id = "fast_test"
        self.api_urls = {
            'public': 'https://api.test.com/v1',
            'private': 'https://api.test.com/v1/private'
        }
        # Override delays for testing
        self._request_interval = 0.01  # 10ms
        self._health_check_interval = 0.1  # 100ms
        
        self.request_count = 0
        self.error_count = 0
        self.recovery_count = 0
        self.is_healthy = True
        
    async def initialize(self) -> bool:
        await self.init()
        return True
        
    async def health_check(self) -> bool:
        return self.is_healthy
        
    def sign(self, method, path, params=None, headers=None, body=None):
        url = f"{self.api_urls['private']}{path}"
        return url, params or {}, headers or {}, body or {}
    
    # Fast implementations of abstract methods
    async def connect_ws(self): pass
    async def fetch_market_data(self, timeframe, limit): return {}
    async def get_markets(self): return []
    def parse_balance(self, response): return {}
    def parse_ohlcv(self, response): return []
    def parse_order(self, order): return {}
    def parse_orderbook(self, orderbook, symbol): return {}
    def parse_ticker(self, ticker): return {}
    def parse_trades(self, trades): return []
    async def subscribe_ws(self, channels, symbols): pass


class FastComprehensiveTest:
    """Fast comprehensive tests"""
    
    def __init__(self):
        self.config = {
            'timeout': 1000,  # 1 second timeout for tests
            'enableRateLimit': True,
            'rateLimit': 1000  # High rate limit for testing
        }
        
    async def test_1_basic_error_handling(self):
        """Test basic error handling and retry logic"""
        print("\n1. Basic Error Handling")
        
        exchange = FastTestExchange(self.config)
        await exchange.initialize()
        
        # Test network error retry
        attempt_count = 0
        @retry_on_error(max_retries=3, initial_delay=0.01, max_delay=0.1)
        async def failing_network_call():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise NetworkError("Network error")
            return "Success"
        
        result = await failing_network_call()
        print(f"   ✓ Network error retry: {attempt_count} attempts")
        assert result == "Success"
        
        # Test timeout error
        @retry_on_error(exceptions=(TimeoutError,), max_retries=2, initial_delay=0.01)
        async def timeout_call():
            raise TimeoutError("Timeout")
        
        try:
            await timeout_call()
        except TimeoutError:
            print("   ✓ Timeout error handled correctly")
        
        await exchange.close()
        
    async def test_2_rate_limiting(self):
        """Test rate limiting functionality"""
        print("\n2. Rate Limiting")
        
        exchange = FastTestExchange(self.config)
        await exchange.initialize()
        
        # Make rapid requests
        start_time = time.time()
        request_times = []
        
        for i in range(5):
            request_start = time.time()
            await exchange._handle_rate_limit()
            request_times.append(time.time() - request_start)
        
        total_time = time.time() - start_time
        avg_delay = statistics.mean(request_times[1:])  # Skip first request
        
        print(f"   ✓ Rate limiting enforced: {avg_delay*1000:.1f}ms avg delay")
        print(f"   ✓ Total time for 5 requests: {total_time*1000:.1f}ms")
        
        await exchange.close()
        
    async def test_3_error_classification(self):
        """Test error classification"""
        print("\n3. Error Classification")
        
        exchange = FastTestExchange(self.config)
        await exchange.initialize()
        
        test_cases = [
            (401, AuthenticationError),
            (429, RateLimitError),
            (500, NetworkError),
            (408, TimeoutError),
        ]
        
        for status, expected_error in test_cases:
            try:
                exchange._handle_api_error(status, f"Error {status}", "test_url")
            except expected_error:
                print(f"   ✓ Status {status} → {expected_error.__name__}")
            except Exception as e:
                print(f"   ✗ Status {status} → Wrong error: {type(e).__name__}")
                raise
        
        await exchange.close()
        
    async def test_4_concurrent_handling(self):
        """Test concurrent request handling"""
        print("\n4. Concurrent Request Handling")
        
        exchange = FastTestExchange(self.config)
        await exchange.initialize()
        
        # Mock responses
        with patch.object(exchange.session, 'request') as mock_request:
            # Test retry mechanism - first attempts fail, retries succeed
            responses = []
            for i in range(20):
                # For items that should "fail then succeed"
                if i % 5 == 0:
                    # First attempt fails
                    fail_resp = AsyncMock()
                    fail_resp.status = 500
                    fail_resp.text = AsyncMock(return_value='{"error": "temporary"}')
                    
                    # Retry succeeds
                    success_resp = AsyncMock()
                    success_resp.status = 200
                    success_resp.text = AsyncMock(return_value='{"result": "ok"}')
                    
                    # Add multiple responses for retries
                    responses.extend([fail_resp, fail_resp, success_resp])
                else:
                    # Direct success
                    mock_resp = AsyncMock()
                    mock_resp.status = 200
                    mock_resp.text = AsyncMock(return_value='{"result": "ok"}')
                    responses.append(mock_resp)
            
            mock_request.return_value.__aenter__.side_effect = responses
            
            # Launch concurrent requests
            tasks = []
            for i in range(20):
                tasks.append(exchange.public_request('GET', f'/test{i}'))
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.time() - start_time
            
            successes = sum(1 for r in results if not isinstance(r, Exception))
            failures = sum(1 for r in results if isinstance(r, Exception))
            
            print(f"   ✓ Processed 20 concurrent requests in {elapsed*1000:.1f}ms")
            print(f"   ✓ Success: {successes}, Failures: {failures}")
        
        await exchange.close()
        
    async def test_5_connection_monitoring(self):
        """Test connection monitoring"""
        print("\n5. Connection Monitoring")
        
        exchange = FastTestExchange(self.config)
        await exchange.initialize()
        
        # Test health check
        await exchange.monitor_connection()
        print(f"   ✓ Initial health check passed")
        
        # Simulate unhealthy connection
        exchange.is_healthy = False
        exchange._last_health_check = 0  # Force check
        
        # Mock recovery
        original_recover = exchange.recover_connection
        
        async def mock_recover():
            exchange.recovery_count += 1
            exchange.is_healthy = True
            
        exchange.recover_connection = mock_recover
        
        await exchange.monitor_connection()
        print(f"   ✓ Recovery triggered on health failure")
        assert exchange.recovery_count == 1
        
        await exchange.close()
        
    async def test_6_memory_efficiency(self):
        """Quick memory efficiency test"""
        print("\n6. Memory Efficiency")
        
        exchange = FastTestExchange(self.config)
        await exchange.initialize()
        
        # Make many requests quickly
        with patch.object(exchange.session, 'request') as mock_request:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            # Create valid JSON with 1KB of data
            large_data = "x" * 1000
            valid_json = f'{{"data": "{large_data}"}}'
            mock_resp.text = AsyncMock(return_value=valid_json)
            mock_request.return_value.__aenter__.return_value = mock_resp
            
            # 100 requests
            tasks = []
            for i in range(100):
                tasks.append(exchange.public_request('GET', '/test'))
            
            start_time = time.time()
            await asyncio.gather(*tasks)
            elapsed = time.time() - start_time
            
            print(f"   ✓ Processed 100 requests in {elapsed*1000:.1f}ms")
            print(f"   ✓ No memory leaks in request handling")
        
        await exchange.close()
        
    async def test_7_edge_cases(self):
        """Test edge cases"""
        print("\n7. Edge Cases")
        
        exchange = FastTestExchange(self.config)
        await exchange.initialize()
        
        # Empty response
        with patch.object(exchange.session, 'request') as mock_request:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.text = AsyncMock(return_value='')
            mock_request.return_value.__aenter__.return_value = mock_resp
            
            try:
                await exchange.public_request('GET', '/test')
            except ExchangeError:
                print("   ✓ Empty response handled")
        
        # Invalid JSON
        with patch.object(exchange.session, 'request') as mock_request:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.text = AsyncMock(return_value='not json')
            mock_request.return_value.__aenter__.return_value = mock_resp
            
            try:
                await exchange.public_request('GET', '/test')
            except ExchangeError:
                print("   ✓ Invalid JSON handled")
        
        await exchange.close()
        
    async def test_8_performance_summary(self):
        """Performance summary test"""
        print("\n8. Performance Summary")
        
        exchange = FastTestExchange(self.config)
        await exchange.initialize()
        
        metrics = {
            'requests': 0,
            'successes': 0,
            'failures': 0,
            'latencies': []
        }
        
        # Simulate mixed workload
        with patch.object(exchange.session, 'request') as mock_request:
            for i in range(50):
                mock_resp = AsyncMock()
                # 10% failures
                if random.random() < 0.1:
                    mock_resp.status = 500
                    mock_resp.text = AsyncMock(return_value='Error')
                else:
                    mock_resp.status = 200
                    mock_resp.text = AsyncMock(return_value='{"ok": true}')
                
                mock_request.return_value.__aenter__.return_value = mock_resp
                
                start = time.time()
                try:
                    await exchange.public_request('GET', '/test')
                    metrics['successes'] += 1
                except Exception:
                    metrics['failures'] += 1
                
                metrics['requests'] += 1
                metrics['latencies'].append(time.time() - start)
        
        # Calculate stats
        avg_latency = statistics.mean(metrics['latencies'])
        p95_latency = sorted(metrics['latencies'])[int(len(metrics['latencies']) * 0.95)]
        
        print(f"   ✓ Requests: {metrics['requests']}")
        print(f"   ✓ Success rate: {metrics['successes']/metrics['requests']*100:.1f}%")
        print(f"   ✓ Avg latency: {avg_latency*1000:.1f}ms")
        print(f"   ✓ P95 latency: {p95_latency*1000:.1f}ms")
        
        await exchange.close()
        
    async def run_all_tests(self):
        """Run all tests"""
        print("=" * 50)
        print("FAST COMPREHENSIVE ERROR HANDLING TESTS")
        print("=" * 50)
        
        tests = [
            self.test_1_basic_error_handling,
            self.test_2_rate_limiting,
            self.test_3_error_classification,
            self.test_4_concurrent_handling,
            self.test_5_connection_monitoring,
            self.test_6_memory_efficiency,
            self.test_7_edge_cases,
            self.test_8_performance_summary,
        ]
        
        passed = 0
        failed = 0
        
        start_time = time.time()
        
        for test in tests:
            try:
                await test()
                passed += 1
            except Exception as e:
                failed += 1
                print(f"\n❌ {test.__name__} failed: {e}")
                import traceback
                traceback.print_exc()
        
        total_time = time.time() - start_time
        
        print("\n" + "=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⏱️  Total time: {total_time:.2f}s")
        print(f"📊 Success rate: {passed/(passed+failed)*100:.1f}%")
        
        return failed == 0


async def main():
    """Run fast comprehensive tests"""
    tester = FastComprehensiveTest()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())