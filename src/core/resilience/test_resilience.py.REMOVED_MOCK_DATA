"""
Comprehensive Test Suite for Resilience Patterns.

This module provides comprehensive tests demonstrating resilience patterns
under various failure scenarios including:
- Circuit breaker state transitions and recovery
- Retry policy behavior with different failure types
- Connection pool exhaustion and recovery
- Health check failure detection and alerting
- Graceful degradation and fallback mechanisms
"""

import asyncio
import logging
import time
import random
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from unittest.mock import Mock, AsyncMock
import traceback

from .circuit_breaker import (
    CircuitBreaker, 
    CircuitBreakerConfig, 
    CircuitBreakerState, 
    CircuitBreakerError
)
from .retry_policy import (
    RetryPolicy, 
    RetryConfig, 
    BackoffStrategy,
    create_exponential_retry
)
from .connection_pool import (
    ConnectionPoolManager, 
    PoolConfig,
    get_connection_pool_manager
)
from .health_check import (
    HealthCheckService, 
    HealthCheck, 
    ServiceStatus,
    HealthCheckConfig,
    SimpleHealthCheck,
    get_health_service
)
from .exchange_adapter import (
    ResilientExchangeAdapter,
    ExchangeResilienceConfig
)
from .cache_adapter import (
    ResilientCacheAdapter,
    CacheResilienceConfig
)

logger = logging.getLogger(__name__)


@dataclass
class TestMetrics:
    """Metrics collected during resilience testing."""
    
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    circuit_breaker_trips: int = 0
    retry_attempts: int = 0
    fallback_activations: int = 0
    recovery_events: int = 0
    average_response_time: float = 0.0
    test_duration: float = 0.0


class FailureSimulator:
    """Simulates various types of failures for testing resilience patterns."""
    
    def __init__(self):
        self.failure_rate = 0.0
        self.failure_duration = 0.0
        self.failure_start_time = 0.0
        self.consecutive_failures = 0
        self.is_failing = False
    
    def set_failure_scenario(self, failure_rate: float, duration: float = 0.0):
        """Set failure scenario parameters."""
        self.failure_rate = failure_rate
        self.failure_duration = duration
        if duration > 0:
            self.failure_start_time = time.time()
            self.is_failing = True
    
    def should_fail(self) -> bool:
        """Determine if operation should fail based on current scenario."""
        # Time-based failure
        if self.failure_duration > 0:
            elapsed = time.time() - self.failure_start_time
            if elapsed < self.failure_duration:
                return True
            else:
                self.is_failing = False
                return False
        
        # Random failure rate
        return random.random() < self.failure_rate
    
    def simulate_failure(self, operation_name: str = "test_operation"):
        """Simulate a failure by raising an exception."""
        failure_types = [
            ConnectionError(f"Connection failed for {operation_name}"),
            TimeoutError(f"Timeout occurred for {operation_name}"),
            OSError(f"OS error for {operation_name}"),
        ]
        
        raise random.choice(failure_types)


class MockExchange:
    """Mock exchange for testing resilient exchange adapter."""
    
    def __init__(self, failure_simulator: FailureSimulator):
        self.id = "mock_exchange"
        self.failure_simulator = failure_simulator
        self._operation_count = 0
    
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Mock fetch ticker with failure simulation."""
        self._operation_count += 1
        
        if self.failure_simulator.should_fail():
            self.failure_simulator.simulate_failure("fetch_ticker")
        
        # Simulate network delay
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        return {
            'symbol': symbol,
            'last': random.uniform(30000, 50000),
            'timestamp': time.time() * 1000,
            'operation_count': self._operation_count
        }
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', since: Optional[int] = None, limit: Optional[int] = None) -> List[List]:
        """Mock fetch OHLCV with failure simulation."""
        self._operation_count += 1
        
        if self.failure_simulator.should_fail():
            self.failure_simulator.simulate_failure("fetch_ohlcv")
        
        await asyncio.sleep(random.uniform(0.2, 0.8))
        
        # Return mock OHLCV data
        return [[
            int(time.time() * 1000),
            random.uniform(30000, 50000),
            random.uniform(30000, 50000),
            random.uniform(30000, 50000),
            random.uniform(30000, 50000),
            random.uniform(100, 1000)
        ] for _ in range(limit or 10)]


class MockCacheClient:
    """Mock cache client for testing resilient cache adapter."""
    
    def __init__(self, failure_simulator: FailureSimulator):
        self.failure_simulator = failure_simulator
        self._storage: Dict[str, Any] = {}
        self._operation_count = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """Mock cache get with failure simulation."""
        self._operation_count += 1
        
        if self.failure_simulator.should_fail():
            self.failure_simulator.simulate_failure("cache_get")
        
        await asyncio.sleep(random.uniform(0.01, 0.05))
        return self._storage.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Mock cache set with failure simulation."""
        self._operation_count += 1
        
        if self.failure_simulator.should_fail():
            self.failure_simulator.simulate_failure("cache_set")
        
        await asyncio.sleep(random.uniform(0.01, 0.05))
        self._storage[key] = value
        return True
    
    async def delete(self, key: str) -> bool:
        """Mock cache delete with failure simulation."""
        self._operation_count += 1
        
        if self.failure_simulator.should_fail():
            self.failure_simulator.simulate_failure("cache_delete")
        
        await asyncio.sleep(random.uniform(0.01, 0.05))
        return self._storage.pop(key, None) is not None


