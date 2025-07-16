#!/usr/bin/env python3

import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

import asyncio
import logging
import subprocess
import time
from typing import List, Dict, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveBinanceTestSuite:
    """Comprehensive Binance integration test suite runner."""
    
    def __init__(self):
        self.test_scripts = [
            ('1', 'test_1_top_symbols_integration.py', '🔍 TopSymbolsManager Integration'),
            ('2', 'test_2_websocket_integration.py', '📡 WebSocket Integration'),
            ('3', 'test_3_alert_system_integration.py', '🚨 Alert System Integration'),
            ('4', 'test_4_multi_timeframe_data.py', '📊 Multi-Timeframe Data'),
            ('5', 'test_5_rate_limiting_circuit_breaker.py', '⚡ Rate Limiting & Circuit Breaker'),
            ('6', 'test_6_pdf_report_generation.py', '📄 PDF Report Generation'),
            ('7', 'test_7_production_environment.py', '🏭 Production Environment'),
            ('8', 'test_8_data_quality_cross_validation.py', '🔍 Data Quality Cross-Validation')
        ]
        self.results = {}
        
    def print_header(self):
        """Print test suite header."""
        print("\n" + "="*80)
        print("🚀 COMPREHENSIVE BINANCE INTEGRATION TEST SUITE")
        print("="*80)
        print("📋 Running 8 Critical Tests for Production Readiness")
        print(f"🕐 Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # List all tests
        for test_num, script, description in self.test_scripts:
            print(f"  TEST {test_num}: {description}")
        print("="*80)
    
    def run_test_script(self, test_num: str, script_name: str, description: str) -> Tuple[bool, float, str]:
        """Run a single test script and return results."""
        script_path = f"scripts/{script_name}"
        
        logger.info(f"\n🔄 RUNNING TEST {test_num}: {description}")
        logger.info(f"📄 Script: {script_name}")
        
        start_time = time.time()
        
        try:
            # Run the test script
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per test
            )
            
            duration = time.time() - start_time
            success = result.returncode == 0
            
            # Extract summary from output
            output_lines = result.stdout.split('\n')
            summary_lines = []
            capturing_summary = False
            
            for line in output_lines:
                if 'TEST SUMMARY' in line:
                    capturing_summary = True
                if capturing_summary:
                    summary_lines.append(line)
                if capturing_summary and ('Success Rate:' in line or 'integration is' in line):
                    break
            
            summary = '\n'.join(summary_lines) if summary_lines else "No summary available"
            
            # Log result
            status = "✅ PASSED" if success else "❌ FAILED"
            logger.info(f"{status} - Test {test_num} completed in {duration:.1f}s")
            
            if not success and result.stderr:
                logger.error(f"Error output: {result.stderr[:500]}")
            
            return success, duration, summary
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.error(f"⏰ TIMEOUT - Test {test_num} exceeded 5 minutes")
            return False, duration, "Test timed out after 5 minutes"
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"💥 ERROR - Test {test_num} failed with exception: {str(e)}")
            return False, duration, f"Exception: {str(e)}"
    
    def run_all_tests(self) -> Dict[str, Tuple[bool, float, str]]:
        """Run all tests in sequence."""
        logger.info("Starting comprehensive test suite...")
        
        for test_num, script, description in self.test_scripts:
            success, duration, summary = self.run_test_script(test_num, script, description)
            self.results[test_num] = (success, duration, summary, description)
            
            # Small delay between tests
            time.sleep(2)
        
        return self.results
    
    def generate_comprehensive_report(self):
        """Generate comprehensive test report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for success, _, _, _ in self.results.values() if success)
        total_duration = sum(duration for _, duration, _, _ in self.results.values())
        
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE BINANCE INTEGRATION TEST RESULTS")
        print("="*80)
        
        # Overall summary
        success_rate = (passed_tests / total_tests) * 100
        print(f"📈 Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests} tests passed)")
        print(f"⏱️ Total Execution Time: {total_duration:.1f} seconds")
        print(f"🕐 Completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n" + "-"*80)
        print("📋 DETAILED TEST RESULTS")
        print("-"*80)
        
        # Individual test results
        for test_num in sorted(self.results.keys()):
            success, duration, summary, description = self.results[test_num]
            status_icon = "✅" if success else "❌"
            status_text = "PASSED" if success else "FAILED"
            
            print(f"\n{status_icon} TEST {test_num}: {description}")
            print(f"   Status: {status_text}")
            print(f"   Duration: {duration:.1f}s")
            
            # Extract key metrics from summary
            if summary and "Success Rate:" in summary:
                for line in summary.split('\n'):
                    if "Success Rate:" in line:
                        print(f"   {line.strip()}")
                        break
        
        print("\n" + "-"*80)
        print("🎯 PRODUCTION READINESS ASSESSMENT")
        print("-"*80)
        
        # Categorize results
        critical_tests = ['1', '4', '7', '8']  # Core functionality
        performance_tests = ['2', '5']         # Performance related
        reporting_tests = ['3', '6']           # Reporting features
        
        critical_passed = sum(1 for test_num in critical_tests if self.results[test_num][0])
        performance_passed = sum(1 for test_num in performance_tests if self.results[test_num][0])
        reporting_passed = sum(1 for test_num in reporting_tests if self.results[test_num][0])
        
        print(f"🔧 Core Functionality: {critical_passed}/{len(critical_tests)} tests passed")
        print(f"⚡ Performance & Reliability: {performance_passed}/{len(performance_tests)} tests passed")
        print(f"📊 Reporting & Monitoring: {reporting_passed}/{len(reporting_tests)} tests passed")
        
        # Final recommendation
        print("\n" + "="*80)
        
        if success_rate >= 85 and critical_passed == len(critical_tests):
            print("🎉 RECOMMENDATION: READY FOR PRODUCTION")
            print("   ✅ All critical systems are functional")
            print("   ✅ Integration tests show high success rate")
            print("   ✅ Binance exchange integration is robust")
        elif success_rate >= 70 and critical_passed >= len(critical_tests) * 0.75:
            print("⚠️ RECOMMENDATION: READY WITH MONITORING")
            print("   ✅ Core functionality is working")
            print("   ⚠️ Some features need attention")
            print("   📊 Deploy with enhanced monitoring")
        elif success_rate >= 50:
            print("🔧 RECOMMENDATION: NEEDS FIXES BEFORE PRODUCTION")
            print("   ⚠️ Several critical issues detected")
            print("   🔧 Address failing tests before deployment")
            print("   📋 Focus on core functionality first")
        else:
            print("❌ RECOMMENDATION: NOT READY FOR PRODUCTION")
            print("   ❌ Major integration issues detected")
            print("   🚨 Requires significant development work")
            print("   🔄 Run tests again after fixes")
        
        print("="*80)
        
        return success_rate >= 70
    
    def save_results_to_file(self):
        """Save test results to file."""
        timestamp = int(time.time())
        filename = f"binance_integration_test_results_{timestamp}.txt"
        
        try:
            with open(filename, 'w') as f:
                f.write(f"Binance Integration Test Results\n")
                f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*50 + "\n\n")
                
                for test_num in sorted(self.results.keys()):
                    success, duration, summary, description = self.results[test_num]
                    status = "PASSED" if success else "FAILED"
                    
                    f.write(f"TEST {test_num}: {description}\n")
                    f.write(f"Status: {status}\n")
                    f.write(f"Duration: {duration:.1f}s\n")
                    f.write(f"Summary:\n{summary}\n")
                    f.write("-"*30 + "\n\n")
            
            logger.info(f"📁 Test results saved to: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save results to file: {str(e)}")

def main():
    """Main function to run comprehensive test suite."""
    suite = ComprehensiveBinanceTestSuite()
    
    # Print header
    suite.print_header()
    
    try:
        # Run all tests
        results = suite.run_all_tests()
        
        # Generate report
        is_ready = suite.generate_comprehensive_report()
        
        # Save results
        suite.save_results_to_file()
        
        # Exit with appropriate code
        sys.exit(0 if is_ready else 1)
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Test suite failed with error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 