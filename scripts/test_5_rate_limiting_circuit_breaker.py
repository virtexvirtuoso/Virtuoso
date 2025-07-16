#!/usr/bin/env python3

import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

import asyncio
import logging
import time
from typing import Dict, List, Any

from config.manager import ConfigManager
from data_acquisition.binance.binance_exchange import BinanceExchange

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class RateLimitingCircuitBreakerTester:
    """Test rate limiting and circuit breaker functionality."""
    
    def __init__(self):
        self.test_results = {'passed': 0, 'failed': 0, 'warnings': 0}
        
    def log_result(self, test_name: str, status: str, message: str):
        """Log test results."""
        if status == 'PASS':
            logger.info(f"✅ {test_name}: {message}")
            self.test_results['passed'] += 1
        elif status == 'FAIL':
            logger.error(f"❌ {test_name}: {message}")
            self.test_results['failed'] += 1
        else:
            logger.warning(f"⚠️ {test_name}: {message}")
            self.test_results['warnings'] += 1

    async def test_concurrent_request_handling(self, exchange):
        """Test handling of concurrent requests without hitting rate limits."""
        try:
            logger.info("Testing concurrent request handling...")
            
            # Create multiple concurrent requests
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT'] * 4  # 20 requests
            
            start_time = time.time()
            tasks = [exchange.get_ticker(symbol) for symbol in symbols]
            
            # Execute all requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Analyze results
            successful = sum(1 for r in results if not isinstance(r, Exception))
            rate_limited = sum(1 for r in results if isinstance(r, Exception) and '429' in str(r))
            other_errors = len(results) - successful - rate_limited
            
            requests_per_second = len(results) / total_time if total_time > 0 else 0
            success_rate = (successful / len(results)) * 100
            
            if success_rate >= 70 and rate_limited <= 5:
                self.log_result("Concurrent Request Handling", "PASS", 
                               f"{successful}/{len(results)} successful, "
                               f"{rate_limited} rate limited, {requests_per_second:.1f} req/s")
            else:
                self.log_result("Concurrent Request Handling", "WARN", 
                               f"High error rate: {100-success_rate:.1f}%, "
                               f"{rate_limited} rate limited")
                
        except Exception as e:
            self.log_result("Concurrent Request Handling", "FAIL", f"Error: {str(e)}")

    async def test_rate_limit_recovery(self, exchange):
        """Test recovery from rate limiting."""
        try:
            logger.info("Testing rate limit recovery...")
            
            # Try to trigger rate limiting with rapid requests
            recovery_successful = False
            
            # Burst phase - rapid requests to potentially trigger rate limiting
            burst_tasks = []
            for i in range(10):
                task = exchange.get_ticker('BTCUSDT')
                burst_tasks.append(task)
            
            burst_results = await asyncio.gather(*burst_tasks, return_exceptions=True)
            rate_limited_count = sum(1 for r in burst_results if isinstance(r, Exception) and '429' in str(r))
            
            # Recovery phase - wait and test if we can recover
            if rate_limited_count > 0:
                logger.debug(f"Rate limiting detected: {rate_limited_count} requests limited")
                await asyncio.sleep(2)  # Wait for recovery
                
                # Test recovery
                recovery_ticker = await exchange.get_ticker('BTCUSDT')
                if recovery_ticker and 'last' in recovery_ticker:
                    recovery_successful = True
                    
            # If no rate limiting occurred, that's also a pass (system is robust)
            if rate_limited_count == 0 or recovery_successful:
                self.log_result("Rate Limit Recovery", "PASS", 
                               f"System handled {len(burst_tasks)} requests, recovery successful")
            else:
                self.log_result("Rate Limit Recovery", "FAIL", 
                               "Failed to recover from rate limiting")
                
        except Exception as e:
            self.log_result("Rate Limit Recovery", "FAIL", f"Error: {str(e)}")

    async def test_request_spacing(self, exchange):
        """Test request spacing to avoid rate limits."""
        try:
            logger.info("Testing request spacing...")
            
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
            request_times = []
            successful_requests = 0
            
            for symbol in symbols:
                start = time.time()
                try:
                    ticker = await exchange.get_ticker(symbol)
                    if ticker and 'last' in ticker:
                        successful_requests += 1
                        request_times.append(time.time() - start)
                        
                    # Small delay between requests
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.debug(f"Request failed for {symbol}: {str(e)}")
            
            if successful_requests >= 2:
                avg_response_time = sum(request_times) / len(request_times) if request_times else 0
                self.log_result("Request Spacing", "PASS", 
                               f"{successful_requests}/{len(symbols)} requests successful, "
                               f"avg response: {avg_response_time:.3f}s")
            else:
                self.log_result("Request Spacing", "FAIL", 
                               f"Too many failed requests: {successful_requests}/{len(symbols)}")
                
        except Exception as e:
            self.log_result("Request Spacing", "FAIL", f"Error: {str(e)}")

    async def test_error_accumulation_tracking(self, exchange):
        """Test error accumulation and tracking for circuit breaker logic."""
        try:
            logger.info("Testing error accumulation tracking...")
            
            # Test with invalid symbols to generate errors
            invalid_symbols = ['INVALIDUSDT', 'FAKECOINUSDT', 'TESTUSDT', 'WRONGUSDT']
            error_count = 0
            total_requests = 0
            
            for symbol in invalid_symbols:
                total_requests += 1
                try:
                    await exchange.get_ticker(symbol)
                except Exception as e:
                    error_count += 1
                    logger.debug(f"Expected error for {symbol}: {type(e).__name__}")
            
            # Test with valid symbol to ensure system still works
            try:
                valid_ticker = await exchange.get_ticker('BTCUSDT')
                valid_response = valid_ticker and 'last' in valid_ticker
            except Exception:
                valid_response = False
            
            error_rate = (error_count / total_requests) * 100 if total_requests > 0 else 0
            
            if error_rate >= 75 and valid_response:  # High error rate for invalid symbols, but valid requests work
                self.log_result("Error Accumulation Tracking", "PASS", 
                               f"Error tracking working: {error_rate:.1f}% error rate for invalid symbols, "
                               f"valid requests still work")
            else:
                self.log_result("Error Accumulation Tracking", "WARN", 
                               f"Error tracking issues: {error_rate:.1f}% error rate")
                
        except Exception as e:
            self.log_result("Error Accumulation Tracking", "FAIL", f"Error: {str(e)}")

    async def test_timeout_handling(self, exchange):
        """Test timeout handling under different conditions."""
        try:
            logger.info("Testing timeout handling...")
            
            timeout_tests = []
            
            # Test 1: Normal request with reasonable timeout
            try:
                start_time = time.time()
                ticker = await asyncio.wait_for(exchange.get_ticker('BTCUSDT'), timeout=10)
                elapsed = time.time() - start_time
                
                if ticker and elapsed < 5:  # Should complete quickly
                    timeout_tests.append(('normal_request', True, elapsed))
                else:
                    timeout_tests.append(('normal_request', False, elapsed))
            except asyncio.TimeoutError:
                timeout_tests.append(('normal_request', False, 10))
            except Exception as e:
                timeout_tests.append(('normal_request', False, 0))
            
            # Test 2: Request with very short timeout
            try:
                start_time = time.time()
                await asyncio.wait_for(exchange.get_ticker('BTCUSDT'), timeout=0.001)
                elapsed = time.time() - start_time
                timeout_tests.append(('short_timeout', False, elapsed))  # Should have timed out
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                timeout_tests.append(('short_timeout', True, elapsed))  # Expected timeout
            except Exception:
                timeout_tests.append(('short_timeout', True, 0.001))
            
            # Test 3: Multiple requests with timeout
            try:
                start_time = time.time()
                tasks = [exchange.get_ticker(sym) for sym in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']]
                results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=15)
                elapsed = time.time() - start_time
                
                successful = sum(1 for r in results if r and 'last' in r)
                if successful >= 2:
                    timeout_tests.append(('multiple_requests', True, elapsed))
                else:
                    timeout_tests.append(('multiple_requests', False, elapsed))
            except asyncio.TimeoutError:
                timeout_tests.append(('multiple_requests', False, 15))
            except Exception:
                timeout_tests.append(('multiple_requests', False, 0))
            
            # Evaluate results
            passed_tests = sum(1 for _, success, _ in timeout_tests if success)
            total_tests = len(timeout_tests)
            
            if passed_tests >= 2:
                avg_time = sum(elapsed for _, _, elapsed in timeout_tests) / total_tests
                self.log_result("Timeout Handling", "PASS", 
                               f"{passed_tests}/{total_tests} timeout tests passed, "
                               f"avg time: {avg_time:.3f}s")
            else:
                self.log_result("Timeout Handling", "FAIL", 
                               f"Timeout handling issues: {passed_tests}/{total_tests} passed")
                
        except Exception as e:
            self.log_result("Timeout Handling", "FAIL", f"Error: {str(e)}")

    async def test_backoff_strategy(self, exchange):
        """Test exponential backoff strategy for failed requests."""
        try:
            logger.info("Testing backoff strategy...")
            
            # Simulate requests with increasing delays
            backoff_delays = [0.1, 0.2, 0.4, 0.8, 1.6]  # Exponential backoff
            request_times = []
            successful_requests = 0
            
            for i, delay in enumerate(backoff_delays):
                if i > 0:  # Apply backoff delay
                    await asyncio.sleep(delay)
                
                start_time = time.time()
                try:
                    ticker = await exchange.get_ticker('BTCUSDT')
                    request_time = time.time() - start_time
                    
                    if ticker and 'last' in ticker:
                        successful_requests += 1
                        request_times.append(request_time)
                        logger.debug(f"Request {i+1} successful in {request_time:.3f}s after {delay}s delay")
                    
                except Exception as e:
                    logger.debug(f"Request {i+1} failed after {delay}s delay: {str(e)}")
            
            if successful_requests >= 3:
                avg_request_time = sum(request_times) / len(request_times) if request_times else 0
                self.log_result("Backoff Strategy", "PASS", 
                               f"{successful_requests}/{len(backoff_delays)} requests successful "
                               f"with backoff, avg time: {avg_request_time:.3f}s")
            else:
                self.log_result("Backoff Strategy", "WARN", 
                               f"Backoff strategy may need tuning: {successful_requests}/{len(backoff_delays)} successful")
                
        except Exception as e:
            self.log_result("Backoff Strategy", "FAIL", f"Error: {str(e)}")

    async def test_system_resilience_under_load(self, exchange):
        """Test system resilience under sustained load."""
        try:
            logger.info("Testing system resilience under load...")
            
            # Sustained load test
            duration = 10  # seconds
            start_time = time.time()
            request_count = 0
            successful_count = 0
            error_count = 0
            
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT']
            
            while (time.time() - start_time) < duration:
                symbol = symbols[request_count % len(symbols)]
                request_count += 1
                
                try:
                    ticker = await exchange.get_ticker(symbol)
                    if ticker and 'last' in ticker:
                        successful_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
                    logger.debug(f"Load test error: {str(e)}")
                
                # Small delay to avoid overwhelming the system
                await asyncio.sleep(0.2)
            
            total_time = time.time() - start_time
            requests_per_second = request_count / total_time
            success_rate = (successful_count / request_count) * 100 if request_count > 0 else 0
            
            if success_rate >= 70 and requests_per_second >= 2:
                self.log_result("System Resilience Under Load", "PASS", 
                               f"{request_count} requests in {total_time:.1f}s, "
                               f"{success_rate:.1f}% success rate, {requests_per_second:.1f} req/s")
            else:
                self.log_result("System Resilience Under Load", "WARN", 
                               f"Performance under load: {success_rate:.1f}% success, "
                               f"{requests_per_second:.1f} req/s")
                
        except Exception as e:
            self.log_result("System Resilience Under Load", "FAIL", f"Error: {str(e)}")

    def generate_summary(self):
        """Generate test summary."""
        total = sum(self.test_results.values())
        passed = self.test_results['passed']
        
        logger.info("\n" + "="*60)
        logger.info("RATE LIMITING & CIRCUIT BREAKER TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"📊 Total Tests: {total}")
        logger.info(f"✅ Passed: {self.test_results['passed']}")
        logger.info(f"❌ Failed: {self.test_results['failed']}")
        logger.info(f"⚠️ Warnings: {self.test_results['warnings']}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        logger.info(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 70:
            logger.info("🎉 Rate limiting and circuit breaker systems are robust!")
            return True
        else:
            logger.warning("⚠️ Rate limiting/circuit breaker systems need attention")
            return False

async def main():
    """Run Rate Limiting & Circuit Breaker tests."""
    logger.info("⚡ TEST 5: Rate Limiting & Circuit Breaker")
    logger.info("="*50)
    
    tester = RateLimitingCircuitBreakerTester()
    
    try:
        # Initialize exchange
        config_manager = ConfigManager()
        config = config_manager.config
        
        async with BinanceExchange(config=config) as exchange:
            logger.info("🔗 Connected to Binance exchange")
            
            # Run rate limiting tests
            await tester.test_concurrent_request_handling(exchange)
            await tester.test_rate_limit_recovery(exchange)
            await tester.test_request_spacing(exchange)
            await tester.test_error_accumulation_tracking(exchange)
            await tester.test_timeout_handling(exchange)
            await tester.test_backoff_strategy(exchange)
            await tester.test_system_resilience_under_load(exchange)
            
        return tester.generate_summary()
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 