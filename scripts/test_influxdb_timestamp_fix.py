#!/usr/bin/env python3
"""
Test script to verify InfluxDB timestamp field type conflict fixes.

This script tests the timestamp normalization functionality and ensures
that analysis data can be stored successfully without field type conflicts.

Usage:
    python scripts/test_influxdb_timestamp_fix.py
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
import time
import pandas as pd

# Add src to path and set proper Python path
project_root = os.path.join(os.path.dirname(__file__), '..')
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, project_root)
sys.path.insert(0, src_path)
os.environ['PYTHONPATH'] = f"{project_root}:{src_path}"

try:
    from src.data_storage.database import DatabaseClient
    from src.core.config import Config
except ImportError:
    # Alternative import approach
    import importlib.util
    
    # Import database module
    db_spec = importlib.util.spec_from_file_location("database", os.path.join(src_path, "data_storage", "database.py"))
    db_module = importlib.util.module_from_spec(db_spec)
    sys.modules["database"] = db_module
    db_spec.loader.exec_module(db_module)
    DatabaseClient = db_module.DatabaseClient
    
    # Import config module
    config_spec = importlib.util.spec_from_file_location("config", os.path.join(src_path, "core", "config.py"))
    config_module = importlib.util.module_from_spec(config_spec)
    sys.modules["config"] = config_module
    config_spec.loader.exec_module(config_module)
    Config = config_module.Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_timestamp_normalization():
    """Test the timestamp normalization functionality."""
    logger.info("Starting InfluxDB timestamp fix verification...")
    
    try:
        # Load configuration
        config = Config()
        await config.load()
        
        # Initialize database client
        db_client = DatabaseClient(config.config)
        
        # Check database health
        logger.info("Checking database health...")
        if not await db_client.is_healthy():
            logger.error("Database is not healthy - cannot proceed with tests")
            return False
        
        logger.info("✓ Database is healthy")
        
        # Test 1: Various timestamp formats
        logger.info("Test 1: Testing various timestamp formats...")
        
        test_cases = [
            {
                'name': 'Integer milliseconds timestamp',
                'data': {
                    'confluence_score': 75.5,
                    'timestamp': int(time.time() * 1000),
                    'test_field': 42.0
                }
            },
            {
                'name': 'Float seconds timestamp', 
                'data': {
                    'confluence_score': 68.2,
                    'timestamp': time.time(),
                    'test_field': 37.5
                }
            },
            {
                'name': 'ISO string timestamp',
                'data': {
                    'confluence_score': 82.1,
                    'timestamp': datetime.now().isoformat(),
                    'test_field': 51.3
                }
            },
            {
                'name': 'String integer timestamp',
                'data': {
                    'confluence_score': 59.7,
                    'timestamp': str(int(time.time() * 1000)),
                    'test_field': 29.8
                }
            },
            {
                'name': 'Nested timestamp in component data',
                'data': {
                    'confluence_score': 71.4,
                    'components': {
                        'orderflow': {
                            'score': 65.0,
                            'timestamp': int(time.time() * 1000)
                        }
                    },
                    'test_field': 33.7
                }
            }
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            logger.info(f"  Testing: {test_case['name']}")
            
            try:
                success = await db_client.store_analysis(
                    f'TEST_SYMBOL_{i}',
                    test_case['data']
                )
                
                if success:
                    logger.info(f"    ✓ SUCCESS: {test_case['name']}")
                    results.append({'test': test_case['name'], 'success': True, 'error': None})
                else:
                    logger.error(f"    ✗ FAILED: {test_case['name']}")
                    results.append({'test': test_case['name'], 'success': False, 'error': 'Store returned False'})
                    
            except Exception as e:
                logger.error(f"    ✗ ERROR: {test_case['name']} - {str(e)}")
                results.append({'test': test_case['name'], 'success': False, 'error': str(e)})
        
        # Test 2: Complex analysis data structure (similar to real confluence output)
        logger.info("Test 2: Testing complex analysis data structure...")
        
        complex_analysis_data = {
            'confluence_score': 78.5,
            'timestamp': int(time.time() * 1000),
            'components': {
                'orderflow': {'score': 72.0, 'confidence': 0.85},
                'sentiment': {'score': 81.5, 'confidence': 0.92},
                'liquidity': {'score': 75.2, 'confidence': 0.78}
            },
            'signals': {
                'primary': 'BUY',
                'secondary': 'STRONG'
            },
            'metadata': {
                'processing_time': 2.34,
                'data_quality': 0.95,
                'timestamp': datetime.now().isoformat()  # Different timestamp format in nested data
            }
        }
        
        try:
            success = await db_client.store_analysis('COMPLEX_TEST_SYMBOL', complex_analysis_data)
            
            if success:
                logger.info("  ✓ SUCCESS: Complex analysis data structure")
                results.append({'test': 'Complex analysis data', 'success': True, 'error': None})
            else:
                logger.error("  ✗ FAILED: Complex analysis data structure")
                results.append({'test': 'Complex analysis data', 'success': False, 'error': 'Store returned False'})
                
        except Exception as e:
            logger.error(f"  ✗ ERROR: Complex analysis data - {str(e)}")
            results.append({'test': 'Complex analysis data', 'success': False, 'error': str(e)})
        
        # Test 3: Schema conflict check
        logger.info("Test 3: Running schema conflict check...")
        
        try:
            schema_status = await db_client.check_and_fix_schema_conflicts()
            logger.info(f"  Schema conflicts found: {len(schema_status['conflicts_found'])}")
            logger.info(f"  Fixes applied: {len(schema_status['fixes_applied'])}")
            logger.info(f"  Errors: {len(schema_status['errors'])}")
            
            results.append({
                'test': 'Schema conflict check',
                'success': len(schema_status['errors']) == 0,
                'error': ', '.join(schema_status['errors']) if schema_status['errors'] else None
            })
            
        except Exception as e:
            logger.error(f"  ✗ ERROR: Schema conflict check - {str(e)}")
            results.append({'test': 'Schema conflict check', 'success': False, 'error': str(e)})
        
        # Test 4: Market data storage (should also work with timestamp normalization)
        logger.info("Test 4: Testing market data storage...")
        
        market_data = {
            'price': 45250.75,
            'volume': 123.45,
            'timestamp': int(time.time() * 1000)
        }
        
        try:
            await db_client.store_market_data('TEST_MARKET_SYMBOL', market_data)
            logger.info("  ✓ SUCCESS: Market data storage")
            results.append({'test': 'Market data storage', 'success': True, 'error': None})
            
        except Exception as e:
            logger.error(f"  ✗ ERROR: Market data storage - {str(e)}")
            results.append({'test': 'Market data storage', 'success': False, 'error': str(e)})
        
        # Summary
        successful_tests = sum(1 for r in results if r['success'])
        total_tests = len(results)
        
        logger.info(f"\n=== TEST SUMMARY ===")
        logger.info(f"Total tests: {total_tests}")
        logger.info(f"Successful: {successful_tests}")
        logger.info(f"Failed: {total_tests - successful_tests}")
        logger.info(f"Success rate: {successful_tests/total_tests*100:.1f}%")
        
        if successful_tests == total_tests:
            logger.info("🎉 ALL TESTS PASSED - InfluxDB timestamp fixes are working correctly!")
            return_code = True
        else:
            logger.error("❌ SOME TESTS FAILED - Review the errors above")
            logger.info("\nFailed tests:")
            for result in results:
                if not result['success']:
                    logger.error(f"  - {result['test']}: {result['error']}")
            return_code = False
        
        # Cleanup test data
        logger.info("\nCleaning up test data...")
        try:
            # Note: In a real cleanup, you might want to delete the test records
            # For now, we'll just log that cleanup would happen here
            logger.info("  Test data cleanup completed (test records left for verification)")
        except Exception as e:
            logger.warning(f"  Cleanup warning: {str(e)}")
        
        await db_client.close()
        return return_code
        
    except Exception as e:
        logger.error(f"Fatal test error: {str(e)}")
        return False


async def main():
    """Main test function."""
    success = await test_timestamp_normalization()
    
    if success:
        print("\n✅ VERIFICATION COMPLETE: InfluxDB timestamp fixes are working correctly")
        print("The field type conflict issue should now be resolved.")
        sys.exit(0)
    else:
        print("\n❌ VERIFICATION FAILED: Issues detected with timestamp handling")
        print("Please review the error logs above and ensure InfluxDB is properly configured.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())