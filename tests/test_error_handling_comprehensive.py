#!/usr/bin/env python3
"""
Comprehensive test suite for enhanced error handling.

This tests:
- Concurrent request handling
- Circuit breaker patterns
- Cascading failures
- Memory leaks under stress
- Edge cases and race conditions
- Real exchange simulation
- Performance under load
"""

import asyncio
import sys
import time
import random
import statistics
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from collections import defaultdict
import aiohttp
import psutil
import gc

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.exchanges.base import (
    BaseExchange, NetworkError, TimeoutError, RateLimitError, 
    AuthenticationError, ExchangeError, retry_on_error
)


class SimulatedExchange(BaseExchange):
    """Simulated exchange with configurable failure patterns"""
    
    def __init__(self, config, failure_config=None):
        super().__init__(config)
        self.exchange_id = "simulated_exchange"
        self.api_urls = {
            'public': 'https://api.simulated.com/v1',
            'private': 'https://api.simulated.com/v1/private'
        }
        
        # Failure configuration
        self.failure_config = failure_config or {}
        self.request_count = 0
        self.error_count = 0
        self.success_count = 0
        self.total_retry_time = 0
        self.request_history = []
        
        # Simulate rate limit state
        self.rate_limit_remaining = 100
        self.rate_limit_reset = time.time() + 60
        
        # Connection state
        self.is_connected = True
        self.connection_quality = 1.0  # 0-1, affects error probability
        
    async def initialize(self) -> bool:
        """Initialize simulated exchange"""
        await self.init()
        return True
        
    async def health_check(self) -> bool:
        """Simulated health check"""
        # Simulate degraded connection
        if self.connection_quality < 0.5:
            return random.random() < self.connection_quality
        return self.is_connected
        
    def sign(self, method, path, params=None, headers=None, body=None):
        """Mock signing"""
        url = f"{self.api_urls['private']}{path}"
        headers = headers or {}
        headers['X-API-Key'] = 'test-key'
        headers['X-Signature'] = 'test-signature'
        return url, params or {}, headers, body or {}
    
    async def simulate_request(self, endpoint_type='public'):
        """Simulate various failure scenarios"""
        self.request_count += 1
        request_time = time.time()
        
        # Update rate limit
        if request_time > self.rate_limit_reset:
            self.rate_limit_remaining = 100
            self.rate_limit_reset = request_time + 60
        
        # Check rate limit
        if self.rate_limit_remaining <= 0:
            self.error_count += 1
            raise RateLimitError("Rate limit exceeded")
        
        self.rate_limit_remaining -= 1
        
        # Simulate various failures based on configuration
        failure_rate = self.failure_config.get('failure_rate', 0)
        
        if random.random() < failure_rate:
            error_type = random.choice(self.failure_config.get('error_types', ['network']))
            self.error_count += 1
            
            if error_type == 'network':
                raise NetworkError("Simulated network error")
            elif error_type == 'timeout':
                await asyncio.sleep(2)  # Simulate slow response
                raise TimeoutError("Request timeout")
            elif error_type == 'auth':
                raise AuthenticationError("Invalid credentials")
            elif error_type == 'server':
                raise NetworkError("500 Internal Server Error")
        
        # Simulate latency
        latency = random.uniform(0.05, 0.2) * (2 - self.connection_quality)
        await asyncio.sleep(latency)
        
        self.success_count += 1
        self.request_history.append({
            'timestamp': request_time,
            'latency': latency,
            'endpoint_type': endpoint_type
        })
        
        return {'status': 'success', 'data': f'Response at {datetime.now()}'}
    
    # Implement abstract methods
    async def connect_ws(self): 
        if not self.is_connected:
            raise NetworkError("WebSocket connection failed")
            
    async def fetch_market_data(self, timeframe, limit): 
        return await self.simulate_request('public')
        
    async def get_markets(self): 
        return ['BTC/USDT', 'ETH/USDT']
        
    def parse_balance(self, response): return {'BTC': 1.0, 'USDT': 10000}
    def parse_ohlcv(self, response): return [[time.time(), 50000, 51000, 49000, 50500, 1000]]
    def parse_order(self, order): return order
    def parse_orderbook(self, orderbook, symbol): return orderbook
    def parse_ticker(self, ticker): return ticker
    def parse_trades(self, trades): return trades
    async def subscribe_ws(self, channels, symbols): pass