class ResilienceTestSuite:
    """Comprehensive test suite for resilience patterns."""
    
    def __init__(self):
        self.failure_simulator = FailureSimulator()
        self.metrics = TestMetrics()
        self.test_results: Dict[str, Dict[str, Any]] = {}
    
    async def test_circuit_breaker_basic_functionality(self) -> Dict[str, Any]:
        """Test basic circuit breaker functionality."""
        logger.info("Testing circuit breaker basic functionality")
        
        config = CircuitBreakerConfig(
            name="test_cb",
            failure_threshold=3,
            success_threshold=2,
            timeout=2.0
        )
        
        circuit_breaker = CircuitBreaker(config)
        test_results = {
            'operations': 0,
            'failures': 0,
            'circuit_breaker_trips': 0,
            'state_transitions': []
        }
        
        async def failing_operation():
            test_results['operations'] += 1
            if test_results['operations'] <= 5:  # First 5 operations fail
                test_results['failures'] += 1
                raise ConnectionError("Simulated failure")
            return "success"
        
        # Test failure accumulation and circuit opening
        for i in range(10):
            try:
                result = await circuit_breaker.call_async(failing_operation)
                logger.info(f"Operation {i+1}: Success - {result}")
            except CircuitBreakerError:
                test_results['circuit_breaker_trips'] += 1
                logger.info(f"Operation {i+1}: Circuit breaker open")
            except Exception as e:
                logger.info(f"Operation {i+1}: Failed - {e}")
            
            # Record state transitions
            current_state = circuit_breaker.state.value
            if not test_results['state_transitions'] or test_results['state_transitions'][-1] != current_state:
                test_results['state_transitions'].append(current_state)
            
            await asyncio.sleep(0.1)
        
        # Wait for circuit breaker timeout and test recovery
        logger.info("Waiting for circuit breaker timeout...")
        await asyncio.sleep(2.5)
        
        # Test recovery
        for i in range(5):
            try:
                result = await circuit_breaker.call_async(failing_operation)
                logger.info(f"Recovery operation {i+1}: Success - {result}")
            except Exception as e:
                logger.info(f"Recovery operation {i+1}: Failed - {e}")
            
            current_state = circuit_breaker.state.value
            if not test_results['state_transitions'] or test_results['state_transitions'][-1] != current_state:
                test_results['state_transitions'].append(current_state)
        
        test_results['final_metrics'] = circuit_breaker.get_metrics()
        return test_results
    
    async def test_retry_policy_with_different_backoff_strategies(self) -> Dict[str, Any]:
        """Test retry policy with different backoff strategies."""
        logger.info("Testing retry policy with different backoff strategies")
        
        test_results = {}
        
        # Test exponential backoff
        exponential_retry = create_exponential_retry(
            name="exponential_test",
            max_attempts=4,
            base_delay=0.1,
            max_delay=2.0,
            jitter=True
        )
        
        async def intermittent_failure():
            if random.random() < 0.7:  # 70% failure rate
                raise ConnectionError("Random failure")
            return "success"
        
        exponential_results = {'attempts': [], 'successes': 0, 'failures': 0}
        
        for i in range(10):
            start_time = time.time()
            try:
                result = await exponential_retry.call_async(intermittent_failure)
                exponential_results['successes'] += 1
                exponential_results['attempts'].append({
                    'operation': i+1,
                    'result': 'success',
                    'duration': time.time() - start_time
                })
            except Exception as e:
                exponential_results['failures'] += 1
                exponential_results['attempts'].append({
                    'operation': i+1,
                    'result': 'failure',
                    'exception': str(e),
                    'duration': time.time() - start_time
                })
        
        exponential_results['metrics'] = exponential_retry.get_metrics()
        test_results['exponential_backoff'] = exponential_results
        
        return test_results
    
    async def test_connection_pool_exhaustion_and_recovery(self) -> Dict[str, Any]:
        """Test connection pool behavior under load and exhaustion."""
        logger.info("Testing connection pool exhaustion and recovery")
        
        pool_manager = get_connection_pool_manager()
        
        # Configure small pool for testing
        config = PoolConfig(
            name="test_pool",
            max_connections=5,
            max_connections_per_host=3,
            connect_timeout=1.0,
            request_timeout=2.0,
            pool_timeout=1.0
        )
        
        pool = pool_manager.get_pool("test_pool", config)
        await pool.initialize()
        
        test_results = {
            'concurrent_requests': 20,
            'successful_requests': 0,
            'failed_requests': 0,
            'pool_timeouts': 0,
            'request_times': []
        }
        
        async def make_request(request_id: int):
            start_time = time.time()
            try:
                async with pool.get_session() as session:
                    # Simulate work
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    test_results['successful_requests'] += 1
                    return f"request_{request_id}_success"
            except Exception as e:
                test_results['failed_requests'] += 1
                if "pool timeout" in str(e).lower() or "timeout" in str(e).lower():
                    test_results['pool_timeouts'] += 1
                return f"request_{request_id}_failed: {e}"
            finally:
                test_results['request_times'].append(time.time() - start_time)
        
        # Launch concurrent requests to exhaust pool
        tasks = [make_request(i) for i in range(test_results['concurrent_requests'])]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        test_results['results'] = [str(r) for r in results]
        test_results['pool_metrics'] = pool.get_metrics()
        
        await pool.close()
        return test_results
    
    async def test_health_check_failure_detection(self) -> Dict[str, Any]:
        """Test health check failure detection and status reporting."""
        logger.info("Testing health check failure detection")
        
        health_service = get_health_service()
        test_results = {
            'health_checks': [],
            'status_changes': [],
            'final_status': None
        }
        
        # Create a health check that will fail after some time
        failure_after_calls = 3
        call_count = 0
        
        async def test_health_check():
            nonlocal call_count
            call_count += 1
            
            if call_count > failure_after_calls:
                raise ConnectionError("Simulated service failure")
            
            return True
        
        config = HealthCheckConfig(
            name="test_health_check",
            interval=0.5,  # Fast interval for testing
            timeout=1.0,
            consecutive_failures=2,
            consecutive_successes=2
        )
        
        health_check = SimpleHealthCheck(
            "test_service",
            test_health_check,
            config
        )
        
        # Add status change listener
        async def status_listener(status):
            test_results['status_changes'].append({
                'timestamp': time.time(),
                'status': status.value
            })
            logger.info(f"Health status changed to: {status.value}")
        
        health_service.add_status_listener(status_listener)
        health_service.register_health_check(health_check)
        
        # Let it run for a while to see status changes
        await asyncio.sleep(5)
        
        # Perform manual health checks
        for i in range(3):
            result = await health_service.check_health("test_service")
            test_results['health_checks'].append({
                'check_number': i + 1,
                'status': result.status.value,
                'message': result.message,
                'timestamp': result.timestamp
            })
        
        test_results['final_status'] = health_service.get_overall_status().value
        test_results['health_metrics'] = health_service.get_metrics()
        
        health_service.unregister_health_check("test_service")
        return test_results
    
    async def test_resilient_exchange_under_failures(self) -> Dict[str, Any]:
        """Test resilient exchange adapter behavior under various failures."""
        logger.info("Testing resilient exchange under failures")
        
        # Create mock exchange with failure simulator
        mock_exchange = MockExchange(self.failure_simulator)
        
        config = ExchangeResilienceConfig(
            exchange_name="mock_exchange",
            failure_threshold=3,
            success_threshold=2,
            circuit_timeout=2.0,
            max_retries=3,
            base_retry_delay=0.1,
            max_retry_delay=1.0
        )
        
        resilient_exchange = ResilientExchangeAdapter(mock_exchange, config)
        await resilient_exchange.initialize()
        
        test_results = {
            'scenarios': {},
            'final_metrics': None
        }
        
        # Scenario 1: High failure rate
        logger.info("Scenario 1: High failure rate (70%)")
        self.failure_simulator.set_failure_scenario(0.7)
        
        scenario1_results = {'operations': 0, 'successes': 0, 'failures': 0}
        
        for i in range(10):
            try:
                ticker = await resilient_exchange.fetch_ticker('BTCUSDT')
                scenario1_results['successes'] += 1
                logger.debug(f"Success: {ticker['symbol']}")
            except Exception as e:
                scenario1_results['failures'] += 1
                logger.debug(f"Failed: {e}")
            scenario1_results['operations'] += 1
        
        test_results['scenarios']['high_failure_rate'] = scenario1_results
        
        # Scenario 2: Complete failure for a period
        logger.info("Scenario 2: Complete failure for 3 seconds")
        self.failure_simulator.set_failure_scenario(1.0, duration=3.0)
        
        scenario2_results = {'operations': 0, 'successes': 0, 'failures': 0, 'circuit_breaker_trips': 0}
        
        for i in range(15):
            try:
                ohlcv = await resilient_exchange.fetch_ohlcv('BTCUSDT', '1m', limit=5)
                scenario2_results['successes'] += 1
                logger.debug(f"Success: {len(ohlcv)} candles")
            except Exception as e:
                scenario2_results['failures'] += 1
                if "circuit breaker" in str(e).lower():
                    scenario2_results['circuit_breaker_trips'] += 1
                logger.debug(f"Failed: {e}")
            scenario2_results['operations'] += 1
            
            await asyncio.sleep(0.3)
        
        test_results['scenarios']['temporary_outage'] = scenario2_results
        
        # Reset failure simulator
        self.failure_simulator.set_failure_scenario(0.0)
        
        # Scenario 3: Recovery testing
        logger.info("Scenario 3: Recovery testing")
        scenario3_results = {'operations': 0, 'successes': 0, 'failures': 0}
        
        for i in range(5):
            try:
                ticker = await resilient_exchange.fetch_ticker('ETHUSDT')
                scenario3_results['successes'] += 1
                logger.debug(f"Recovery success: {ticker['symbol']}")
            except Exception as e:
                scenario3_results['failures'] += 1
                logger.debug(f"Recovery failed: {e}")
            scenario3_results['operations'] += 1
        
        test_results['scenarios']['recovery'] = scenario3_results
        test_results['final_metrics'] = resilient_exchange.get_metrics()
        
        await resilient_exchange.close()
        return test_results
    
    async def test_resilient_cache_with_fallback(self) -> Dict[str, Any]:
        """Test resilient cache adapter with fallback mechanisms."""
        logger.info("Testing resilient cache with fallback")
        
        # Create mock cache client
        mock_cache = MockCacheClient(self.failure_simulator)
        
        config = CacheResilienceConfig(
            cache_name="mock_cache",
            failure_threshold=2,
            success_threshold=2,
            circuit_timeout=2.0,
            max_retries=2,
            base_retry_delay=0.05,
            enable_fallback=True,
            fallback_to_memory=True,
            fallback_ttl=60.0
        )
        
        resilient_cache = ResilientCacheAdapter(mock_cache, config)
        await resilient_cache.initialize()
        
        test_results = {
            'scenarios': {},
            'final_metrics': None
        }
        
        # Scenario 1: Normal operation
        logger.info("Scenario 1: Normal cache operation")
        self.failure_simulator.set_failure_scenario(0.0)
        
        scenario1_results = {'sets': 0, 'gets': 0, 'hits': 0, 'misses': 0}
        
        # Set some values
        for i in range(5):
            try:
                await resilient_cache.set(f"key_{i}", f"value_{i}", ttl=60)
                scenario1_results['sets'] += 1
            except Exception as e:
                logger.error(f"Set failed: {e}")
        
        # Get values
        for i in range(7):  # Try to get more than we set
            try:
                value = await resilient_cache.get(f"key_{i}")
                scenario1_results['gets'] += 1
                if value is not None:
                    scenario1_results['hits'] += 1
                else:
                    scenario1_results['misses'] += 1
            except Exception as e:
                logger.error(f"Get failed: {e}")
        
        test_results['scenarios']['normal_operation'] = scenario1_results
        
        # Scenario 2: Cache failure with fallback
        logger.info("Scenario 2: Cache failure with fallback")
        
        # First, populate cache and fallback
        await resilient_cache.set("fallback_test", "fallback_value", ttl=60)
        
        # Now simulate cache failure
        self.failure_simulator.set_failure_scenario(1.0)
        
        scenario2_results = {'operations': 0, 'fallback_hits': 0, 'total_failures': 0}
        
        for i in range(10):
            try:
                # Try to get the value we just set
                value = await resilient_cache.get("fallback_test")
                scenario2_results['operations'] += 1
                if value == "fallback_value":
                    scenario2_results['fallback_hits'] += 1
                    logger.debug("Fallback cache hit!")
            except Exception as e:
                scenario2_results['total_failures'] += 1
                logger.debug(f"Operation failed: {e}")
        
        test_results['scenarios']['cache_failure_fallback'] = scenario2_results
        
        # Reset failure simulator
        self.failure_simulator.set_failure_scenario(0.0)
        
        test_results['final_metrics'] = resilient_cache.get_metrics()
        
        await resilient_cache.close()
        return test_results
    
    async def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run the complete resilience test suite."""
        logger.info("Starting comprehensive resilience test suite")
        
        start_time = time.time()
        comprehensive_results = {
            'test_suite_info': {
                'start_time': start_time,
                'end_time': None,
                'duration': None,
                'tests_run': 0,
                'tests_passed': 0,
                'tests_failed': 0
            },
            'test_results': {}
        }
        
        # Define all tests
        tests = [
            ('circuit_breaker_basic', self.test_circuit_breaker_basic_functionality),
            ('retry_policy_backoff', self.test_retry_policy_with_different_backoff_strategies),
            ('connection_pool_exhaustion', self.test_connection_pool_exhaustion_and_recovery),
            ('health_check_detection', self.test_health_check_failure_detection),
            ('resilient_exchange', self.test_resilient_exchange_under_failures),
            ('resilient_cache_fallback', self.test_resilient_cache_with_fallback),
        ]
        
        # Run each test
        for test_name, test_func in tests:
            comprehensive_results['test_suite_info']['tests_run'] += 1
            logger.info(f"Running test: {test_name}")
            
            try:
                test_result = await test_func()
                comprehensive_results['test_results'][test_name] = {
                    'status': 'passed',
                    'results': test_result
                }
                comprehensive_results['test_suite_info']['tests_passed'] += 1
                logger.info(f"Test {test_name} PASSED")
                
            except Exception as e:
                comprehensive_results['test_results'][test_name] = {
                    'status': 'failed',
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
                comprehensive_results['test_suite_info']['tests_failed'] += 1
                logger.error(f"Test {test_name} FAILED: {e}")
        
        # Finalize results
        end_time = time.time()
        comprehensive_results['test_suite_info']['end_time'] = end_time
        comprehensive_results['test_suite_info']['duration'] = end_time - start_time
        
        logger.info(f"Comprehensive test suite completed in {comprehensive_results['test_suite_info']['duration']:.2f} seconds")
        logger.info(f"Tests passed: {comprehensive_results['test_suite_info']['tests_passed']}/{comprehensive_results['test_suite_info']['tests_run']}")
        
        return comprehensive_results


# Convenience function to run tests
async def run_resilience_tests() -> Dict[str, Any]:
    """Run the complete resilience test suite and return results."""
    test_suite = ResilienceTestSuite()
    return await test_suite.run_comprehensive_test_suite()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the test suite
    async def main():
        logger.info("Starting resilience patterns test suite")
        results = await run_resilience_tests()
        
        # Print summary
        print("\n" + "="*80)
        print("RESILIENCE TEST SUITE SUMMARY")
        print("="*80)
        print(f"Total tests: {results['test_suite_info']['tests_run']}")
        print(f"Passed: {results['test_suite_info']['tests_passed']}")
        print(f"Failed: {results['test_suite_info']['tests_failed']}")
        print(f"Duration: {results['test_suite_info']['duration']:.2f} seconds")
        print("="*80)
        
        # Print detailed results
        for test_name, test_result in results['test_results'].items():
            status = test_result['status'].upper()
            print(f"\n{test_name}: {status}")
            
            if status == 'FAILED':
                print(f"  Error: {test_result['error']}")
            else:
                # Print key metrics for passed tests
                if 'results' in test_result and isinstance(test_result['results'], dict):
                    for key, value in test_result['results'].items():
                        if isinstance(value, (int, float, str, bool)):
                            print(f"  {key}: {value}")
    
    # Run the main function
    asyncio.run(main())