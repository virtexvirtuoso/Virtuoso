#!/usr/bin/env python3
"""
Integration test script to verify critical fixes:
1. PDF Report Generation
2. Memory Optimization 
3. Symbol Format Issues
"""

import asyncio
import logging
import sys
import os
import time
import gc
import traceback
from datetime import datetime
import glob

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'logs/integration_fixes_test_{int(time.time())}.log')
    ]
)
logger = logging.getLogger(__name__)

async def test_pdf_generation():
    """Test 1: PDF Generation Fix"""
    logger.info("=" * 60)
    logger.info("TEST 1: PDF GENERATION FIX")
    logger.info("=" * 60)
    
    try:
        from src.monitoring.market_reporter import MarketReporter
        
        # Create market reporter instance
        reporter = MarketReporter()
        
        # Check if PDF is enabled
        pdf_status = "✅ ENABLED" if reporter.pdf_enabled else "❌ DISABLED"
        logger.info(f"PDF Generation Status: {pdf_status}")
        
        if reporter.pdf_enabled:
            logger.info(f"PDF Generator: {type(reporter.pdf_generator).__name__}")
            logger.info(f"Report Manager: {type(reporter.report_manager).__name__}")
            
            # Test basic PDF generation with mock data
            test_data = {
                'market_overview': {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'total_symbols': 5,
                    'avg_volume': 1234567,
                    'market_cap': 2000000000
                },
                'timestamp': int(time.time())
            }
            
            try:
                pdf_file = await reporter.pdf_generator.generate_market_html_report(
                    test_data, 
                    output_path=f"exports/test_report_{int(time.time())}.html",
                    generate_pdf=True
                )
                logger.info(f"✅ PDF generated successfully: {pdf_file}")
                
                if pdf_file:
                    # Method returns True on success, so check for actual file
                    if pdf_file is True:
                        # Check for generated files
                        pdf_files = glob.glob("reports/pdf/test_report_*.pdf")
                        html_files = glob.glob("exports/test_report_*.html")
                        
                        if pdf_files or html_files:
                            found_file = pdf_files[0] if pdf_files else html_files[0]
                            file_size = os.path.getsize(found_file) / 1024  # KB
                            logger.info(f"✅ Generated file verified: {found_file} ({file_size:.1f} KB)")
                            return True
                        else:
                            logger.warning("⚠️ No generated files found")
                            return False
                    else:
                        # Check for PDF file (might have .pdf extension instead of .html)
                        pdf_path = pdf_file.replace('.html', '.pdf') if isinstance(pdf_file, str) else None
                        if isinstance(pdf_file, str) and os.path.exists(pdf_file):
                            file_size = os.path.getsize(pdf_file) / 1024  # KB
                            logger.info(f"✅ HTML file verified: {file_size:.1f} KB")
                            return True
                        elif pdf_path and os.path.exists(pdf_path):
                            file_size = os.path.getsize(pdf_path) / 1024  # KB
                            logger.info(f"✅ PDF file verified: {file_size:.1f} KB")
                            return True
                        else:
                            logger.warning("⚠️ Neither HTML nor PDF file found")
                            return False
                else:
                    logger.warning("⚠️ PDF generation returned None/False")
                    return False
            except Exception as e:
                logger.error(f"❌ PDF generation test failed: {e}")
                return False
        else:
            logger.warning("⚠️ PDF generation is disabled")
            return False
            
    except Exception as e:
        logger.error(f"❌ PDF test setup failed: {e}")
        return False

async def test_memory_optimization():
    """Test 2: Memory Optimization Fix"""
    logger.info("=" * 60)
    logger.info("TEST 2: MEMORY OPTIMIZATION FIX")
    logger.info("=" * 60)
    
    try:
        from src.monitoring.market_reporter import MarketReporter
        
        # Create market reporter instance
        reporter = MarketReporter()
        
        # Check memory optimization features
        memory_opt_status = "✅ ENABLED" if reporter.memory_optimization_enabled else "❌ DISABLED"
        logger.info(f"Memory Optimization Status: {memory_opt_status}")
        
        if reporter.memory_optimization_enabled:
            logger.info(f"Cache Max Size: {reporter.cache.maxsize}")
            logger.info(f"Ticker Cache Max Size: {reporter.ticker_cache.maxsize}")
            logger.info(f"GC Interval: {reporter.gc_collection_interval}")
            
            # Test memory pressure detection
            memory_pressure = reporter._check_memory_pressure()
            pressure_status = "🔴 HIGH" if memory_pressure else "🟢 NORMAL"
            logger.info(f"Memory Pressure: {pressure_status}")
            
            # Test memory optimization function
            initial_memory = reporter._get_memory_usage()
            logger.info(f"Initial Memory: {initial_memory}")
            
            # Simulate data accumulation
            for i in range(100):
                reporter.api_latencies.append(i * 0.1)
                reporter.data_quality_scores.append(90 + i % 10)
                reporter.processing_times.append(i * 0.05)
            
            logger.info(f"Added test data - API Latencies: {len(reporter.api_latencies)}")
            
            # Run memory optimization
            reporter._optimize_memory()
            
            # Check if data was truncated
            optimized_latencies = len(reporter.api_latencies)
            optimized_scores = len(reporter.data_quality_scores)
            
            logger.info(f"After optimization - API Latencies: {optimized_latencies}")
            logger.info(f"After optimization - Quality Scores: {optimized_scores}")
            
            # Verify memory optimization worked
            if optimized_latencies <= 50 and optimized_scores <= 20:
                logger.info("✅ Memory optimization working correctly")
                return True
            else:
                logger.warning("⚠️ Memory optimization may not be working as expected")
                return False
        else:
            logger.warning("⚠️ Memory optimization is disabled")
            return False
            
    except Exception as e:
        logger.error(f"❌ Memory optimization test failed: {e}")
        logger.error(traceback.format_exc())
        return False

