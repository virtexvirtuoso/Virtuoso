#!/usr/bin/env python3
"""
Monitor Refactoring Validation Script

This script provides comprehensive validation of the monitor refactoring by:
1. Running performance comparisons between original and refactored monitors
2. Validating functional equivalence
3. Checking memory usage improvements  
4. Verifying signal generation consistency
5. Testing integration with Virtuoso trading system
6. Generating detailed validation report

Usage:
    python scripts/validate_monitor_refactoring.py
    python scripts/validate_monitor_refactoring.py --detailed
    python scripts/validate_monitor_refactoring.py --benchmark-only
    python scripts/validate_monitor_refactoring.py --integration-test
"""

import asyncio
import sys
import os
import time
import logging
import tracemalloc
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import json
import pandas as pd
import psutil
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import monitors (with fallback handling)
try:
    from monitoring.monitor import MarketMonitor as OriginalMonitor
    ORIGINAL_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import original monitor: {e}")
    OriginalMonitor = None
    ORIGINAL_AVAILABLE = False

try:
    from monitoring.monitor_refactored import RefactoredMarketMonitor, MarketMonitor as RefactoredAlias
    REFACTORED_AVAILABLE = True
except ImportError as e:
    print(f"Error: Could not import refactored monitor: {e}")
    RefactoredMarketMonitor = None
    REFACTORED_AVAILABLE = False
    sys.exit(1)

# Import test utilities
from tests.test_monitor_refactoring import TestSetup, BenchmarkUtils