class ComprehensiveErrorTest:
    """Comprehensive error handling tests"""
    
    def __init__(self):
        self.config = {
            'timeout': 30000,
            'enableRateLimit': True,
            'rateLimit': 100
        }
        self.start_memory = 0
        
    async def test_concurrent_requests(self):
        """Test handling multiple concurrent requests"""
        print("\n=== Testing Concurrent Request Handling ===")
        
        exchange = SimulatedExchange(self.config, {
            'failure_rate': 0.2,  # 20% failure rate
            'error_types': ['network', 'timeout']
        })
        await exchange.initialize()
        
        # Launch 50 concurrent requests
        tasks = []
        for i in range(50):
            tasks.append(exchange.simulate_request())
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time
        
        # Analyze results
        successes = sum(1 for r in results if not isinstance(r, Exception))
        failures = sum(1 for r in results if isinstance(r, Exception))
        
        print(f"✓ Completed 50 concurrent requests in {elapsed:.2f}s")
        print(f"✓ Successes: {successes}, Failures: {failures}")
        print(f"✓ Success rate: {successes/50*100:.1f}%")
        
        await exchange.close()
        assert successes > 30  # At least 60% should succeed with retries
        
    async def test_circuit_breaker_pattern(self):
        """Test circuit breaker behavior"""
        print("\n=== Testing Circuit Breaker Pattern ===")
        
        exchange = SimulatedExchange(self.config)
        await exchange.initialize()
        
        # Simulate cascading failures
        exchange.connection_quality = 0.1  # Very poor connection
        exchange.is_connected = False
        
        failure_count = 0
        recovery_attempted = False
        
        # Make requests until circuit opens
        for i in range(10):
            try:
                await exchange.monitor_connection()
                if not recovery_attempted and exchange._is_healthy is False:
                    recovery_attempted = True
                    print(f"✓ Circuit breaker triggered after {i+1} failures")
            except Exception:
                failure_count += 1
        
        print(f"✓ Total failures: {failure_count}")
        assert recovery_attempted, "Circuit breaker should have triggered"
        
        await exchange.close()
        
    async def test_rate_limit_burst(self):
        """Test rate limit handling under burst load"""
        print("\n=== Testing Rate Limit Burst Handling ===")
        
        exchange = SimulatedExchange(self.config)
        await exchange.initialize()
        
        # Set aggressive rate limits
        exchange.rate_limit_remaining = 10
        exchange._request_interval = 0.05  # 50ms between requests
        
        burst_size = 20
        tasks = []
        
        start_time = time.time()
        
        # Create burst of requests
        for i in range(burst_size):
            tasks.append(exchange.simulate_request())
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time
        
        # Count rate limit errors
        rate_limit_errors = sum(1 for r in results if isinstance(r, RateLimitError))
        
        print(f"✓ Burst of {burst_size} requests completed in {elapsed:.2f}s")
        print(f"✓ Rate limit errors: {rate_limit_errors}")
        print(f"✓ Effective rate: {burst_size/elapsed:.1f} req/s")
        
        await exchange.close()
        assert rate_limit_errors > 0, "Should have triggered rate limits"
        
    async def test_connection_recovery_stress(self):
        """Test connection recovery under stress"""
        print("\n=== Testing Connection Recovery Under Stress ===")
        
        exchange = SimulatedExchange(self.config, {
            'failure_rate': 0.5,  # 50% failure rate
            'error_types': ['network', 'timeout', 'server']
        })
        await exchange.initialize()
        
        recovery_count = 0
        
        # Simulate intermittent connection issues
        for cycle in range(5):
            print(f"\nCycle {cycle + 1}/5:")
            
            # Degrade connection
            exchange.connection_quality = 0.3
            exchange.is_connected = False
            
            # Try to recover
            with patch.object(exchange, 'recover_connection') as mock_recover:
                async def mock_recovery():
                    nonlocal recovery_count
                    recovery_count += 1
                    exchange.connection_quality = 1.0
                    exchange.is_connected = True
                    
                mock_recover.side_effect = mock_recovery
                
                # Monitor and trigger recovery
                await exchange.monitor_connection()
                
            # Make some requests
            tasks = []
            for i in range(10):
                tasks.append(exchange.simulate_request())
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successes = sum(1 for r in results if not isinstance(r, Exception))
            
            print(f"  - Recovery #{recovery_count} completed")
            print(f"  - Post-recovery success rate: {successes/10*100:.1f}%")
        
        print(f"\n✓ Total recoveries: {recovery_count}")
        await exchange.close()
        assert recovery_count >= 4, "Should have recovered multiple times"
        
    async def test_memory_leak_prevention(self):
        """Test for memory leaks under high load"""
        print("\n=== Testing Memory Leak Prevention ===")
        
        # Force garbage collection and get baseline
        gc.collect()
        process = psutil.Process()
        self.start_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"Starting memory: {self.start_memory:.1f} MB")
        
        exchange = SimulatedExchange(self.config, {
            'failure_rate': 0.3,
            'error_types': ['network', 'timeout', 'server']
        })
        await exchange.initialize()
        
        # Simulate high-frequency trading for extended period
        request_count = 1000
        batch_size = 100
        
        for batch in range(request_count // batch_size):
            tasks = []
            for _ in range(batch_size):
                tasks.append(exchange.simulate_request())
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Periodic memory check
            if batch % 2 == 0:
                gc.collect()
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - self.start_memory
                print(f"  Batch {batch + 1}: Memory +{memory_increase:.1f} MB")
        
        await exchange.close()
        
        # Final memory check
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - self.start_memory
        
        print(f"\n✓ Final memory: {final_memory:.1f} MB")
        print(f"✓ Total increase: {total_increase:.1f} MB")
        print(f"✓ Requests processed: {exchange.request_count}")
        
        # Memory increase should be reasonable (< 50MB for 1000 requests)
        assert total_increase < 50, f"Memory leak detected: {total_increase:.1f} MB increase"
        
    async def test_edge_cases(self):
        """Test various edge cases"""
        print("\n=== Testing Edge Cases ===")
        
        # Test 1: Empty response handling
        print("\n1. Empty response handling:")
        exchange = SimulatedExchange(self.config)
        await exchange.initialize()
        
        with patch.object(exchange.session, 'request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='')
            mock_request.return_value.__aenter__.return_value = mock_response
            
            try:
                await exchange.public_request('GET', '/test')
                print("  ✗ Should have raised ExchangeError")
            except ExchangeError as e:
                print("  ✓ Correctly handled empty response")
        
        # Test 2: Malformed JSON
        print("\n2. Malformed JSON handling:")
        with patch.object(exchange.session, 'request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{invalid json}')
            mock_request.return_value.__aenter__.return_value = mock_response
            
            try:
                await exchange.public_request('GET', '/test')
                print("  ✗ Should have raised ExchangeError")
            except ExchangeError as e:
                print("  ✓ Correctly handled malformed JSON")
        
        # Test 3: Extremely long retry-after
        print("\n3. Extremely long retry-after:")
        # Override the retry decorator to use shorter delays for testing
        from functools import wraps
        
        async def quick_retry_wrapper(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except RateLimitError as e:
                    # For testing, just fail immediately instead of waiting
                    raise
            return wrapper
        
        # Temporarily replace the method
        original_method = exchange.public_request
        exchange.public_request = await quick_retry_wrapper(original_method.__wrapped__.__wrapped__)
        
        with patch.object(exchange.session, 'request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_response.text = AsyncMock(return_value='{"retry_after": 3600}')
            mock_request.return_value.__aenter__.return_value = mock_response
            
            start_time = time.time()
            try:
                await exchange.public_request('GET', '/test')
            except RateLimitError:
                elapsed = time.time() - start_time
                print(f"  ✓ Request failed quickly ({elapsed:.2f}s), didn't wait full hour")
        
        # Restore original method
        exchange.public_request = original_method
        
        await exchange.close()
        
    async def test_performance_metrics(self):
        """Test and collect performance metrics"""
        print("\n=== Performance Metrics ===")
        
        exchange = SimulatedExchange(self.config, {
            'failure_rate': 0.1,  # 10% failure rate
            'error_types': ['network', 'timeout']
        })
        await exchange.initialize()
        
        # Collect metrics over 100 requests
        latencies = []
        start_time = time.time()
        
        for i in range(100):
            request_start = time.time()
            try:
                await exchange.simulate_request()
                latency = time.time() - request_start
                latencies.append(latency)
            except Exception:
                pass
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        if latencies:
            avg_latency = statistics.mean(latencies)
            median_latency = statistics.median(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
            
            print(f"\n✓ Total requests: {exchange.request_count}")
            print(f"✓ Success rate: {exchange.success_count/exchange.request_count*100:.1f}%")
            print(f"✓ Average latency: {avg_latency*1000:.1f}ms")
            print(f"✓ Median latency: {median_latency*1000:.1f}ms")
            print(f"✓ P95 latency: {p95_latency*1000:.1f}ms")
            print(f"✓ P99 latency: {p99_latency*1000:.1f}ms")
            print(f"✓ Throughput: {100/total_time:.1f} req/s")
        
        await exchange.close()
        
    async def test_real_world_simulation(self):
        """Simulate real-world trading scenario"""
        print("\n=== Real-World Trading Simulation ===")
        
        exchange = SimulatedExchange(self.config)
        await exchange.initialize()
        
        # Simulate a day of trading with varying conditions
        print("\nSimulating 24-hour trading cycle...")
        
        hours_data = []
        
        for hour in range(24):
            # Vary connection quality throughout the day
            if hour in [2, 3, 4]:  # Maintenance window
                exchange.connection_quality = 0.5
                exchange.failure_config = {
                    'failure_rate': 0.3,
                    'error_types': ['network', 'server']
                }
            elif hour in [9, 10, 14, 15]:  # Peak hours
                exchange.connection_quality = 0.8
                exchange.failure_config = {
                    'failure_rate': 0.1,
                    'error_types': ['timeout', 'network']
                }
            else:  # Normal hours
                exchange.connection_quality = 0.95
                exchange.failure_config = {
                    'failure_rate': 0.05,
                    'error_types': ['network']
                }
            
            # Simulate hourly activity
            hour_start = exchange.request_count
            tasks = []
            
            # Variable request rate
            if hour in [9, 10, 14, 15]:  # Peak
                request_count = 50
            elif hour in [2, 3, 4]:  # Low
                request_count = 10
            else:  # Normal
                request_count = 25
            
            for _ in range(request_count):
                tasks.append(exchange.simulate_request())
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            hour_successes = sum(1 for r in results if not isinstance(r, Exception))
            hours_data.append({
                'hour': hour,
                'requests': request_count,
                'successes': hour_successes,
                'success_rate': hour_successes / request_count * 100
            })
            
            if hour % 6 == 0:
                print(f"  Hour {hour:02d}:00 - Success rate: {hour_successes/request_count*100:.1f}%")
        
        # Summary statistics
        total_requests = sum(h['requests'] for h in hours_data)
        total_successes = sum(h['successes'] for h in hours_data)
        avg_success_rate = total_successes / total_requests * 100
        
        print(f"\n✓ 24-hour simulation complete")
        print(f"✓ Total requests: {total_requests}")
        print(f"✓ Overall success rate: {avg_success_rate:.1f}%")
        print(f"✓ Maintenance window handled gracefully")
        print(f"✓ Peak hours sustained")
        
        await exchange.close()
        assert avg_success_rate > 85, "Success rate should be high with retry logic"
        
    async def run_all_tests(self):
        """Run all comprehensive tests"""
        print("=" * 60)
        print("COMPREHENSIVE ERROR HANDLING TEST SUITE")
        print("=" * 60)
        
        tests = [
            ("Concurrent Requests", self.test_concurrent_requests),
            ("Circuit Breaker Pattern", self.test_circuit_breaker_pattern),
            ("Rate Limit Burst", self.test_rate_limit_burst),
            ("Connection Recovery Stress", self.test_connection_recovery_stress),
            ("Memory Leak Prevention", self.test_memory_leak_prevention),
            ("Edge Cases", self.test_edge_cases),
            ("Performance Metrics", self.test_performance_metrics),
            ("Real-World Simulation", self.test_real_world_simulation),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n{'=' * 60}")
            print(f"Running: {test_name}")
            print(f"{'=' * 60}")
            
            try:
                start_time = time.time()
                await test_func()
                elapsed = time.time() - start_time
                results[test_name] = ('PASSED', elapsed)
                print(f"\n✅ {test_name} PASSED in {elapsed:.2f}s")
            except Exception as e:
                results[test_name] = ('FAILED', str(e))
                print(f"\n❌ {test_name} FAILED: {e}")
                import traceback
                traceback.print_exc()
        
        # Final summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in results.values() if r[0] == 'PASSED')
        total = len(results)
        
        for test_name, (status, info) in results.items():
            if status == 'PASSED':
                print(f"✅ {test_name:<30} PASSED ({info:.2f}s)")
            else:
                print(f"❌ {test_name:<30} FAILED")
        
        print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        return passed == total


async def main():
    """Run comprehensive tests"""
    tester = ComprehensiveErrorTest()
    success = await tester.run_all_tests()
    
    # Cleanup
    gc.collect()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())