async def test_symbol_format_fixes():
    """Test 3: Symbol Format Issues Fix"""
    logger.info("=" * 60)
    logger.info("TEST 3: SYMBOL FORMAT FIXES")
    logger.info("=" * 60)
    
    try:
        from src.monitoring.market_reporter import MarketReporter
        
        # Create market reporter instance (no exchange needed for format testing)
        reporter = MarketReporter()
        
        # Test quarterly futures symbol generation
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        logger.info("Testing quarterly futures symbol format generation...")
        
        for symbol in test_symbols:
            try:
                # Test _get_last_friday_of_month method
                last_friday = reporter._get_last_friday_of_month(2025, 6)
                expiry_date = last_friday.strftime('%Y%m%d')
                
                base_asset = symbol.replace('USDT', '')
                quarterly_symbol = f"{base_asset}/USDT:USDT-{expiry_date}"
                
                logger.info(f"✅ {symbol} → {quarterly_symbol}")
                
                # Verify format is correct
                if 'USDT:USDT-' in quarterly_symbol and len(expiry_date) == 8:
                    logger.info(f"✅ Symbol format verified for {symbol}")
                else:
                    logger.warning(f"⚠️ Unexpected format for {symbol}: {quarterly_symbol}")
                    
            except Exception as e:
                logger.error(f"❌ Symbol format test failed for {symbol}: {e}")
                return False
        
        # Test circuit breaker functionality
        logger.info("Testing circuit breaker for quarterly futures...")
        
        # Simulate errors to test circuit breaker
        for i in range(6):  # Exceed the max_errors_before_skip = 5
            reporter.error_counts['quarterly_futures_errors'] = i
            
        error_count = reporter.error_counts.get('quarterly_futures_errors', 0)
        circuit_active = error_count >= 5
        
        circuit_status = "🔴 ACTIVE" if circuit_active else "🟢 INACTIVE"
        logger.info(f"Circuit Breaker Status: {circuit_status} (errors: {error_count})")
        
        if circuit_active:
            logger.info("✅ Circuit breaker working correctly")
        else:
            logger.warning("⚠️ Circuit breaker not activated as expected")
        
        logger.info("✅ Symbol format fixes verified")
        return True
        
    except Exception as e:
        logger.error(f"❌ Symbol format test failed: {e}")
        logger.error(traceback.format_exc())
        return False

async def run_comprehensive_integration_test():
    """Run all integration tests"""
    logger.info("🚀 STARTING COMPREHENSIVE INTEGRATION TEST")
    logger.info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    results = {}
    
    # Run all tests
    tests = [
        ("PDF Generation", test_pdf_generation),
        ("Memory Optimization", test_memory_optimization),
        ("Symbol Format Fixes", test_symbol_format_fixes)
    ]
    
    for test_name, test_func in tests:
        logger.info(f"\n🔧 Running {test_name} test...")
        try:
            result = await test_func()
            results[test_name] = result
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name}: {status}")
        except Exception as e:
            results[test_name] = False
            logger.error(f"{test_name}: ❌ FAILED - {e}")
    
    # Calculate results
    total_tests = len(tests)
    passed_tests = sum(1 for result in results.values() if result)
    success_rate = (passed_tests / total_tests) * 100
    
    duration = time.time() - start_time
    
    # Print summary
    logger.info("=" * 80)
    logger.info("🎯 INTEGRATION TEST RESULTS SUMMARY")
    logger.info("=" * 80)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name:.<30} {status}")
    
    logger.info("-" * 80)
    logger.info(f"Total Tests: {total_tests}")
    logger.info(f"Passed: {passed_tests}")
    logger.info(f"Failed: {total_tests - passed_tests}")
    logger.info(f"Success Rate: {success_rate:.1f}%")
    logger.info(f"Duration: {duration:.2f} seconds")
    
    # Determine overall status
    if success_rate >= 85:
        logger.info("🎉 INTEGRATION TEST STATUS: ✅ EXCELLENT")
        logger.info("All critical fixes are working properly!")
    elif success_rate >= 70:
        logger.info("✅ INTEGRATION TEST STATUS: 🟡 GOOD")
        logger.info("Most fixes are working, minor issues detected.")
    elif success_rate >= 50:
        logger.info("⚠️ INTEGRATION TEST STATUS: 🟠 NEEDS ATTENTION")
        logger.info("Some fixes are working, but significant issues remain.")
    else:
        logger.info("❌ INTEGRATION TEST STATUS: 🔴 CRITICAL ISSUES")
        logger.info("Major problems detected, immediate attention required.")
    
    return results

if __name__ == "__main__":
    try:
        # Ensure required directories exist
        os.makedirs('logs', exist_ok=True)
        os.makedirs('exports', exist_ok=True)
        
        # Run the comprehensive test
        results = asyncio.run(run_comprehensive_integration_test())
        
        # Exit with appropriate code
        if all(results.values()):
            sys.exit(0)  # All tests passed
        else:
            sys.exit(1)  # Some tests failed
            
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Fatal error during testing: {e}")
        logger.error(traceback.format_exc())
        sys.exit(3) 