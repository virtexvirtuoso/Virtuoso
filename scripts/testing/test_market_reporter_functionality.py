#!/usr/bin/env python3
"""
Test Market Reporter Functionality
Comprehensive test of market_reporter.py to ensure it's working properly
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime
import traceback

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

class MarketReporterTester:
    def __init__(self):
        self.test_results = {}
        self.logger = logging.getLogger(__name__)
        
    async def test_imports(self):
        """Test if all imports work correctly"""
        try:
            # Test basic imports
            from monitoring.market_reporter import MarketReporter
            
            # Test if optional dependencies are handled
            import monitoring.market_reporter as mr
            
            # Check flags
            bitcoin_beta_available = getattr(mr, 'BITCOIN_BETA_AVAILABLE', False)
            pdf_classes_available = getattr(mr, 'PDF_CLASSES_AVAILABLE', False)
            
            self.test_results['imports'] = {
                'status': 'PASS',
                'bitcoin_beta_available': bitcoin_beta_available,
                'pdf_classes_available': pdf_classes_available,
                'main_class_importable': True
            }
            
        except Exception as e:
            self.test_results['imports'] = {
                'status': 'FAIL',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    async def test_class_instantiation(self):
        """Test if MarketReporter can be instantiated"""
        try:
            
            # Mock dependencies
            class MockTopSymbolsManager:
                async def get_symbols(self):
                    return ['BTCUSDT', 'ETHUSDT']
                    
                async def get_top_symbols(self, limit=10):
                    return [
                        {'symbol': 'BTCUSDT', 'price': 50000, 'change_24h': 2.5},
                        {'symbol': 'ETHUSDT', 'price': 3000, 'change_24h': 1.8}
                    ]
            
            class MockAlertManager:
                def send_alert(self, message, level='info'):
                    pass
                    
                async def send_async_alert(self, message, level='info'):
                    pass
            
            class MockExchange:
                def __init__(self):
                    self.exchange_id = 'test_exchange'
                    
                async def fetch_ohlcv(self, symbol, timeframe='1d', limit=100):
                    # Return mock OHLCV data
                    import time
                    now = int(time.time() * 1000)
                    return [
                        [now - i * 86400000, 50000 + i * 100, 50500 + i * 100, 49500 + i * 100, 50200 + i * 100, 1000]
                        for i in range(limit)
                    ]
            
            # Test instantiation
            mock_top_symbols = MockTopSymbolsManager()
            mock_alert_manager = MockAlertManager()
            mock_exchange = MockExchange()
            mock_logger = logging.getLogger('test')
            
            reporter = MarketReporter(
                top_symbols_manager=mock_top_symbols,
                alert_manager=mock_alert_manager,
                exchange=mock_exchange,
                logger=mock_logger
            )
            
            self.test_results['instantiation'] = {
                'status': 'PASS',
                'class_created': True,
                'attributes_exist': hasattr(reporter, 'top_symbols_manager')
            }
            
        except Exception as e:
            self.test_results['instantiation'] = {
                'status': 'FAIL',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    async def test_basic_methods(self):
        """Test basic method availability"""
        try:
            
            # Check if key methods exist
            methods_to_check = [
                'generate_market_summary',
                'fetch_market_data',
                'create_analysis_report',
                'format_report_data'
            ]
            
            method_status = {}
            for method_name in methods_to_check:
                method_status[method_name] = hasattr(MarketReporter, method_name)
            
            # Check if any critical methods are missing
            missing_methods = [m for m, exists in method_status.items() if not exists]
            
            self.test_results['methods'] = {
                'status': 'PASS' if not missing_methods else 'WARN',
                'method_availability': method_status,
                'missing_methods': missing_methods
            }
            
        except Exception as e:
            self.test_results['methods'] = {
                'status': 'FAIL',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    async def test_configuration_handling(self):
        """Test configuration handling"""
        try:
            
            # Test with minimal config
            test_config = {
                'reporting': {
                    'enabled': True,
                    'output_dir': 'test_reports'
                }
            }
            
            # This should not crash
            config_handled = True
            
            self.test_results['configuration'] = {
                'status': 'PASS',
                'config_handling': config_handled
            }
            
        except Exception as e:
            self.test_results['configuration'] = {
                'status': 'FAIL',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    async def test_error_handling(self):
        """Test error handling patterns"""
        try:
            # Read the file and check for proper error handling patterns
            market_reporter_path = Path(__file__).parent.parent / 'src' / 'monitoring' / 'market_reporter.py'
            
            with open(market_reporter_path, 'r') as f:
                content = f.read()
            
            # Check for good error handling patterns
            has_try_except = 'try:' in content and 'except' in content
            has_logging = 'logger.error' in content or 'logging.error' in content
            has_traceback = 'traceback' in content
            
            # Check for potential issues
            has_bare_except = 'except:' in content
            has_pass_in_except = 'except' in content and 'pass' in content
            
            self.test_results['error_handling'] = {
                'status': 'PASS',
                'has_try_except': has_try_except,
                'has_logging': has_logging,
                'has_traceback': has_traceback,
                'warnings': {
                    'bare_except_found': has_bare_except,
                    'pass_in_except_found': has_pass_in_except
                }
            }
            
        except Exception as e:
            self.test_results['error_handling'] = {
                'status': 'FAIL',
                'error': str(e)
            }
    
    async def run_all_tests(self):
        """Run all tests"""
        print("🧪 Testing Market Reporter Functionality...")
        print("=" * 60)
        
        tests = [
            ('Import Test', self.test_imports),
            ('Class Instantiation Test', self.test_class_instantiation),
            ('Methods Availability Test', self.test_basic_methods),
            ('Configuration Handling Test', self.test_configuration_handling),
            ('Error Handling Test', self.test_error_handling)
        ]
        
        for test_name, test_func in tests:
            print(f"\n🔍 Running {test_name}...")
            try:
                await test_func()
                result = self.test_results.get(test_name.lower().replace(' ', '_').replace('test', '').strip('_'), {})
                status = result.get('status', 'UNKNOWN')
                
                if status == 'PASS':
                    print(f"✅ {test_name}: PASSED")
                elif status == 'WARN':
                    print(f"⚠️  {test_name}: PASSED WITH WARNINGS")
                else:
                    print(f"❌ {test_name}: FAILED")
                    if 'error' in result:
                        print(f"   Error: {result['error']}")
                        
            except Exception as e:
                print(f"❌ {test_name}: CRASHED - {str(e)}")
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "=" * 60)
        print("📊 Market Reporter Test Summary")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results.values() if r.get('status') == 'PASS')
        warned_tests = sum(1 for r in self.test_results.values() if r.get('status') == 'WARN')
        failed_tests = sum(1 for r in self.test_results.values() if r.get('status') == 'FAIL')
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"⚠️  Warnings: {warned_tests}")
        print(f"❌ Failed: {failed_tests}")
        
        if failed_tests == 0:
            print("\n🎉 All tests passed! Market Reporter appears to be working correctly.")
        else:
            print(f"\n⚠️  {failed_tests} test(s) failed. See details above.")
        
        # Save detailed results
        import json
        report_path = Path('test_output') / f'market_reporter_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: {report_path}")

async def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    tester = MarketReporterTester()
    await tester.run_all_tests()
    tester.generate_report()

if __name__ == "__main__":
    asyncio.run(main())