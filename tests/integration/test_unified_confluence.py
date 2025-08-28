#!/usr/bin/env python3
"""
Test script for the unified confluence data flow system.

This script tests:
1. Cache key standardization
2. Data format consistency
3. Service integration
4. API response formats
"""

import asyncio
import json
import time
import sys
import os
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.confluence_service import confluence_service, ConfluenceCacheKeys
from src.core.cache_manager import cache_manager

class ConfluenceSystemTest:
    """Test suite for unified confluence system."""
    
    def __init__(self):
        self.test_symbol = "BTCUSDT"
        self.results = []
    
    async def run_all_tests(self):
        """Run all confluence system tests."""
        print("=" * 60)
        print("UNIFIED CONFLUENCE SYSTEM TEST")
        print("=" * 60)
        
        tests = [
            self.test_cache_key_patterns,
            self.test_data_standardization,
            self.test_service_integration,
            self.test_formatting_consistency,
            self.test_api_compatibility,
            self.test_cache_performance
        ]
        
        for test in tests:
            try:
                print(f"\n{'='*20}")
                print(f"Running: {test.__name__}")
                print('='*20)
                await test()
                self.results.append((test.__name__, "✅ PASS"))
                print(f"✅ {test.__name__} PASSED")
            except Exception as e:
                self.results.append((test.__name__, f"❌ FAIL: {str(e)}"))
                print(f"❌ {test.__name__} FAILED: {e}")
        
        self.print_summary()
    
    async def test_cache_key_patterns(self):
        """Test that cache keys follow standardized patterns."""
        print("Testing cache key standardization...")
        
        # Test key generation
        detailed_key = ConfluenceCacheKeys.SYMBOL_DETAILED.format(symbol=self.test_symbol)
        score_key = ConfluenceCacheKeys.SYMBOL_SCORE.format(symbol=self.test_symbol)
        
        expected_detailed = f"confluence:detailed:{self.test_symbol}"
        expected_score = f"confluence:score:{self.test_symbol}"
        
        assert detailed_key == expected_detailed, f"Detailed key mismatch: {detailed_key} != {expected_detailed}"
        assert score_key == expected_score, f"Score key mismatch: {score_key} != {expected_score}"
        
        print(f"✓ Detailed key: {detailed_key}")
        print(f"✓ Score key: {score_key}")
        print(f"✓ Aggregated key: {ConfluenceCacheKeys.AGGREGATED}")
    
    async def test_data_standardization(self):
        """Test that data formats are standardized across the system."""
        print("Testing data standardization...")
        
        # Create mock analysis result
        mock_analysis = {
            'final_score': 75.5,
            'component_scores': {
                'technical': 80.0,
                'volume': 70.0,
                'orderflow': 75.0
            },
            'reliability': 0.85,
            'metadata': {
                'weights': {'technical': 0.4, 'volume': 0.3, 'orderflow': 0.3}
            }
        }
        
        # Cache using unified service
        success = await confluence_service.cache_analysis_result(self.test_symbol, mock_analysis)
        assert success, "Failed to cache analysis result"
        
        # Retrieve and verify format
        detailed_data = await confluence_service.get_detailed_analysis(self.test_symbol)
        assert detailed_data is not None, "Failed to retrieve detailed data"
        
        # Check required fields
        required_fields = ['symbol', 'confluence_score', 'signal', 'components', 'reliability', 'timestamp', 'version']
        for field in required_fields:
            assert field in detailed_data, f"Missing required field: {field}"
        
        # Verify data consistency
        assert detailed_data['symbol'] == self.test_symbol
        assert detailed_data['confluence_score'] == 75.5
        assert detailed_data['reliability'] == 0.85
        
        print(f"✓ Standardized data format verified")
        print(f"✓ Symbol: {detailed_data['symbol']}")
        print(f"✓ Score: {detailed_data['confluence_score']}")
        print(f"✓ Signal: {detailed_data['signal']}")
    
    async def test_service_integration(self):
        """Test integration between different service methods."""
        print("Testing service integration...")
        
        # Test score retrieval
        score_data = await confluence_service.get_symbol_score(self.test_symbol)
        assert score_data is not None, "Failed to retrieve score data"
        
        # Test aggregated data
        aggregated = await confluence_service.get_aggregated_analysis()
        assert aggregated is not None, "Failed to retrieve aggregated data"
        assert 'symbols' in aggregated, "Missing symbols in aggregated data"
        assert self.test_symbol in aggregated['symbols'], f"{self.test_symbol} not in aggregated data"
        
        # Test multiple symbol retrieval
        symbols = [self.test_symbol, "ETHUSDT", "SOLUSDT"]
        multiple_scores = await confluence_service.get_multiple_scores(symbols)
        assert self.test_symbol in multiple_scores, f"{self.test_symbol} not in multiple scores"
        
        print(f"✓ Score data retrieval works")
        print(f"✓ Aggregated data contains {len(aggregated.get('symbols', {}))} symbols")
        print(f"✓ Multiple symbol retrieval works for {len(multiple_scores)} symbols")
    
    async def test_formatting_consistency(self):
        """Test that formatting is consistent across all output types."""
        print("Testing formatting consistency...")
        
        # Get detailed data
        detailed_data = await confluence_service.get_detailed_analysis(self.test_symbol)
        assert detailed_data is not None, "No detailed data available for formatting test"
        
        # Test API formatting
        api_format = confluence_service.format_for_api(detailed_data)
        assert 'symbol' in api_format, "API format missing symbol"
        assert 'confluence_score' in api_format, "API format missing confluence_score"
        assert 'signal' in api_format, "API format missing signal"
        
        # Test mobile formatting
        mobile_format = confluence_service.format_for_mobile(detailed_data)
        assert 'symbol' in mobile_format, "Mobile format missing symbol"
        assert 'score' in mobile_format, "Mobile format missing score"
        
        # Test terminal formatting
        terminal_format = confluence_service.format_for_terminal(detailed_data)
        assert isinstance(terminal_format, str), "Terminal format should be string"
        assert len(terminal_format) > 0, "Terminal format should not be empty"
        
        print(f"✓ API format validated")
        print(f"✓ Mobile format validated")
        print(f"✓ Terminal format validated")
    
    async def test_api_compatibility(self):
        """Test compatibility with existing API expectations."""
        print("Testing API compatibility...")
        
        # Test that API format matches expected structure
        detailed_data = await confluence_service.get_detailed_analysis(self.test_symbol)
        api_format = confluence_service.format_for_api(detailed_data)
        
        # Check API response structure
        expected_api_fields = ['symbol', 'confluence_score', 'signal', 'reliability', 'components', 'timestamp', 'metadata']
        for field in expected_api_fields:
            assert field in api_format, f"API format missing expected field: {field}"
        
        # Check mobile format compatibility
        mobile_format = confluence_service.format_for_mobile(detailed_data)
        expected_mobile_fields = ['symbol', 'score', 'signal', 'components', 'reliability']
        for field in expected_mobile_fields:
            assert field in mobile_format, f"Mobile format missing expected field: {field}"
        
        print(f"✓ API format compatibility verified")
        print(f"✓ Mobile format compatibility verified")
    
    async def test_cache_performance(self):
        """Test cache performance and statistics."""
        print("Testing cache performance...")
        
        start_time = time.time()
        
        # Test cache statistics
        stats = await confluence_service.get_cache_statistics()
        assert 'cache_keys_pattern' in stats, "Stats missing cache key patterns"
        assert 'ttl_values' in stats, "Stats missing TTL values"
        
        # Test batch operations
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
        batch_results = await confluence_service.get_multiple_scores(symbols)
        
        end_time = time.time()
        operation_time = end_time - start_time
        
        print(f"✓ Cache statistics retrieved")
        print(f"✓ Batch operation completed in {operation_time:.3f}s")
        print(f"✓ Retrieved data for {len(batch_results)} symbols")
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, result in self.results if result.startswith("✅"))
        failed = len(self.results) - passed
        
        for test_name, result in self.results:
            print(f"{result} {test_name}")
        
        print(f"\nTotal: {len(self.results)} tests")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        if failed == 0:
            print("\n🎉 ALL TESTS PASSED! Unified confluence system is working correctly.")
        else:
            print(f"\n⚠️  {failed} tests failed. Please review and fix issues.")

async def main():
    """Main test runner."""
    tester = ConfluenceSystemTest()
    await tester.run_all_tests()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Test runner error: {e}")
        sys.exit(1)