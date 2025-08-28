#!/usr/bin/env python3
"""
Comprehensive Test Suite for Frontend Endpoint Changes
Tests unified endpoints, caching, debouncing, and fallback mechanisms.
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
from bs4 import BeautifulSoup
import re

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FrontendEndpointTester:
    """Frontend endpoint changes test suite."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.session = None
        
    async def initialize(self):
        """Initialize HTTP session for testing."""
        try:
            timeout = aiohttp.ClientTimeout(total=15)
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
    
    async def get_dashboard_html(self) -> Optional[str]:
        """Get dashboard HTML for testing."""
        try:
            async with self.session.get(f"{self.base_url}/dashboard") as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"Dashboard returned status {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Failed to get dashboard HTML: {e}")
            return None
    
    async def test_unified_endpoint_usage(self):
        """Test that frontend uses new unified endpoints."""
        test_name = "Unified Endpoint Usage"
        
        try:
            # Get dashboard HTML
            html_content = await self.get_dashboard_html()
            
            if not html_content:
                self.log_test_result(test_name, False, "Could not retrieve dashboard HTML")
                return False
            
            # Parse HTML to check for endpoint URLs
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for JavaScript that makes API calls
            scripts = soup.find_all('script')
            script_content = ' '.join([script.get_text() for script in scripts if script.get_text()])
            
            # Check for unified endpoints
            unified_endpoints_found = 0
            legacy_endpoints_found = 0
            
            unified_patterns = [
                r'/api/mobile-unified/',
                r'/api/unified/',
                r'mobile-unified',
            ]
            
            legacy_patterns = [
                r'/api/dashboard/market-overview',
                r'/api/dashboard/overview',
                r'/api/market/movers',
            ]
            
            # Count unified endpoint usage
            for pattern in unified_patterns:
                matches = re.findall(pattern, script_content, re.IGNORECASE)
                unified_endpoints_found += len(matches)
            
            # Count legacy endpoint usage
            for pattern in legacy_patterns:
                matches = re.findall(pattern, script_content, re.IGNORECASE)
                legacy_endpoints_found += len(matches)
            
            # Check if predominantly using unified endpoints
            predominantly_unified = unified_endpoints_found > legacy_endpoints_found
            
            self.log_test_result(f"{test_name} - Unified Endpoints", predominantly_unified, 
                               f"Unified: {unified_endpoints_found}, Legacy: {legacy_endpoints_found}")
            
            # Also test actual endpoint calls
            endpoint_test = await self.test_actual_endpoint_calls()
            
            return predominantly_unified and endpoint_test
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_actual_endpoint_calls(self):
        """Test that the actual API endpoints work as expected."""
        try:
            # Test unified endpoints
            unified_endpoints = [
                "/api/mobile-unified/dashboard",
                "/api/mobile-unified/market-overview",
                "/api/mobile-unified/confluence"
            ]
            
            working_endpoints = 0
            
            for endpoint in unified_endpoints:
                try:
                    async with self.session.get(f"{self.base_url}{endpoint}") as response:
                        if response.status == 200:
                            data = await response.json()
                            if isinstance(data, dict) and data:
                                working_endpoints += 1
                        else:
                            logger.debug(f"Endpoint {endpoint} returned status {response.status}")
                except Exception as e:
                    logger.debug(f"Endpoint {endpoint} failed: {e}")
            
            return working_endpoints >= len(unified_endpoints) * 0.6  # 60% success rate
            
        except Exception as e:
            logger.error(f"Actual endpoint test failed: {e}")
            return False
    
    async def test_dashboard_data_loading(self):
        """Test that dashboard displays data correctly."""
        test_name = "Dashboard Data Loading"
        
        try:
            # Get dashboard HTML
            html_content = await self.get_dashboard_html()
            
            if not html_content:
                self.log_test_result(test_name, False, "Could not retrieve dashboard HTML")
                return False
            
            # Check for data containers and elements
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for market data containers
            market_containers = soup.find_all(['div', 'section'], {'class': re.compile(r'market|overview|dashboard', re.I)})
            has_market_containers = len(market_containers) > 0
            
            # Look for confluence score containers
            confluence_containers = soup.find_all(['div', 'section'], {'class': re.compile(r'confluence|score', re.I)})
            has_confluence_containers = len(confluence_containers) > 0
            
            # Look for charts or visualization containers
            chart_containers = soup.find_all(['canvas', 'div'], {'class': re.compile(r'chart|graph|visual', re.I)})
            has_charts = len(chart_containers) > 0
            
            # Check for loading indicators (good practice)
            loading_indicators = soup.find_all(['div', 'span'], {'class': re.compile(r'loading|spinner|loader', re.I)})
            has_loading_states = len(loading_indicators) > 0
            
            self.log_test_result(f"{test_name} - Market Containers", has_market_containers, 
                               f"Found {len(market_containers)} market containers")
            
            self.log_test_result(f"{test_name} - Confluence Containers", has_confluence_containers, 
                               f"Found {len(confluence_containers)} confluence containers")
            
            self.log_test_result(f"{test_name} - Chart Elements", has_charts, 
                               f"Found {len(chart_containers)} chart elements")
            
            self.log_test_result(f"{test_name} - Loading States", has_loading_states, 
                               f"Found {len(loading_indicators)} loading indicators")
            
            # Overall assessment
            overall_good = sum([has_market_containers, has_confluence_containers, has_charts]) >= 2
            
            return overall_good
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_caching_and_debouncing(self):
        """Test frontend caching and debouncing mechanisms."""
        test_name = "Caching and Debouncing"
        
        try:
            # Test multiple rapid requests to see caching behavior
            endpoint = "/api/mobile-unified/dashboard"
            url = f"{self.base_url}{endpoint}"
            
            # Make rapid consecutive requests
            response_times = []
            cache_headers = []
            
            for i in range(3):
                start_time = time.time()
                async with self.session.get(url) as response:
                    response_time = time.time() - start_time
                    response_times.append(response_time)
                    
                    # Check for cache headers
                    cache_control = response.headers.get('Cache-Control', '')
                    etag = response.headers.get('ETag', '')
                    last_modified = response.headers.get('Last-Modified', '')
                    
                    cache_headers.append({
                        'cache_control': cache_control,
                        'etag': etag,
                        'last_modified': last_modified
                    })
                
                await asyncio.sleep(0.1)  # Small delay between requests
            
            # Analyze caching behavior
            has_cache_headers = any(h['cache_control'] or h['etag'] or h['last_modified'] 
                                  for h in cache_headers)
            
            # Response times should be relatively consistent if caching is working
            if len(response_times) >= 2:
                time_variance = max(response_times) - min(response_times)
                consistent_times = time_variance < 0.5  # Less than 500ms variance
            else:
                consistent_times = True
            
            self.log_test_result(f"{test_name} - Cache Headers", has_cache_headers, 
                               f"Cache headers present: {has_cache_headers}")
            
            self.log_test_result(f"{test_name} - Response Consistency", consistent_times, 
                               f"Time variance: {time_variance:.3f}s")
            
            # Test debouncing by checking JavaScript
            html_content = await self.get_dashboard_html()
            debouncing_test = True
            
            if html_content:
                # Look for debouncing patterns in JavaScript
                debounce_patterns = [
                    r'debounce\s*\(',
                    r'setTimeout\s*\(',
                    r'clearTimeout\s*\(',
                    r'requestAnimationFrame',
                ]
                
                found_debouncing = any(re.search(pattern, html_content, re.IGNORECASE) 
                                     for pattern in debounce_patterns)
                
                self.log_test_result(f"{test_name} - Debouncing Patterns", found_debouncing, 
                                   f"Found debouncing patterns: {found_debouncing}")
            else:
                self.log_test_result(f"{test_name} - Debouncing Patterns", False, 
                                   "Could not check debouncing patterns")
            
            return has_cache_headers and consistent_times
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_fallback_mechanisms(self):
        """Test frontend fallback mechanisms when endpoints fail."""
        test_name = "Fallback Mechanisms"
        
        try:
            # Test with a potentially non-existent endpoint
            test_endpoint = "/api/mobile-unified/nonexistent"
            
            try:
                async with self.session.get(f"{self.base_url}{test_endpoint}") as response:
                    status_code = response.status
            except Exception:
                status_code = 0
            
            # Test that non-existent endpoints return appropriate status
            handles_missing_endpoints = status_code in [404, 500, 0]  # Any error status
            
            # Check dashboard still loads even with some failed endpoints
            html_content = await self.get_dashboard_html()
            dashboard_loads = html_content is not None
            
            self.log_test_result(f"{test_name} - Missing Endpoint Handling", handles_missing_endpoints, 
                               f"Non-existent endpoint status: {status_code}")
            
            self.log_test_result(f"{test_name} - Dashboard Resilience", dashboard_loads, 
                               f"Dashboard loads despite endpoint issues")
            
            # Test JavaScript error handling
            error_handling_test = True
            if html_content:
                # Look for error handling patterns
                error_patterns = [
                    r'try\s*{',
                    r'catch\s*\(',
                    r'\.catch\s*\(',
                    r'onerror\s*=',
                    r'addEventListener\s*\(\s*[\'"]error',
                ]
                
                found_error_handling = sum(1 for pattern in error_patterns 
                                         if re.search(pattern, html_content, re.IGNORECASE))
                
                error_handling_test = found_error_handling >= 2  # At least 2 error handling patterns
                
                self.log_test_result(f"{test_name} - Error Handling Patterns", error_handling_test, 
                                   f"Found {found_error_handling} error handling patterns")
            
            return handles_missing_endpoints and dashboard_loads and error_handling_test
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_real_time_updates(self):
        """Test real-time update functionality."""
        test_name = "Real-time Updates"
        
        try:
            # Check for WebSocket or polling mechanisms
            html_content = await self.get_dashboard_html()
            
            if not html_content:
                self.log_test_result(test_name, False, "Could not retrieve dashboard HTML")
                return False
            
            # Look for WebSocket usage
            websocket_patterns = [
                r'WebSocket\s*\(',
                r'new\s+WebSocket',
                r'ws://',
                r'wss://',
            ]
            
            found_websocket = any(re.search(pattern, html_content, re.IGNORECASE) 
                                for pattern in websocket_patterns)
            
            # Look for polling mechanisms
            polling_patterns = [
                r'setInterval\s*\(',
                r'setTimeout\s*\(',
                r'requestAnimationFrame',
                r'fetch\s*\(',
                r'XMLHttpRequest',
            ]
            
            found_polling = any(re.search(pattern, html_content, re.IGNORECASE) 
                              for pattern in polling_patterns)
            
            # Look for update functions
            update_patterns = [
                r'update\w*\s*\(',
                r'refresh\w*\s*\(',
                r'reload\w*\s*\(',
            ]
            
            found_updates = any(re.search(pattern, html_content, re.IGNORECASE) 
                              for pattern in update_patterns)
            
            has_real_time = found_websocket or found_polling
            has_update_logic = found_updates
            
            self.log_test_result(f"{test_name} - WebSocket Support", found_websocket, 
                               f"WebSocket patterns found: {found_websocket}")
            
            self.log_test_result(f"{test_name} - Polling Support", found_polling, 
                               f"Polling patterns found: {found_polling}")
            
            self.log_test_result(f"{test_name} - Update Functions", has_update_logic, 
                               f"Update function patterns found: {found_updates}")
            
            return has_real_time and has_update_logic
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def test_mobile_responsiveness(self):
        """Test mobile responsiveness of the frontend."""
        test_name = "Mobile Responsiveness"
        
        try:
            # Get dashboard HTML
            html_content = await self.get_dashboard_html()
            
            if not html_content:
                self.log_test_result(test_name, False, "Could not retrieve dashboard HTML")
                return False
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Check for viewport meta tag
            viewport_tag = soup.find('meta', {'name': 'viewport'})
            has_viewport = viewport_tag is not None
            
            # Check for responsive CSS patterns
            responsive_patterns = [
                r'@media\s*\(',
                r'mobile',
                r'tablet',
                r'responsive',
                r'flex',
                r'grid',
                r'max-width',
                r'min-width',
            ]
            
            found_responsive_css = sum(1 for pattern in responsive_patterns 
                                     if re.search(pattern, html_content, re.IGNORECASE))
            
            # Check for mobile-specific classes or IDs
            mobile_classes = soup.find_all(['div', 'section'], {'class': re.compile(r'mobile|responsive|flex|grid', re.I)})
            has_mobile_classes = len(mobile_classes) > 0
            
            responsive_score = sum([has_viewport, found_responsive_css >= 3, has_mobile_classes])
            is_responsive = responsive_score >= 2
            
            self.log_test_result(f"{test_name} - Viewport Meta Tag", has_viewport, 
                               f"Viewport tag present: {has_viewport}")
            
            self.log_test_result(f"{test_name} - Responsive CSS", found_responsive_css >= 3, 
                               f"Found {found_responsive_css} responsive patterns")
            
            self.log_test_result(f"{test_name} - Mobile Classes", has_mobile_classes, 
                               f"Found {len(mobile_classes)} mobile-friendly elements")
            
            return is_responsive
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.session:
            await self.session.close()
            logger.info("🧹 HTTP session closed")
    
    async def run_all_tests(self):
        """Run all frontend endpoint tests."""
        logger.info("🧪 Starting Frontend Endpoint Changes Tests")
        logger.info("=" * 55)
        
        # Initialize
        if not await self.initialize():
            logger.error("❌ Failed to initialize frontend tester")
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
            self.test_unified_endpoint_usage,
            self.test_dashboard_data_loading,
            self.test_caching_and_debouncing,
            self.test_fallback_mechanisms,
            self.test_real_time_updates,
            self.test_mobile_responsiveness,
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
        logger.info(f"📊 FRONTEND ENDPOINT CHANGES TEST SUMMARY")
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
    
    parser = argparse.ArgumentParser(description='Test Frontend Endpoint Changes')
    parser.add_argument('--base-url', default='http://localhost:8000', 
                       help='Base URL for the API server')
    args = parser.parse_args()
    
    tester = FrontendEndpointTester(base_url=args.base_url)
    success = await tester.run_all_tests()
    
    if success:
        logger.info("🎉 ALL FRONTEND ENDPOINT TESTS PASSED!")
        sys.exit(0)
    else:
        logger.error("💥 SOME FRONTEND ENDPOINT TESTS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())