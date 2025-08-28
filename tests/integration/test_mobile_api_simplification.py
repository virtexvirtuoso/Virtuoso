#!/usr/bin/env python3
"""
Comprehensive Test Suite for Mobile API Simplification
Tests unified mobile endpoints, fallback removal, and response time improvements.
"""

import asyncio
import aiohttp
import time
import logging
import sys
import os
import json
from typing import Dict, Any, List, Optional
import traceback
from dataclasses import dataclass

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class EndpointTest:
    """Test configuration for an endpoint."""
    path: str
    method: str = "GET"
    expected_fields: List[str] = None
    max_response_time: float = 2.0
    description: str = ""

class MobileAPITester:
    """Mobile API simplification test suite."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.session = None
        
        # Define unified mobile endpoints to test
        self.unified_endpoints = [
            EndpointTest(
                path="/api/mobile-unified/dashboard",
                expected_fields=["market_overview", "confluence_scores", "top_movers", "timestamp"],
                max_response_time=1.5,
                description="Unified mobile dashboard data"
            ),
            EndpointTest(
                path="/api/mobile-unified/confluence",
                expected_fields=["confluence_scores", "timestamp", "status"],
                max_response_time=1.0,
                description="Mobile confluence scores"
            ),
            EndpointTest(
                path="/api/mobile-unified/market-overview",
                expected_fields=["active_symbols", "total_volume", "market_regime"],
                max_response_time=0.8,
                description="Mobile market overview"
            ),
            EndpointTest(
                path="/api/mobile-unified/top-movers",
                expected_fields=["gainers", "losers", "timestamp"],
                max_response_time=0.8,
                description="Mobile top movers"
            ),
        ]
        
        # Legacy endpoints that should still work (for compatibility)
        self.legacy_endpoints = [
            EndpointTest(
                path="/api/dashboard/market-overview",
                expected_fields=["active_symbols", "market_regime"],
                description="Legacy market overview"
            ),
            EndpointTest(
                path="/api/market/movers",
                expected_fields=["gainers", "losers"],
                description="Legacy market movers"
            ),
        ]
    
    async def initialize(self):
        """Initialize HTTP session for testing."""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info("✅ HTTP session initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize HTTP session: {e}")
            return False
    
    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Log a test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
        if details:
            logger.info(f"   Details: {details}")
        
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details,
            'timestamp': time.time()
        })
    
    async def test_endpoint(self, endpoint: EndpointTest) -> Dict[str, Any]:
        """Test a single endpoint."""
        url = f"{self.base_url}{endpoint.path}"
        
        try:
            start_time = time.time()
            async with self.session.request(endpoint.method, url) as response:
                response_time = time.time() - start_time
                
                # Check status code
                status_ok = response.status == 200
                
                # Get response data
                try:
                    data = await response.json()
                except Exception as e:
                    data = await response.text()
                
                # Check response time
                response_time_ok = response_time <= endpoint.max_response_time
                
                # Check expected fields
                fields_ok = True
                missing_fields = []
                if endpoint.expected_fields and isinstance(data, dict):
                    for field in endpoint.expected_fields:
                        if field not in data:
                            fields_ok = False
                            missing_fields.append(field)
                
                return {
                    'success': status_ok and response_time_ok and fields_ok,
                    'status_code': response.status,
                    'response_time': response_time,
                    'data': data,
                    'missing_fields': missing_fields,
                    'data_size': len(str(data)) if data else 0
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response_time': float('inf'),
                'status_code': 0
            }
    
    async def test_unified_mobile_endpoints(self):
        """Test all unified mobile endpoints."""
        test_name = "Unified Mobile Endpoints"
        
        try:
            total_endpoints = len(self.unified_endpoints)
            successful_endpoints = 0
            total_response_time = 0
            
            for endpoint in self.unified_endpoints:
                logger.info(f"  Testing {endpoint.path}...")
                result = await self.test_endpoint(endpoint)
                
                success = result.get('success', False)
                response_time = result.get('response_time', float('inf'))
                
                if success:
                    successful_endpoints += 1
                
                total_response_time += response_time
                
                # Log individual endpoint result
                status = "✅" if success else "❌"
                details = f"Status: {result.get('status_code', 'N/A')}, Time: {response_time:.3f}s"
                
                if result.get('missing_fields'):
                    details += f", Missing: {result['missing_fields']}"
                if result.get('error'):
                    details += f", Error: {result['error']}"
                
                self.log_test_result(f"{test_name} - {endpoint.description}", success, details)
            
            # Overall success rate
            success_rate = (successful_endpoints / total_endpoints) * 100
            avg_response_time = total_response_time / total_endpoints
            
            overall_success = success_rate >= 80  # 80% success rate threshold
            
            self.log_test_result(f"{test_name} - Overall Performance", overall_success, 
                               f"Success: {successful_endpoints}/{total_endpoints} ({success_rate:.1f}%), Avg time: {avg_response_time:.3f}s")
            
            return overall_success
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_fallback_removal(self):
        """Test that complex fallback chains have been removed."""
        test_name = "Fallback Chain Removal"
        
        try:
            # Test endpoints for consistency (no fallback behavior)
            test_endpoint = self.unified_endpoints[0]  # Use dashboard endpoint
            
            # Make multiple requests to same endpoint
            response_times = []
            response_data = []
            
            for i in range(3):
                result = await self.test_endpoint(test_endpoint)
                if result.get('success'):
                    response_times.append(result['response_time'])
                    response_data.append(result.get('data'))
                await asyncio.sleep(0.1)  # Small delay between requests
            
            # Check response time consistency (no long fallback delays)
            time_consistency = True
            if len(response_times) >= 2:
                max_time = max(response_times)
                min_time = min(response_times)
                # Response times shouldn't vary too much if fallbacks are removed
                time_consistency = (max_time - min_time) < 1.0
            
            # Check data consistency (no fallback data switching)
            data_consistency = True
            if len(response_data) >= 2:
                # Basic structure should be consistent
                first_keys = set(response_data[0].keys()) if isinstance(response_data[0], dict) else set()
                for data in response_data[1:]:
                    if isinstance(data, dict):
                        current_keys = set(data.keys())
                        # Allow some variation but core structure should be similar
                        key_similarity = len(first_keys & current_keys) / len(first_keys | current_keys)
                        if key_similarity < 0.8:
                            data_consistency = False
                            break
            
            self.log_test_result(f"{test_name} - Response Time Consistency", time_consistency, 
                               f"Time variation: {max(response_times) - min(response_times):.3f}s")
            
            self.log_test_result(f"{test_name} - Data Structure Consistency", data_consistency, 
                               f"Consistent structure across {len(response_data)} requests")
            
            return time_consistency and data_consistency
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_response_time_improvements(self):
        """Test that response times have improved."""
        test_name = "Response Time Improvements"
        
        try:
            # Test multiple endpoints and check response times
            fast_responses = 0
            slow_responses = 0
            total_time = 0
            
            # Test each unified endpoint multiple times
            for endpoint in self.unified_endpoints:
                for _ in range(2):  # Test each endpoint twice
                    result = await self.test_endpoint(endpoint)
                    response_time = result.get('response_time', float('inf'))
                    total_time += response_time
                    
                    if response_time <= endpoint.max_response_time:
                        fast_responses += 1
                    else:
                        slow_responses += 1
            
            total_requests = fast_responses + slow_responses
            avg_response_time = total_time / total_requests if total_requests > 0 else float('inf')
            
            # Performance criteria
            fast_enough = (fast_responses / total_requests) >= 0.8 if total_requests > 0 else False
            avg_acceptable = avg_response_time <= 1.5  # Average should be under 1.5s
            
            self.log_test_result(f"{test_name} - Response Speed", fast_enough, 
                               f"Fast responses: {fast_responses}/{total_requests}")
            
            self.log_test_result(f"{test_name} - Average Response Time", avg_acceptable, 
                               f"Average: {avg_response_time:.3f}s")
            
            return fast_enough and avg_acceptable
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_data_completeness(self):
        """Test that mobile endpoints provide all required data."""
        test_name = "Data Completeness"
        
        try:
            complete_endpoints = 0
            
            for endpoint in self.unified_endpoints:
                result = await self.test_endpoint(endpoint)
                
                if result.get('success') and not result.get('missing_fields'):
                    complete_endpoints += 1
                
                # Additional checks for data quality
                data = result.get('data')
                if isinstance(data, dict):
                    # Check for empty or null values in critical fields
                    has_meaningful_data = False
                    
                    if 'confluence_scores' in data and data['confluence_scores']:
                        has_meaningful_data = True
                    elif 'market_overview' in data and data['market_overview']:
                        has_meaningful_data = True
                    elif 'active_symbols' in data and data['active_symbols'] > 0:
                        has_meaningful_data = True
                    elif 'gainers' in data or 'losers' in data:
                        has_meaningful_data = True
                    
                    if has_meaningful_data:
                        self.log_test_result(f"{test_name} - {endpoint.description} Data Quality", True, 
                                           "Contains meaningful data")
                    else:
                        self.log_test_result(f"{test_name} - {endpoint.description} Data Quality", False, 
                                           "Data appears empty or incomplete")
            
            completeness_rate = (complete_endpoints / len(self.unified_endpoints)) * 100
            overall_complete = completeness_rate >= 75  # 75% completeness threshold
            
            self.log_test_result(f"{test_name} - Overall Completeness", overall_complete, 
                               f"Complete endpoints: {complete_endpoints}/{len(self.unified_endpoints)} ({completeness_rate:.1f}%)")
            
            return overall_complete
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_backward_compatibility(self):
        """Test that legacy endpoints still work for backward compatibility."""
        test_name = "Backward Compatibility"
        
        try:
            working_legacy = 0
            
            for endpoint in self.legacy_endpoints:
                result = await self.test_endpoint(endpoint)
                
                success = result.get('success', False)
                if success or result.get('status_code') == 200:  # Allow some field variations
                    working_legacy += 1
                
                self.log_test_result(f"{test_name} - {endpoint.description}", success, 
                                   f"Status: {result.get('status_code', 'N/A')}, Time: {result.get('response_time', 0):.3f}s")
            
            compatibility_rate = (working_legacy / len(self.legacy_endpoints)) * 100 if self.legacy_endpoints else 100
            overall_compatible = compatibility_rate >= 70  # Allow some legacy endpoints to fail
            
            self.log_test_result(f"{test_name} - Overall Compatibility", overall_compatible, 
                               f"Working legacy endpoints: {working_legacy}/{len(self.legacy_endpoints)} ({compatibility_rate:.1f}%)")
            
            return overall_compatible
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_mobile_specific_features(self):
        """Test features specific to mobile optimization."""
        test_name = "Mobile-Specific Features"
        
        try:
            mobile_optimized = 0
            total_features = 0
            
            # Test mobile dashboard endpoint specifically
            dashboard_endpoint = next((e for e in self.unified_endpoints if 'dashboard' in e.path), None)
            
            if dashboard_endpoint:
                result = await self.test_endpoint(dashboard_endpoint)
                data = result.get('data', {})
                
                # Test 1: Data is compact and mobile-friendly
                data_size = result.get('data_size', 0)
                compact_data = data_size < 50000  # Less than 50KB
                total_features += 1
                if compact_data:
                    mobile_optimized += 1
                
                self.log_test_result(f"{test_name} - Compact Data", compact_data, 
                                   f"Response size: {data_size} bytes")
                
                # Test 2: Essential fields are present
                if isinstance(data, dict):
                    essential_fields = ['market_overview', 'confluence_scores', 'timestamp']
                    has_essentials = all(field in data for field in essential_fields)
                    total_features += 1
                    if has_essentials:
                        mobile_optimized += 1
                    
                    self.log_test_result(f"{test_name} - Essential Fields", has_essentials, 
                                       f"Has essential mobile fields")
                
                # Test 3: Fast response time
                response_time = result.get('response_time', float('inf'))
                fast_response = response_time <= 1.0  # Under 1 second for mobile
                total_features += 1
                if fast_response:
                    mobile_optimized += 1
                
                self.log_test_result(f"{test_name} - Fast Response", fast_response, 
                                   f"Response time: {response_time:.3f}s")
            
            optimization_rate = (mobile_optimized / total_features) * 100 if total_features > 0 else 0
            well_optimized = optimization_rate >= 80
            
            self.log_test_result(f"{test_name} - Overall Optimization", well_optimized, 
                               f"Optimized features: {mobile_optimized}/{total_features} ({optimization_rate:.1f}%)")
            
            return well_optimized
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.session:
            await self.session.close()
            logger.info("🧹 HTTP session closed")
    
    async def run_all_tests(self):
        """Run all mobile API tests."""
        logger.info("🧪 Starting Mobile API Simplification Tests")
        logger.info("=" * 55)
        
        # Initialize
        if not await self.initialize():
            logger.error("❌ Failed to initialize mobile API tester")
            return False
        
        # Check if server is running
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status != 200:
                    logger.warning("⚠️ Server may not be running or accessible")
        except Exception as e:
            logger.warning(f"⚠️ Cannot reach server at {self.base_url}: {e}")
            logger.info("💡 Make sure the server is running: python -m src.main")
        
        # Run all tests
        tests = [
            self.test_unified_mobile_endpoints,
            self.test_fallback_removal,
            self.test_response_time_improvements,
            self.test_data_completeness,
            self.test_backward_compatibility,
            self.test_mobile_specific_features,
        ]
        
        total_tests = 0
        passed_tests = 0
        
        for test_func in tests:
            try:
                logger.info(f"\n🔬 Running {test_func.__name__}...")
                result = await test_func()
                if result:
                    passed_tests += 1
                total_tests += 1
            except Exception as e:
                logger.error(f"❌ Test {test_func.__name__} failed with exception: {e}")
                logger.error(traceback.format_exc())
                total_tests += 1
        
        # Cleanup
        await self.cleanup()
        
        # Summary
        logger.info("\n" + "=" * 55)
        logger.info(f"📊 MOBILE API SIMPLIFICATION TEST SUMMARY")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {total_tests - passed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Detailed results
        logger.info("\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result['passed'] else "❌"
            logger.info(f"{status} {result['test']}")
            if result['details']:
                logger.info(f"   {result['details']}")
        
        return passed_tests == total_tests


async def main():
    """Main test execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Mobile API Simplification')
    parser.add_argument('--base-url', default='http://localhost:8000', 
                       help='Base URL for the API server')
    args = parser.parse_args()
    
    tester = MobileAPITester(base_url=args.base_url)
    success = await tester.run_all_tests()
    
    if success:
        logger.info("🎉 ALL MOBILE API TESTS PASSED!")
        sys.exit(0)
    else:
        logger.error("💥 SOME MOBILE API TESTS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())