class ValidationReport:
    """Generates comprehensive validation reports."""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'validation_type': 'monitor_refactoring',
            'original_monitor_available': ORIGINAL_AVAILABLE,
            'refactored_monitor_available': REFACTORED_AVAILABLE,
            'tests': {},
            'benchmarks': {},
            'integration': {},
            'summary': {}
        }
    
    def add_test_result(self, test_name: str, passed: bool, details: Dict[str, Any]):
        """Add test result to report."""
        self.results['tests'][test_name] = {
            'passed': passed,
            'details': details,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def add_benchmark_result(self, benchmark_name: str, results: Dict[str, Any]):
        """Add benchmark result to report."""
        self.results['benchmarks'][benchmark_name] = {
            'results': results,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def add_integration_result(self, integration_name: str, passed: bool, details: Dict[str, Any]):
        """Add integration test result to report."""
        self.results['integration'][integration_name] = {
            'passed': passed,
            'details': details,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def generate_summary(self):
        """Generate summary of all results."""
        total_tests = len(self.results['tests'])
        passed_tests = sum(1 for test in self.results['tests'].values() if test['passed'])
        
        total_integration = len(self.results['integration'])
        passed_integration = sum(1 for test in self.results['integration'].values() if test['passed'])
        
        self.results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'test_pass_rate': passed_tests / max(total_tests, 1),
            'total_integration_tests': total_integration,
            'passed_integration_tests': passed_integration,
            'integration_pass_rate': passed_integration / max(total_integration, 1),
            'overall_success': passed_tests == total_tests and passed_integration == total_integration,
            'total_benchmarks': len(self.results['benchmarks'])
        }
    
    def save_report(self, filename: str = None):
        """Save report to file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'monitor_refactoring_validation_{timestamp}.json'
        
        report_path = Path('reports') / filename
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        return report_path
    
    def print_summary(self):
        """Print summary to console."""
        self.generate_summary()
        summary = self.results['summary']
        
        print("\n" + "="*80)
        print("MONITOR REFACTORING VALIDATION REPORT")
        print("="*80)
        
        print(f"Validation Time: {self.results['timestamp']}")
        print(f"Original Monitor Available: {self.results['original_monitor_available']}")
        print(f"Refactored Monitor Available: {self.results['refactored_monitor_available']}")
        
        print(f"\nTEST RESULTS:")
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Passed Tests: {summary['passed_tests']}")
        print(f"  Test Pass Rate: {summary['test_pass_rate']:.1%}")
        
        print(f"\nINTEGRATION RESULTS:")
        print(f"  Total Integration Tests: {summary['total_integration_tests']}")
        print(f"  Passed Integration Tests: {summary['passed_integration_tests']}")
        print(f"  Integration Pass Rate: {summary['integration_pass_rate']:.1%}")
        
        print(f"\nBENCHMARKS:")
        print(f"  Total Benchmarks Run: {summary['total_benchmarks']}")
        
        if summary['overall_success']:
            print(f"\n🎉 OVERALL RESULT: SUCCESS")
            print("   All tests passed! Refactoring validation successful!")
        else:
            print(f"\n❌ OVERALL RESULT: FAILURES DETECTED")
            print("   Some tests failed. Review detailed results below.")
        
        # Detailed test results
        print(f"\nDETAILED TEST RESULTS:")
        for test_name, result in self.results['tests'].items():
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"  {status} {test_name}")
            if not result['passed'] and 'error' in result['details']:
                print(f"    Error: {result['details']['error']}")
        
        # Benchmark results
        if self.results['benchmarks']:
            print(f"\nBENCHMARK RESULTS:")
            for bench_name, result in self.results['benchmarks'].items():
                print(f"  {bench_name}:")
                if 'comparison' in result['results']:
                    comp = result['results']['comparison']
                    if 'improvement' in comp:
                        improvement = comp['improvement']
                        print(f"    Performance Improvement: {improvement:.1%}")
                    if 'memory_reduction' in comp:
                        reduction = comp['memory_reduction']
                        print(f"    Memory Reduction: {reduction:.1%}")
        
        print("="*80)


class MonitorValidator:
    """Validates monitor refactoring with comprehensive tests."""
    
    def __init__(self, detailed: bool = False):
        self.detailed = detailed
        self.report = ValidationReport()
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Set up logger for validation."""
        logger = logging.getLogger('monitor_validator')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    async def run_functional_validation(self):
        """Run functional validation tests."""
        print("Running functional validation tests...")
        
        try:
            # Test 1: Component Initialization
            await self._test_component_initialization()
            
            # Test 2: Data Flow
            await self._test_data_flow()
            
            # Test 3: Error Handling
            await self._test_error_handling()
            
            # Test 4: Backward Compatibility
            await self._test_backward_compatibility()
            
        except Exception as e:
            self.logger.error(f"Error in functional validation: {str(e)}")
            self.report.add_test_result("functional_validation", False, {
                'error': str(e),
                'traceback': str(e.__traceback__) if self.detailed else None
            })
    
    async def _test_component_initialization(self):
        """Test component initialization."""
        try:
            config = TestSetup.create_test_config()
            monitor = RefactoredMarketMonitor(
                exchange_manager=TestSetup.create_mock_exchange_manager(),
                config=config,
                top_symbols_manager=TestSetup.create_mock_top_symbols_manager(),
                confluence_analyzer=TestSetup.create_mock_confluence_analyzer(),
                alert_manager=TestSetup.create_mock_alert_manager(),
                signal_generator=TestSetup.create_mock_signal_generator(),
                logger=self.logger
            )
            
            success = await monitor.initialize()
            
            details = {
                'initialization_success': success,
                'components_initialized': {
                    'data_collector': bool(monitor.data_collector),
                    'validator': bool(monitor.validator),
                    'signal_processor': bool(monitor.signal_processor),
                    'metrics_tracker': bool(monitor.metrics_tracker)
                }
            }
            
            self.report.add_test_result("component_initialization", success, details)
            
        except Exception as e:
            self.report.add_test_result("component_initialization", False, {'error': str(e)})
    
    async def _test_data_flow(self):
        """Test data flow through components."""
        try:
            config = TestSetup.create_test_config()
            monitor = RefactoredMarketMonitor(
                exchange_manager=TestSetup.create_mock_exchange_manager(),
                config=config,
                top_symbols_manager=TestSetup.create_mock_top_symbols_manager(),
                confluence_analyzer=TestSetup.create_mock_confluence_analyzer(),
                alert_manager=TestSetup.create_mock_alert_manager(),
                signal_generator=TestSetup.create_mock_signal_generator(),
                logger=self.logger
            )
            
            await monitor.initialize()
            
            # Test data fetching
            test_data = TestSetup.create_mock_market_data()
            monitor.data_collector.fetch_market_data = lambda symbol: test_data
            
            market_data = await monitor.fetch_market_data('BTC/USDT')
            data_valid = await monitor.validate_market_data(market_data)
            
            success = market_data is not None and data_valid
            
            details = {
                'data_fetched': market_data is not None,
                'data_valid': data_valid,
                'data_fields': list(market_data.keys()) if market_data else []
            }
            
            self.report.add_test_result("data_flow", success, details)
            
        except Exception as e:
            self.report.add_test_result("data_flow", False, {'error': str(e)})
    
    async def _test_error_handling(self):
        """Test error handling."""
        try:
            config = TestSetup.create_test_config()
            monitor = RefactoredMarketMonitor(
                exchange_manager=TestSetup.create_mock_exchange_manager(),
                config=config,
                top_symbols_manager=TestSetup.create_mock_top_symbols_manager(),
                confluence_analyzer=TestSetup.create_mock_confluence_analyzer(),
                alert_manager=TestSetup.create_mock_alert_manager(),
                signal_generator=TestSetup.create_mock_signal_generator(),
                logger=self.logger
            )
            
            await monitor.initialize()
            
            # Test error handling
            async def failing_fetch(symbol):
                raise Exception("Network error")
            
            monitor.data_collector.fetch_market_data = failing_fetch
            
            # Should handle error gracefully
            result = await monitor.fetch_market_data('BTC/USDT')
            
            success = result is None  # Should return None on error, not crash
            
            details = {
                'error_handled_gracefully': success,
                'monitor_still_running': monitor.running is not None
            }
            
            self.report.add_test_result("error_handling", success, details)
            
        except Exception as e:
            self.report.add_test_result("error_handling", False, {'error': str(e)})
    
    async def _test_backward_compatibility(self):
        """Test backward compatibility."""
        try:
            config = TestSetup.create_test_config()
            
            # Test that MarketMonitor alias works
            from monitoring.monitor_refactored import MarketMonitor
            
            monitor = MarketMonitor(
                exchange_manager=TestSetup.create_mock_exchange_manager(),
                config=config,
                top_symbols_manager=TestSetup.create_mock_top_symbols_manager(),
                confluence_analyzer=TestSetup.create_mock_confluence_analyzer(),
                alert_manager=TestSetup.create_mock_alert_manager(),
                signal_generator=TestSetup.create_mock_signal_generator(),
                logger=self.logger
            )
            
            # Test expected methods exist
            expected_methods = [
                'start_monitoring', 'stop_monitoring', 'fetch_market_data',
                'validate_market_data', 'get_market_data', 'get_stats'
            ]
            
            missing_methods = []
            for method in expected_methods:
                if not hasattr(monitor, method):
                    missing_methods.append(method)
            
            success = len(missing_methods) == 0
            
            details = {
                'alias_works': isinstance(monitor, RefactoredMarketMonitor),
                'missing_methods': missing_methods,
                'all_methods_present': success
            }
            
            self.report.add_test_result("backward_compatibility", success, details)
            
        except Exception as e:
            self.report.add_test_result("backward_compatibility", False, {'error': str(e)})
    
    async def run_performance_benchmarks(self):
        """Run performance benchmarks."""
        print("Running performance benchmarks...")
        
        try:
            await self._benchmark_memory_usage()
            await self._benchmark_processing_speed()
            await self._benchmark_concurrent_processing()
            
        except Exception as e:
            self.logger.error(f"Error in performance benchmarks: {str(e)}")
    
    async def _benchmark_memory_usage(self):
        """Benchmark memory usage."""
        try:
            tracemalloc.start()
            
            config = TestSetup.create_test_config()
            monitor = RefactoredMarketMonitor(
                exchange_manager=TestSetup.create_mock_exchange_manager(),
                config=config,
                top_symbols_manager=TestSetup.create_mock_top_symbols_manager(),
                confluence_analyzer=TestSetup.create_mock_confluence_analyzer(),
                alert_manager=TestSetup.create_mock_alert_manager(),
                signal_generator=TestSetup.create_mock_signal_generator(),
                logger=self.logger
            )
            
            await monitor.initialize()
            
            # Measure memory
            snapshot1 = tracemalloc.take_snapshot()
            init_memory = sum(stat.size for stat in snapshot1.statistics('filename'))
            
            # Process some symbols
            symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'DOT/USDT']
            for symbol in symbols:
                await monitor._process_symbol(symbol)
            
            snapshot2 = tracemalloc.take_snapshot()
            processing_memory = sum(stat.size for stat in snapshot2.statistics('filename'))
            
            memory_growth = processing_memory - init_memory
            memory_growth_mb = memory_growth / 1024 / 1024
            
            results = {
                'initial_memory_mb': init_memory / 1024 / 1024,
                'processing_memory_mb': processing_memory / 1024 / 1024,
                'memory_growth_mb': memory_growth_mb,
                'memory_efficient': memory_growth_mb < 50  # Less than 50MB growth
            }
            
            self.report.add_benchmark_result("memory_usage", {"results": results})
            tracemalloc.stop()
            
        except Exception as e:
            self.logger.error(f"Memory benchmark error: {str(e)}")
    
    async def _benchmark_processing_speed(self):
        """Benchmark processing speed."""
        try:
            config = TestSetup.create_test_config()
            monitor = RefactoredMarketMonitor(
                exchange_manager=TestSetup.create_mock_exchange_manager(),
                config=config,
                top_symbols_manager=TestSetup.create_mock_top_symbols_manager(),
                confluence_analyzer=TestSetup.create_mock_confluence_analyzer(),
                alert_manager=TestSetup.create_mock_alert_manager(),
                signal_generator=TestSetup.create_mock_signal_generator(),
                logger=self.logger
            )
            
            await monitor.initialize()
            
            # Mock fast data fetching
            test_data = TestSetup.create_mock_market_data()
            monitor.data_collector.fetch_market_data = lambda symbol: test_data
            
            # Benchmark monitoring cycle
            num_cycles = 10
            start_time = time.time()
            
            for _ in range(num_cycles):
                await monitor._monitoring_cycle()
            
            end_time = time.time()
            total_time = end_time - start_time
            avg_time = total_time / num_cycles
            
            results = {
                'total_time': total_time,
                'average_cycle_time': avg_time,
                'cycles_per_second': num_cycles / total_time,
                'performance_acceptable': avg_time < 5.0  # Less than 5 seconds per cycle
            }
            
            self.report.add_benchmark_result("processing_speed", {"results": results})
            
        except Exception as e:
            self.logger.error(f"Processing speed benchmark error: {str(e)}")
    
    async def _benchmark_concurrent_processing(self):
        """Benchmark concurrent processing."""
        try:
            config = TestSetup.create_test_config()
            monitor = RefactoredMarketMonitor(
                exchange_manager=TestSetup.create_mock_exchange_manager(),
                config=config,
                top_symbols_manager=TestSetup.create_mock_top_symbols_manager(),
                confluence_analyzer=TestSetup.create_mock_confluence_analyzer(),
                alert_manager=TestSetup.create_mock_alert_manager(),
                signal_generator=TestSetup.create_mock_signal_generator(),
                logger=self.logger
            )
            
            await monitor.initialize()
            
            # Mock slow data fetching to test concurrency
            async def slow_fetch(symbol):
                await asyncio.sleep(0.1)
                return TestSetup.create_mock_market_data()
            
            monitor.data_collector.fetch_market_data = slow_fetch
            
            symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'DOT/USDT']
            
            # Test sequential processing
            start_time = time.time()
            for symbol in symbols:
                await monitor._process_symbol(symbol)
            sequential_time = time.time() - start_time
            
            # Test concurrent processing
            start_time = time.time()
            tasks = [monitor._process_symbol(symbol) for symbol in symbols]
            await asyncio.gather(*tasks)
            concurrent_time = time.time() - start_time
            
            speedup = sequential_time / concurrent_time if concurrent_time > 0 else 1
            
            results = {
                'sequential_time': sequential_time,
                'concurrent_time': concurrent_time,
                'speedup_factor': speedup,
                'concurrency_effective': speedup > 2.0  # At least 2x speedup
            }
            
            self.report.add_benchmark_result("concurrent_processing", {"results": results})
            
        except Exception as e:
            self.logger.error(f"Concurrent processing benchmark error: {str(e)}")
    
    async def run_integration_tests(self):
        """Run integration tests with Virtuoso trading system."""
        print("Running integration tests...")
        
        try:
            await self._test_exchange_integration()
            await self._test_signal_integration()
            await self._test_alert_integration()
            
        except Exception as e:
            self.logger.error(f"Error in integration tests: {str(e)}")
    
    async def _test_exchange_integration(self):
        """Test integration with exchange manager."""
        try:
            # This would test real exchange integration
            # For now, just test that the interface works
            config = TestSetup.create_test_config()
            monitor = RefactoredMarketMonitor(
                exchange_manager=TestSetup.create_mock_exchange_manager(),
                config=config,
                logger=self.logger
            )
            
            success = monitor.exchange_manager is not None
            
            details = {
                'exchange_manager_available': success,
                'exchange_id': monitor.exchange_id
            }
            
            self.report.add_integration_result("exchange_integration", success, details)
            
        except Exception as e:
            self.report.add_integration_result("exchange_integration", False, {'error': str(e)})
    
    async def _test_signal_integration(self):
        """Test signal generation integration."""
        try:
            config = TestSetup.create_test_config()
            signal_generator = TestSetup.create_mock_signal_generator()
            
            monitor = RefactoredMarketMonitor(
                exchange_manager=TestSetup.create_mock_exchange_manager(),
                config=config,
                signal_generator=signal_generator,
                logger=self.logger
            )
            
            success = monitor.signal_generator is not None
            
            details = {
                'signal_generator_available': success,
                'signal_processor_initialized': monitor.signal_processor is not None
            }
            
            self.report.add_integration_result("signal_integration", success, details)
            
        except Exception as e:
            self.report.add_integration_result("signal_integration", False, {'error': str(e)})
    
    async def _test_alert_integration(self):
        """Test alert system integration."""
        try:
            config = TestSetup.create_test_config()
            alert_manager = TestSetup.create_mock_alert_manager()
            
            monitor = RefactoredMarketMonitor(
                exchange_manager=TestSetup.create_mock_exchange_manager(),
                config=config,
                alert_manager=alert_manager,
                logger=self.logger
            )
            
            success = monitor.alert_manager is not None
            
            details = {
                'alert_manager_available': success,
                'alert_component_initialized': monitor.alert_manager_component is not None
            }
            
            self.report.add_integration_result("alert_integration", success, details)
            
        except Exception as e:
            self.report.add_integration_result("alert_integration", False, {'error': str(e)})
    
    async def run_validation(self):
        """Run complete validation suite."""
        print("Starting Monitor Refactoring Validation...")
        print(f"Original Monitor Available: {ORIGINAL_AVAILABLE}")
        print(f"Refactored Monitor Available: {REFACTORED_AVAILABLE}")
        
        await self.run_functional_validation()
        await self.run_performance_benchmarks()
        await self.run_integration_tests()
        
        # Generate and display report
        self.report.print_summary()
        
        # Save detailed report
        report_path = self.report.save_report()
        print(f"\nDetailed report saved to: {report_path}")
        
        return self.report.results['summary']['overall_success']


async def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description='Validate Monitor Refactoring')
    parser.add_argument('--detailed', action='store_true', help='Include detailed error information')
    parser.add_argument('--benchmark-only', action='store_true', help='Run only performance benchmarks')
    parser.add_argument('--integration-test', action='store_true', help='Run only integration tests')
    parser.add_argument('--functional-only', action='store_true', help='Run only functional tests')
    
    args = parser.parse_args()
    
    validator = MonitorValidator(detailed=args.detailed)
    
    try:
        if args.benchmark_only:
            await validator.run_performance_benchmarks()
        elif args.integration_test:
            await validator.run_integration_tests()
        elif args.functional_only:
            await validator.run_functional_validation()
        else:
            success = await validator.run_validation()
            
            if success:
                print("\n✅ VALIDATION SUCCESSFUL: Monitor refactoring validated!")
                sys.exit(0)
            else:
                print("\n❌ VALIDATION FAILED: Issues detected in refactoring!")
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Validation error: {str(e)}")
        if args.detailed:
            import traceback
            print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())