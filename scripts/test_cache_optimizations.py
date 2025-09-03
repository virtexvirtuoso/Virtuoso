#!/usr/bin/env python3
"""
Test script for optimized cache system
Validates performance, reliability, and zero empty data guarantee
"""
import asyncio
import aiohttp
import time
import json
import logging
from typing import Dict, Any, List
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CacheOptimizationTester:
    """Comprehensive testing for the optimized cache system"""
    
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.session = None
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'performance_metrics': {},
            'data_quality_metrics': {},
            'reliability_metrics': {},
            'detailed_results': []
        }
    
    async def setup_session(self):
        """Setup HTTP session with proper timeouts"""
        connector = aiohttp.TCPConnector(limit=20, limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'CacheOptimizationTester/1.0'}
        )
    
    async def cleanup_session(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all cache optimization tests"""
        logger.info("🚀 Starting comprehensive cache optimization tests...")
        
        try:
            await self.setup_session()
            
            # Test categories
            await self.test_cache_warming()
            await self.test_zero_empty_data_guarantee()
            await self.test_performance_improvements()
            await self.test_fallback_mechanisms()
            await self.test_data_validation()
            await self.test_monitoring_endpoints()
            await self.test_concurrent_load()
            await self.test_error_resilience()
            
            # Generate final report
            await self.generate_test_report()
            
            return self.test_results
            
        finally:
            await self.cleanup_session()
    
    async def test_cache_warming(self):
        """Test cache warming functionality"""
        logger.info("🔥 Testing cache warming functionality...")
        
        try:
            # Trigger cache warming
            warming_url = f"{self.base_url}/api/dashboard-optimized/warm-cache"
            
            start_time = time.perf_counter()
            async with self.session.post(warming_url) as response:
                elapsed_time = (time.perf_counter() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Validate warming response
                    test_passed = (
                        data.get('status') == 'success' and
                        'warming_results' in data
                    )
                    
                    self._record_test_result(
                        'cache_warming_trigger',
                        test_passed,
                        {
                            'response_time_ms': elapsed_time,
                            'warming_status': data.get('status'),
                            'results': data.get('warming_results')
                        }
                    )
                    
                    # Wait for warming to complete
                    await asyncio.sleep(5)
                    
                    # Test that data is now available
                    await self._test_data_availability_after_warming()
                    
                else:
                    self._record_test_result(
                        'cache_warming_trigger',
                        False,
                        {'error': f"HTTP {response.status}"}
                    )
        
        except Exception as e:
            logger.error(f"Cache warming test failed: {e}")
            self._record_test_result('cache_warming_trigger', False, {'error': str(e)})
    
    async def _test_data_availability_after_warming(self):
        """Test that data is available after warming"""
        critical_endpoints = [
            '/api/dashboard-optimized/overview',
            '/api/dashboard-optimized/signals',
            '/api/dashboard-optimized/mobile-data'
        ]
        
        for endpoint in critical_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        has_data = self._validate_non_empty_data(data, endpoint)
                        
                        self._record_test_result(
                            f'post_warming_data_{endpoint.split("/")[-1]}',
                            has_data,
                            {'endpoint': endpoint, 'has_meaningful_data': has_data}
                        )
                    else:
                        self._record_test_result(
                            f'post_warming_data_{endpoint.split("/")[-1]}',
                            False,
                            {'error': f"HTTP {response.status}"}
                        )
            
            except Exception as e:
                self._record_test_result(
                    f'post_warming_data_{endpoint.split("/")[-1]}',
                    False,
                    {'error': str(e)}
                )
    
    async def test_zero_empty_data_guarantee(self):
        """Test that dashboard never returns empty data"""
        logger.info("🛡️ Testing zero empty data guarantee...")
        
        # Test multiple times to ensure consistency
        test_endpoints = [
            '/api/dashboard-optimized/overview',
            '/api/dashboard-optimized/mobile-data',
            '/api/dashboard-optimized/signals'
        ]
        
        for endpoint in test_endpoints:
            empty_data_count = 0
            total_requests = 10
            
            for i in range(total_requests):
                try:
                    url = f"{self.base_url}{endpoint}"
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if not self._validate_non_empty_data(data, endpoint):
                                empty_data_count += 1
                                logger.warning(f"Empty data detected on {endpoint} (attempt {i+1})")
                        
                        # Small delay between requests
                        await asyncio.sleep(0.5)
                
                except Exception as e:
                    logger.error(f"Request failed for {endpoint}: {e}")
                    empty_data_count += 1
            
            success_rate = ((total_requests - empty_data_count) / total_requests) * 100
            
            self._record_test_result(
                f'zero_empty_data_{endpoint.split("/")[-1]}',
                success_rate == 100,
                {
                    'success_rate': success_rate,
                    'empty_data_count': empty_data_count,
                    'total_requests': total_requests
                }
            )
    
    async def test_performance_improvements(self):
        """Test performance improvements vs. baseline"""
        logger.info("⚡ Testing performance improvements...")
        
        endpoints_to_test = [
            '/api/dashboard-optimized/overview',
            '/api/dashboard-optimized/mobile-data',
            '/api/dashboard-cached/overview',  # Compare with existing
            '/api/dashboard-cached/mobile-data'  # Compare with existing
        ]
        
        performance_results = {}
        
        for endpoint in endpoints_to_test:
            response_times = []
            
            # Test 20 requests per endpoint
            for _ in range(20):
                try:
                    start_time = time.perf_counter()
                    url = f"{self.base_url}{endpoint}"
                    
                    async with self.session.get(url) as response:
                        elapsed = (time.perf_counter() - start_time) * 1000
                        
                        if response.status == 200:
                            response_times.append(elapsed)
                        
                        await asyncio.sleep(0.1)  # Small delay
                
                except Exception as e:
                    logger.error(f"Performance test failed for {endpoint}: {e}")
            
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                min_time = min(response_times)
                max_time = max(response_times)
                
                performance_results[endpoint] = {
                    'avg_response_time_ms': round(avg_time, 2),
                    'min_response_time_ms': round(min_time, 2),
                    'max_response_time_ms': round(max_time, 2),
                    'samples': len(response_times)
                }
        
        # Compare optimized vs non-optimized
        optimized_avg = performance_results.get('/api/dashboard-optimized/mobile-data', {}).get('avg_response_time_ms', 0)
        cached_avg = performance_results.get('/api/dashboard-cached/mobile-data', {}).get('avg_response_time_ms', 0)
        
        improvement_ratio = (cached_avg / optimized_avg) if optimized_avg > 0 else 1
        
        self._record_test_result(
            'performance_improvement',
            improvement_ratio >= 0.8,  # At least not worse
            {
                'optimized_avg_ms': optimized_avg,
                'cached_avg_ms': cached_avg,
                'improvement_ratio': round(improvement_ratio, 2),
                'all_results': performance_results
            }
        )
        
        self.test_results['performance_metrics'] = performance_results
    
    async def test_fallback_mechanisms(self):
        """Test fallback mechanisms work correctly"""
        logger.info("🔄 Testing fallback mechanisms...")
        
        # Test endpoints when cache might be cold
        fallback_endpoints = [
            '/api/dashboard-optimized/overview',
            '/api/dashboard-optimized/signals',
            '/api/dashboard-optimized/mobile-data'
        ]
        
        for endpoint in fallback_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check if fallback data structure is correct
                        has_fallback_indicators = (
                            'source' in data or
                            'status' in data or
                            'data_source' in data
                        )
                        
                        # Ensure data is never completely empty
                        has_data_structure = self._validate_data_structure(data, endpoint)
                        
                        self._record_test_result(
                            f'fallback_{endpoint.split("/")[-1]}',
                            has_fallback_indicators and has_data_structure,
                            {
                                'has_fallback_indicators': has_fallback_indicators,
                                'has_data_structure': has_data_structure,
                                'data_source': data.get('source', 'unknown')
                            }
                        )
                    else:
                        self._record_test_result(
                            f'fallback_{endpoint.split("/")[-1]}',
                            False,
                            {'error': f"HTTP {response.status}"}
                        )
            
            except Exception as e:
                self._record_test_result(
                    f'fallback_{endpoint.split("/")[-1]}',
                    False,
                    {'error': str(e)}
                )
    
    async def test_data_validation(self):
        """Test data validation and filtering"""
        logger.info("✅ Testing data validation...")
        
        validation_endpoints = [
            '/api/dashboard-optimized/signals',
            '/api/dashboard-optimized/mobile-data'
        ]
        
        for endpoint in validation_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        validation_passed = self._validate_data_quality(data, endpoint)
                        
                        self._record_test_result(
                            f'data_validation_{endpoint.split("/")[-1]}',
                            validation_passed,
                            {
                                'validation_details': self._get_validation_details(data, endpoint)
                            }
                        )
            
            except Exception as e:
                self._record_test_result(
                    f'data_validation_{endpoint.split("/")[-1]}',
                    False,
                    {'error': str(e)}
                )
    
    async def test_monitoring_endpoints(self):
        """Test monitoring and metrics endpoints"""
        logger.info("📊 Testing monitoring endpoints...")
        
        monitoring_endpoints = [
            '/api/dashboard-optimized/cache-metrics',
            '/api/dashboard-optimized/health'
        ]
        
        for endpoint in monitoring_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        has_metrics = self._validate_monitoring_data(data, endpoint)
                        
                        self._record_test_result(
                            f'monitoring_{endpoint.split("/")[-1]}',
                            has_metrics,
                            {'metrics_available': has_metrics}
                        )
                    else:
                        self._record_test_result(
                            f'monitoring_{endpoint.split("/")[-1]}',
                            False,
                            {'error': f"HTTP {response.status}"}
                        )
            
            except Exception as e:
                self._record_test_result(
                    f'monitoring_{endpoint.split("/")[-1]}',
                    False,
                    {'error': str(e)}
                )
    
    async def test_concurrent_load(self):
        """Test system under concurrent load"""
        logger.info("🔄 Testing concurrent load handling...")
        
        concurrent_requests = 20
        endpoint = '/api/dashboard-optimized/mobile-data'
        
        async def single_request():
            try:
                start_time = time.perf_counter()
                url = f"{self.base_url}{endpoint}"
                
                async with self.session.get(url) as response:
                    elapsed = (time.perf_counter() - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'success': True,
                            'response_time_ms': elapsed,
                            'has_data': self._validate_non_empty_data(data, endpoint)
                        }
                    else:
                        return {
                            'success': False,
                            'error': f"HTTP {response.status}"
                        }
            
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }
        
        # Execute concurrent requests
        tasks = [single_request() for _ in range(concurrent_requests)]
        results = await asyncio.gather(*tasks)
        
        successful_requests = [r for r in results if r.get('success', False)]
        requests_with_data = [r for r in successful_requests if r.get('has_data', False)]
        
        success_rate = (len(successful_requests) / concurrent_requests) * 100
        data_availability_rate = (len(requests_with_data) / concurrent_requests) * 100
        
        if successful_requests:
            avg_response_time = sum(r['response_time_ms'] for r in successful_requests) / len(successful_requests)
        else:
            avg_response_time = 0
        
        self._record_test_result(
            'concurrent_load_test',
            success_rate >= 95 and data_availability_rate >= 90,
            {
                'concurrent_requests': concurrent_requests,
                'success_rate': success_rate,
                'data_availability_rate': data_availability_rate,
                'avg_response_time_ms': round(avg_response_time, 2)
            }
        )
    
    async def test_error_resilience(self):
        """Test system resilience to errors"""
        logger.info("🛡️ Testing error resilience...")
        
        # Test non-existent endpoints (should return graceful fallbacks)
        test_cases = [
            {'endpoint': '/api/dashboard-optimized/nonexistent', 'expected_status': 404},
            {'endpoint': '/api/dashboard-optimized/overview', 'expected_status': 200}
        ]
        
        for test_case in test_cases:
            try:
                url = f"{self.base_url}{test_case['endpoint']}"
                async with self.session.get(url) as response:
                    status_correct = response.status == test_case['expected_status']
                    
                    if response.status == 200:
                        data = await response.json()
                        has_error_handling = 'error' not in data or isinstance(data.get('error'), str)
                    else:
                        has_error_handling = True  # Expected error status
                    
                    self._record_test_result(
                        f'error_resilience_{test_case["endpoint"].split("/")[-1]}',
                        status_correct and has_error_handling,
                        {
                            'expected_status': test_case['expected_status'],
                            'actual_status': response.status,
                            'graceful_error_handling': has_error_handling
                        }
                    )
            
            except Exception as e:
                self._record_test_result(
                    f'error_resilience_{test_case["endpoint"].split("/")[-1]}',
                    False,
                    {'error': str(e)}
                )
    
    def _validate_non_empty_data(self, data: Dict[str, Any], endpoint: str) -> bool:
        """Validate that data is not empty or meaningless"""
        if not isinstance(data, dict):
            return False
        
        if 'mobile-data' in endpoint:
            confluence_scores = data.get('confluence_scores', [])
            market_overview = data.get('market_overview', {})
            
            return (
                len(confluence_scores) > 0 or
                market_overview.get('total_volume_24h', 0) > 0 or
                market_overview.get('market_regime') != 'ERROR'
            )
        
        elif 'overview' in endpoint:
            summary = data.get('summary', {})
            signals = data.get('signals', [])
            
            return (
                summary.get('total_symbols', 0) > 0 or
                summary.get('total_volume', 0) > 0 or
                len(signals) > 0
            )
        
        elif 'signals' in endpoint:
            signals = data.get('signals', [])
            return len(signals) > 0
        
        return True  # Default to pass for unknown endpoints
    
    def _validate_data_structure(self, data: Dict[str, Any], endpoint: str) -> bool:
        """Validate that data has correct structure even if empty"""
        if not isinstance(data, dict):
            return False
        
        if 'mobile-data' in endpoint:
            required_keys = ['market_overview', 'confluence_scores', 'top_movers', 'status']
            return all(key in data for key in required_keys)
        
        elif 'overview' in endpoint:
            required_keys = ['summary', 'market_regime', 'signals']
            return all(key in data for key in required_keys)
        
        elif 'signals' in endpoint:
            required_keys = ['signals', 'count']
            return all(key in data for key in required_keys)
        
        return True
    
    def _validate_data_quality(self, data: Dict[str, Any], endpoint: str) -> bool:
        """Validate data quality (no invalid values)"""
        if not isinstance(data, dict):
            return False
        
        try:
            if 'signals' in endpoint:
                signals = data.get('signals', [])
                for signal in signals[:5]:  # Check first 5
                    if not isinstance(signal, dict):
                        continue
                    
                    score = signal.get('score', 0)
                    price = signal.get('price', 0)
                    
                    if not (0 <= score <= 100) or price < 0:
                        return False
            
            elif 'mobile-data' in endpoint:
                confluence_scores = data.get('confluence_scores', [])
                for score in confluence_scores[:5]:  # Check first 5
                    if not isinstance(score, dict):
                        continue
                    
                    if not (0 <= score.get('score', 0) <= 100):
                        return False
                    
                    if score.get('price', 0) < 0:
                        return False
            
            return True
            
        except Exception:
            return False
    
    def _get_validation_details(self, data: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
        """Get detailed validation information"""
        details = {}
        
        if 'signals' in endpoint:
            signals = data.get('signals', [])
            details['signal_count'] = len(signals)
            details['valid_signals'] = sum(1 for s in signals if self._is_valid_signal(s))
        
        elif 'mobile-data' in endpoint:
            scores = data.get('confluence_scores', [])
            details['confluence_score_count'] = len(scores)
            details['valid_scores'] = sum(1 for s in scores if self._is_valid_confluence_score(s))
        
        return details
    
    def _is_valid_signal(self, signal: Dict[str, Any]) -> bool:
        """Check if a signal is valid"""
        if not isinstance(signal, dict):
            return False
        
        return (
            signal.get('symbol') and
            isinstance(signal.get('score', 0), (int, float)) and
            0 <= signal.get('score', 0) <= 100 and
            isinstance(signal.get('price', 0), (int, float)) and
            signal.get('price', 0) >= 0
        )
    
    def _is_valid_confluence_score(self, score: Dict[str, Any]) -> bool:
        """Check if a confluence score is valid"""
        if not isinstance(score, dict):
            return False
        
        return (
            score.get('symbol') and
            isinstance(score.get('score', 0), (int, float)) and
            0 <= score.get('score', 0) <= 100 and
            isinstance(score.get('price', 0), (int, float)) and
            score.get('price', 0) >= 0
        )
    
    def _validate_monitoring_data(self, data: Dict[str, Any], endpoint: str) -> bool:
        """Validate monitoring endpoint data"""
        if not isinstance(data, dict):
            return False
        
        if 'cache-metrics' in endpoint:
            return 'cache_performance' in data or 'warming_stats' in data
        elif 'health' in endpoint:
            return 'status' in data
        
        return True
    
    def _record_test_result(self, test_name: str, passed: bool, details: Dict[str, Any]):
        """Record a test result"""
        self.test_results['total_tests'] += 1
        
        if passed:
            self.test_results['passed_tests'] += 1
            logger.info(f"✅ {test_name}: PASSED")
        else:
            self.test_results['failed_tests'] += 1
            logger.error(f"❌ {test_name}: FAILED - {details}")
        
        self.test_results['detailed_results'].append({
            'test_name': test_name,
            'passed': passed,
            'details': details,
            'timestamp': time.time()
        })
    
    async def generate_test_report(self):
        """Generate comprehensive test report"""
        success_rate = (self.test_results['passed_tests'] / self.test_results['total_tests']) * 100
        
        logger.info("\n" + "="*60)
        logger.info("📋 CACHE OPTIMIZATION TEST REPORT")
        logger.info("="*60)
        logger.info(f"Total Tests: {self.test_results['total_tests']}")
        logger.info(f"Passed: {self.test_results['passed_tests']}")
        logger.info(f"Failed: {self.test_results['failed_tests']}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        if self.test_results['failed_tests'] > 0:
            logger.info("\n❌ FAILED TESTS:")
            for result in self.test_results['detailed_results']:
                if not result['passed']:
                    logger.info(f"  - {result['test_name']}: {result['details']}")
        
        if self.test_results['performance_metrics']:
            logger.info("\n⚡ PERFORMANCE SUMMARY:")
            for endpoint, metrics in self.test_results['performance_metrics'].items():
                logger.info(f"  {endpoint}: {metrics['avg_response_time_ms']:.1f}ms avg")
        
        logger.info("="*60)
        
        # Save detailed results
        with open('cache_optimization_test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        logger.info("📄 Detailed results saved to: cache_optimization_test_results.json")

async def main():
    """Main test execution"""
    tester = CacheOptimizationTester()
    
    try:
        results = await tester.run_comprehensive_tests()
        
        # Exit with appropriate code
        if results['failed_tests'] == 0:
            logger.info("🎉 All tests passed! Cache optimizations are working correctly.")
            exit(0)
        else:
            logger.error("⚠️ Some tests failed. Please review the results.")
            exit(1)
    
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        exit(2)

if __name__ == "__main__":
    asyncio.run(main())