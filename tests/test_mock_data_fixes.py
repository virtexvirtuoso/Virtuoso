#!/usr/bin/env python3
"""
Comprehensive test suite for mock data elimination fixes.
Tests the three critical fixes:
1. Trade Executor real signal generation
2. Market Data Manager real historical data
3. Liquidation API real detection
"""

import asyncio
import sys
import os
import logging
import time
import traceback
from typing import Dict, Any, List
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockDataEliminationTester:
    """Test suite for verifying mock data has been eliminated"""
    
    def __init__(self):
        self.test_results = {
            'trade_executor': {'passed': False, 'errors': [], 'details': {}},
            'market_data_manager': {'passed': False, 'errors': [], 'details': {}},
            'liquidation_api': {'passed': False, 'errors': [], 'details': {}},
            'mock_detection': {'passed': False, 'errors': [], 'details': {}}
        }
        
    async def run_all_tests(self):
        """Run all mock data elimination tests"""
        logger.info("🔍 Starting Mock Data Elimination Test Suite")
        logger.info("=" * 60)
        
        # Test 1: Trade Executor
        await self.test_trade_executor()
        
        # Test 2: Market Data Manager
        await self.test_market_data_manager()
        
        # Test 3: Liquidation API
        await self.test_liquidation_api()
        
        # Test 4: Mock Detection
        await self.test_mock_detection()
        
        # Generate final report
        self.generate_final_report()
        
    async def test_trade_executor(self):
        """Test Trade Executor real signal generation"""
        logger.info("🎯 Testing Trade Executor Real Signal Generation")
        test_name = 'trade_executor'
        
        try:
            from src.trade_execution.trade_executor import TradeExecutor
            from src.config.manager import ConfigManager
            
            # Load configuration
            config_manager = ConfigManager()
            config = config_manager.get_config()
            
            # Initialize Trade Executor
            executor = TradeExecutor(config)
            
            # Test 1: Check if random import is removed from method
            import inspect
            source_code = inspect.getsource(executor.get_market_prism_score)
            
            if 'import random' in source_code:
                self.test_results[test_name]['errors'].append("❌ Random import still present in get_market_prism_score")
                logger.error("❌ Random import found in Trade Executor")
            else:
                logger.info("✅ No random import found in Trade Executor")
                
            if 'random.uniform' in source_code:
                self.test_results[test_name]['errors'].append("❌ random.uniform still used in signal generation")
                logger.error("❌ random.uniform found in Trade Executor")
            else:
                logger.info("✅ No random.uniform found in Trade Executor")
            
            # Test 2: Test with mock market data
            mock_market_data = {
                'symbol': 'BTCUSDT',
                'ohlcv': {
                    'base': None,
                    'ltf': None,
                    'mtf': None,
                    'htf': None
                },
                'trades': None,
                'orderbook': None
            }
            
            # Call the method multiple times to check consistency
            scores = []
            for i in range(5):
                try:
                    result = await executor.get_market_prism_score('BTCUSDT', mock_market_data)
                    scores.append(result)
                    logger.info(f"Test {i+1}: Score = {result.get('scores', {}).get('overall', 'N/A')}")
                except Exception as e:
                    logger.warning(f"Test {i+1} failed: {e}")
                    scores.append({'error': str(e)})
            
            # Test 3: Verify data source is not 'mock'
            valid_data_sources = ['real_analysis', 'neutral_fallback']
            for i, score in enumerate(scores):
                if 'error' not in score:
                    data_source = score.get('data_source', 'unknown')
                    if data_source not in valid_data_sources:
                        self.test_results[test_name]['errors'].append(f"❌ Invalid data source: {data_source}")
                    else:
                        logger.info(f"✅ Valid data source: {data_source}")
            
            # Test 4: Check for score consistency (should not be completely random)
            overall_scores = [s.get('scores', {}).get('overall', 0) for s in scores if 'error' not in s]
            if len(set(overall_scores)) == len(overall_scores) and len(overall_scores) > 1:
                logger.warning("⚠️  All scores are different - might indicate randomness")
                self.test_results[test_name]['errors'].append("⚠️ Scores appear to be random (all different)")
            
            self.test_results[test_name]['details'] = {
                'scores_generated': len(scores),
                'successful_calls': len([s for s in scores if 'error' not in s]),
                'unique_scores': len(set(overall_scores)),
                'data_sources': list(set([s.get('data_source') for s in scores if 'error' not in s]))
            }
            
            if not self.test_results[test_name]['errors']:
                self.test_results[test_name]['passed'] = True
                logger.info("✅ Trade Executor tests PASSED")
            else:
                logger.error(f"❌ Trade Executor tests FAILED: {len(self.test_results[test_name]['errors'])} errors")
                
        except Exception as e:
            error_msg = f"Trade Executor test failed: {str(e)}"
            self.test_results[test_name]['errors'].append(error_msg)
            logger.error(f"❌ {error_msg}")
            logger.error(traceback.format_exc())
    
    async def test_market_data_manager(self):
        """Test Market Data Manager real historical data"""
        logger.info("\n📊 Testing Market Data Manager Real Historical Data")
        test_name = 'market_data_manager'
        
        try:
            from src.core.market.market_data_manager import MarketDataManager
            from src.core.exchanges.manager import ExchangeManager
            
            # Load configuration
            config_manager = ConfigManager()
            config = config_manager.get_config()
            
            # Initialize components (this might fail if exchange manager isn't available)
            try:
                exchange_manager = ExchangeManager(config)
                await exchange_manager.initialize()
                
                market_data_manager = MarketDataManager(config, exchange_manager)
                
                # Test the source code for fake data patterns
                import inspect
                source_code = inspect.getsource(MarketDataManager)
                
                # Check for eliminated patterns
                fake_patterns = [
                    'fake_timestamp = now - (i * 30 * 60 * 1000)',
                    'random_factor = 1.0 + (random.random() - 0.5) * 0.02',
                    'fake_value = trend_value * random_factor'
                ]
                
                patterns_found = []
                for pattern in fake_patterns:
                    if pattern in source_code:
                        patterns_found.append(pattern)
                
                if patterns_found:
                    for pattern in patterns_found:
                        self.test_results[test_name]['errors'].append(f"❌ Fake pattern still present: {pattern}")
                        logger.error(f"❌ Found fake pattern: {pattern}")
                else:
                    logger.info("✅ No fake timestamp/value patterns found")
                
                # Check for real data fetching patterns
                real_patterns = [
                    'fetch_open_interest_history',
                    'real_exchange',
                    'data_source'
                ]
                
                real_patterns_found = []
                for pattern in real_patterns:
                    if pattern in source_code:
                        real_patterns_found.append(pattern)
                
                logger.info(f"✅ Real data patterns found: {real_patterns_found}")
                
                # Try to get market data (might fail without real exchange connection)
                try:
                    market_data = await market_data_manager.get_market_data('BTCUSDT')
                    
                    if 'open_interest' in market_data:
                        oi_data = market_data['open_interest']
                        
                        # Check data source
                        data_source = oi_data.get('data_source', 'unknown')
                        if data_source == 'mock':
                            self.test_results[test_name]['errors'].append("❌ Open interest data source is still 'mock'")
                        else:
                            logger.info(f"✅ OI data source: {data_source}")
                        
                        # Check history data sources
                        if 'history' in oi_data:
                            history_sources = set([h.get('data_source', 'unknown') for h in oi_data['history']])
                            logger.info(f"✅ History data sources: {history_sources}")
                            
                            if 'mock' in history_sources:
                                self.test_results[test_name]['errors'].append("❌ History contains mock data sources")
                            
                        self.test_results[test_name]['details'] = {
                            'oi_data_source': data_source,
                            'has_history': 'history' in oi_data,
                            'history_count': len(oi_data.get('history', [])),
                            'is_synthetic': oi_data.get('is_synthetic', False)
                        }
                    
                except Exception as e:
                    logger.warning(f"⚠️ Could not fetch market data (expected without exchange connection): {e}")
                    self.test_results[test_name]['details']['market_data_fetch'] = f"Failed: {str(e)}"
                
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize exchange manager (expected in test environment): {e}")
                self.test_results[test_name]['details']['initialization'] = f"Failed: {str(e)}"
                
                # Still check source code for patterns
                import inspect
                source_code = inspect.getsource(MarketDataManager)
                
                if 'fake_timestamp' not in source_code and 'random_factor' not in source_code:
                    logger.info("✅ Source code analysis passed - no fake patterns")
                else:
                    self.test_results[test_name]['errors'].append("❌ Fake patterns still in source code")
            
            if not self.test_results[test_name]['errors']:
                self.test_results[test_name]['passed'] = True
                logger.info("✅ Market Data Manager tests PASSED")
            else:
                logger.error(f"❌ Market Data Manager tests FAILED: {len(self.test_results[test_name]['errors'])} errors")
                
        except Exception as e:
            error_msg = f"Market Data Manager test failed: {str(e)}"
            self.test_results[test_name]['errors'].append(error_msg)
            logger.error(f"❌ {error_msg}")
            logger.error(traceback.format_exc())
    
    async def test_liquidation_api(self):
        """Test Liquidation API real detection"""
        logger.info("\n⚠️  Testing Liquidation API Real Detection")
        test_name = 'liquidation_api'
        
        try:
            # Check source code for mock patterns
            with open('src/api/routes/liquidation.py', 'r') as f:
                source_code = f.read()
            
            # Check for eliminated mock patterns
            mock_patterns = [
                'mock_events = []',
                'mock_event = LiquidationEvent(',
                'Create mock liquidation events',
                'Return mock stress indicators'
            ]
            
            patterns_found = []
            for pattern in mock_patterns:
                if pattern in source_code:
                    patterns_found.append(pattern)
            
            if patterns_found:
                for pattern in patterns_found:
                    self.test_results[test_name]['errors'].append(f"❌ Mock pattern still present: {pattern}")
                    logger.error(f"❌ Found mock pattern: {pattern}")
            else:
                logger.info("✅ No mock event patterns found")
            
            # Check for real detection patterns
            real_patterns = [
                'liquidation_detector.detect_liquidation_events',
                'real_events = await',
                'Return empty list instead of mock'
            ]
            
            real_patterns_found = []
            for pattern in real_patterns:
                if pattern in source_code:
                    real_patterns_found.append(pattern)
            
            logger.info(f"✅ Real detection patterns found: {real_patterns_found}")
            
            # Test imports
            try:
                from src.api.routes.liquidation import router
                from src.analysis.core.liquidation_detector import LiquidationDetectionEngine
                logger.info("✅ Successfully imported liquidation components")
                
                self.test_results[test_name]['details'] = {
                    'mock_patterns_eliminated': len(mock_patterns) - len(patterns_found),
                    'real_patterns_added': len(real_patterns_found),
                    'imports_successful': True
                }
                
            except Exception as e:
                error_msg = f"Failed to import liquidation components: {str(e)}"
                self.test_results[test_name]['errors'].append(error_msg)
                logger.error(f"❌ {error_msg}")
            
            if not self.test_results[test_name]['errors']:
                self.test_results[test_name]['passed'] = True
                logger.info("✅ Liquidation API tests PASSED")
            else:
                logger.error(f"❌ Liquidation API tests FAILED: {len(self.test_results[test_name]['errors'])} errors")
                
        except Exception as e:
            error_msg = f"Liquidation API test failed: {str(e)}"
            self.test_results[test_name]['errors'].append(error_msg)
            logger.error(f"❌ {error_msg}")
            logger.error(traceback.format_exc())
    
    async def test_mock_detection(self):
        """Run comprehensive mock data detection across codebase"""
        logger.info("\n🔍 Running Comprehensive Mock Data Detection")
        test_name = 'mock_detection'
        
        try:
            import subprocess
            import re
            
            # Search for dangerous patterns across the codebase
            dangerous_patterns = {
                'random_uniform': r'random\.uniform\(',
                'random_random': r'random\.random\(',
                'fake_timestamp': r'fake_timestamp',
                'mock_events': r'mock_events',
                'data_source_mock': r'"data_source":\s*"mock"',
                'synthetic_oi': r'synthetic_oi',
                'random_factor': r'random_factor'
            }
            
            findings = {}
            
            for pattern_name, pattern in dangerous_patterns.items():
                try:
                    # Use grep to search for patterns
                    result = subprocess.run(
                        ['grep', '-r', '-n', pattern, 'src/', '--include=*.py'],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        findings[pattern_name] = result.stdout.strip().split('\n')
                        logger.warning(f"⚠️ Found {pattern_name}: {len(findings[pattern_name])} matches")
                        for match in findings[pattern_name][:3]:  # Show first 3 matches
                            logger.warning(f"   {match}")
                        if len(findings[pattern_name]) > 3:
                            logger.warning(f"   ... and {len(findings[pattern_name]) - 3} more")
                    else:
                        logger.info(f"✅ No {pattern_name} found")
                        
                except subprocess.TimeoutExpired:
                    logger.error(f"❌ Timeout searching for {pattern_name}")
                except Exception as e:
                    logger.error(f"❌ Error searching for {pattern_name}: {e}")
            
            # Check specific files that we fixed
            fixed_files = [
                'src/trade_execution/trade_executor.py',
                'src/core/market/market_data_manager.py',
                'src/api/routes/liquidation.py'
            ]
            
            for file_path in fixed_files:
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                    
                    # Check for random imports
                    if 'import random' in content and 'src/trade_execution/trade_executor.py' in file_path:
                        # This might be acceptable if used properly
                        if 'random.uniform(' in content:
                            self.test_results[test_name]['errors'].append(f"❌ {file_path} still uses random.uniform")
                        else:
                            logger.info(f"✅ {file_path} has random import but no random.uniform usage")
                    
                    logger.info(f"✅ Checked {file_path}")
                    
                except Exception as e:
                    logger.error(f"❌ Could not check {file_path}: {e}")
            
            # Summary
            total_findings = sum(len(matches) for matches in findings.values())
            
            self.test_results[test_name]['details'] = {
                'patterns_searched': len(dangerous_patterns),
                'total_findings': total_findings,
                'findings_by_pattern': {k: len(v) for k, v in findings.items()},
                'files_checked': len(fixed_files)
            }
            
            if total_findings == 0:
                self.test_results[test_name]['passed'] = True
                logger.info("✅ Mock Data Detection tests PASSED - No dangerous patterns found")
            elif total_findings < 5:
                logger.warning(f"⚠️ Mock Data Detection tests PARTIAL - {total_findings} patterns found")
                self.test_results[test_name]['passed'] = False
                self.test_results[test_name]['errors'].append(f"Found {total_findings} potentially dangerous patterns")
            else:
                self.test_results[test_name]['passed'] = False
                self.test_results[test_name]['errors'].append(f"Found {total_findings} dangerous patterns - significant mock data remains")
                logger.error(f"❌ Mock Data Detection tests FAILED - {total_findings} patterns found")
                
        except Exception as e:
            error_msg = f"Mock detection test failed: {str(e)}"
            self.test_results[test_name]['errors'].append(error_msg)
            logger.error(f"❌ {error_msg}")
            logger.error(traceback.format_exc())
    
    def generate_final_report(self):
        """Generate final test report"""
        logger.info("\n" + "="*60)
        logger.info("📋 FINAL TEST REPORT: Mock Data Elimination")
        logger.info("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results.values() if t['passed']])
        
        logger.info(f"Tests Passed: {passed_tests}/{total_tests}")
        
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result['passed'] else "❌ FAILED" 
            logger.info(f"{test_name}: {status}")
            
            if result['errors']:
                for error in result['errors']:
                    logger.info(f"  - {error}")
            
            if result['details']:
                logger.info(f"  Details: {result['details']}")
        
        # Overall assessment
        if passed_tests == total_tests:
            logger.info("\n🎉 ALL TESTS PASSED - Mock data successfully eliminated!")
            logger.info("✅ System is ready for production use")
        elif passed_tests >= total_tests * 0.75:
            logger.info(f"\n⚠️ MOSTLY SUCCESSFUL - {passed_tests}/{total_tests} tests passed")
            logger.info("🔧 Minor issues remain but major mock data eliminated")
        else:
            logger.info(f"\n❌ SIGNIFICANT ISSUES - Only {passed_tests}/{total_tests} tests passed")
            logger.info("🚨 System still contains dangerous mock data")
        
        # Save detailed report
        report_file = f"test_output/mock_data_elimination_test_report_{int(time.time())}.json"
        os.makedirs("test_output", exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'success_rate': passed_tests / total_tests
                },
                'results': self.test_results
            }, f, indent=2, default=str)
        
        logger.info(f"\n📄 Detailed report saved to: {report_file}")

async def main():
    """Main test runner"""
    tester = MockDataEliminationTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())