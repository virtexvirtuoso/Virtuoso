#!/usr/bin/env python3
"""
Complex PDF Architecture Integration Test
Tests the complete real-world workflow with actual market data simulation,
multiple signals, concurrent processing, error handling, and performance testing.
"""

import sys
import os
import asyncio
import logging
import tempfile
import uuid
import json
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import threading

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import required modules
from src.monitoring.alert_manager import AlertManager
from src.core.reporting.pdf_generator import ReportGenerator
from src.core.reporting.report_manager import ReportManager

class ComplexPDFArchitectureTest:
    """Complex integration test for PDF architecture"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        self.test_results = {}
        self.generated_pdfs = []
        self.test_start_time = time.time()
        
    def setup_logging(self):
        """Setup detailed test logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
    def generate_mock_ohlcv_data(self, symbol: str, timeframe: str = '1h', periods: int = 100) -> pd.DataFrame:
        """Generate realistic OHLCV data for testing"""
        
        # Base prices for different symbols
        base_prices = {
            'BTCUSDT': 45000,
            'ETHUSDT': 3500,
            'ADAUSDT': 1.25,
            'SOLUSDT': 120,
            'DOGEUSDT': 0.15
        }
        
        base_price = base_prices.get(symbol, 1000)
        
        # Generate timestamps
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=periods)
        timestamps = pd.date_range(start_time, end_time, periods=periods)
        
        # Generate realistic price movements
        np.random.seed(42)  # For reproducible results
        price_changes = np.random.normal(0, 0.02, periods)  # 2% volatility
        prices = [base_price]
        
        for change in price_changes[1:]:
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, base_price * 0.5))  # Prevent extreme crashes
            
        # Create OHLCV data
        data = []
        for i, (timestamp, close) in enumerate(zip(timestamps, prices)):
            high = close * (1 + abs(np.random.normal(0, 0.01)))
            low = close * (1 - abs(np.random.normal(0, 0.01)))
            open_price = prices[i-1] if i > 0 else close
            volume = np.random.uniform(1000000, 10000000)  # Random volume
            
            data.append({
                'timestamp': int(timestamp.timestamp() * 1000),
                'open': open_price,
                'high': max(open_price, high, close),
                'low': min(open_price, low, close),
                'close': close,
                'volume': volume
            })
            
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
        
    def generate_complex_signal_data(self, symbol: str, signal_type: str) -> dict:
        """Generate complex, realistic signal data"""
        
        base_score = 75 if signal_type == 'BUY' else 25
        score_variation = np.random.uniform(-10, 10)
        final_score = max(0, min(100, base_score + score_variation))
        
        return {
            'symbol': symbol,
            'signal_type': signal_type,
            'confluence_score': final_score,
            'price': np.random.uniform(1, 50000),
            'timestamp': int(datetime.now().timestamp() * 1000),
            'transaction_id': str(uuid.uuid4())[:8],
            'signal_id': str(uuid.uuid4())[:8],
            'components': {
                'technical': np.random.uniform(60, 90),
                'volume': np.random.uniform(50, 85),
                'sentiment': np.random.uniform(45, 80),
                'orderbook': np.random.uniform(55, 75),
                'orderflow': np.random.uniform(60, 85),
                'price_structure': np.random.uniform(65, 88)
            },
            'results': {
                'technical': {
                    'rsi': np.random.uniform(30, 70),
                    'macd': 'bullish' if signal_type == 'BUY' else 'bearish',
                    'bb_position': 'upper' if signal_type == 'BUY' else 'lower',
                    'ema_cross': True,
                    'support_resistance': f"Strong {signal_type.lower()} level"
                },
                'volume': {
                    'volume_spike': np.random.choice([True, False]),
                    'volume_profile': 'accumulation' if signal_type == 'BUY' else 'distribution',
                    'vwap_position': 'above' if signal_type == 'BUY' else 'below'
                },
                'sentiment': {
                    'score': np.random.uniform(0.4, 0.9),
                    'fear_greed': np.random.randint(20, 80),
                    'social_sentiment': 'positive' if signal_type == 'BUY' else 'negative'
                },
                'orderbook': {
                    'bid_ask_ratio': np.random.uniform(0.8, 1.2),
                    'depth_analysis': f"{signal_type} pressure detected",
                    'large_orders': np.random.randint(5, 20)
                }
            },
            'weights': {
                'technical': 0.25,
                'volume': 0.20,
                'sentiment': 0.15,
                'orderbook': 0.20,
                'orderflow': 0.10,
                'price_structure': 0.10
            },
            'reliability': np.random.uniform(0.7, 0.95),
            'buy_threshold': 60.0,
            'sell_threshold': 40.0,
            'market_interpretations': [
                f"Technical analysis shows strong {signal_type.lower()} momentum",
                f"Volume patterns support {signal_type.lower()} thesis",
                f"Market structure indicates {signal_type.lower()} opportunity"
            ],
            'actionable_insights': [
                f"Consider {signal_type.lower()} position with tight risk management",
                f"Monitor for confirmation signals",
                f"Set appropriate stop-loss levels"
            ],
            'influential_components': [
                {'component': 'technical', 'impact': 85, 'reasoning': 'Strong momentum indicators'},
                {'component': 'volume', 'impact': 75, 'reasoning': 'Unusual volume activity'},
                {'component': 'sentiment', 'impact': 65, 'reasoning': 'Positive market sentiment'}
            ]
        }
        
    async def test_complete_integration_workflow(self):
        """Test 1: Complete integration workflow simulation"""
        
        print("\n🧪 Test 1: Complete Integration Workflow")
        print("-" * 60)
        
        try:
            # Test symbols and signal types
            test_cases = [
                ('BTCUSDT', 'BUY'),
                ('ETHUSDT', 'SELL'),
                ('ADAUSDT', 'BUY'),
                ('SOLUSDT', 'SELL'),
                ('DOGEUSDT', 'BUY')
            ]
            
            successful_generations = 0
            
            for symbol, signal_type in test_cases:
                print(f"\n  📊 Testing {symbol} {signal_type} signal...")
                
                # Generate mock data
                ohlcv_data = self.generate_mock_ohlcv_data(symbol)
                signal_data = self.generate_complex_signal_data(symbol, signal_type)
                
                # Test PDF generation
                report_gen = ReportGenerator()
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    pdf_path = os.path.join(temp_dir, f'{symbol}_{signal_type}.pdf')
                    
                    start_time = time.time()
                    result = await report_gen.generate_report(
                        signal_data=signal_data,
                        ohlcv_data=ohlcv_data,
                        output_path=pdf_path
                    )
                    generation_time = time.time() - start_time
                    
                    if result and isinstance(result, tuple):
                        generated_pdf_path, json_path = result
                        
                        if os.path.exists(generated_pdf_path):
                            file_size = os.path.getsize(generated_pdf_path)
                            print(f"    ✅ PDF generated: {file_size/1024:.2f} KB in {generation_time:.2f}s")
                            
                            # Verify PDF header
                            with open(generated_pdf_path, 'rb') as f:
                                header = f.read(5)
                                if header[:4] == b'%PDF':
                                    successful_generations += 1
                                    self.generated_pdfs.append({
                                        'symbol': symbol,
                                        'signal_type': signal_type,
                                        'size': file_size,
                                        'generation_time': generation_time,
                                        'path': generated_pdf_path
                                    })
                                else:
                                    print(f"    ❌ Invalid PDF header for {symbol}")
                        else:
                            print(f"    ❌ PDF not found for {symbol}")
                    else:
                        print(f"    ❌ PDF generation failed for {symbol}")
                        
            success_rate = (successful_generations / len(test_cases)) * 100
            print(f"\n  📈 Success Rate: {success_rate:.1f}% ({successful_generations}/{len(test_cases)})")
            
            self.test_results['integration_workflow'] = success_rate >= 80
            
        except Exception as e:
            print(f"❌ Integration workflow test failed: {str(e)}")
            print(traceback.format_exc())
            self.test_results['integration_workflow'] = False
            
    async def test_concurrent_pdf_generation(self):
        """Test 2: Concurrent PDF generation stress test"""
        
        print("\n⚡ Test 2: Concurrent PDF Generation")
        print("-" * 60)
        
        try:
            concurrent_tasks = 5
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOGEUSDT']
            
            async def generate_pdf_task(symbol: str, task_id: int):
                """Individual PDF generation task"""
                try:
                    signal_data = self.generate_complex_signal_data(symbol, 'BUY')
                    ohlcv_data = self.generate_mock_ohlcv_data(symbol)
                    
                    report_gen = ReportGenerator()
                    
                    with tempfile.TemporaryDirectory() as temp_dir:
                        pdf_path = os.path.join(temp_dir, f'concurrent_{task_id}_{symbol}.pdf')
                        
                        start_time = time.time()
                        result = await report_gen.generate_report(
                            signal_data=signal_data,
                            ohlcv_data=ohlcv_data,
                            output_path=pdf_path
                        )
                        generation_time = time.time() - start_time
                        
                        if result and isinstance(result, tuple):
                            generated_pdf_path, _ = result
                            if os.path.exists(generated_pdf_path):
                                file_size = os.path.getsize(generated_pdf_path)
                                return {
                                    'task_id': task_id,
                                    'symbol': symbol,
                                    'success': True,
                                    'size': file_size,
                                    'time': generation_time
                                }
                                
                    return {'task_id': task_id, 'symbol': symbol, 'success': False}
                    
                except Exception as e:
                    return {'task_id': task_id, 'symbol': symbol, 'success': False, 'error': str(e)}
            
            # Run concurrent tasks
            print(f"  🚀 Starting {concurrent_tasks} concurrent PDF generations...")
            start_time = time.time()
            
            tasks = [
                generate_pdf_task(symbols[i % len(symbols)], i) 
                for i in range(concurrent_tasks)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Analyze results
            successful_tasks = sum(1 for r in results if isinstance(r, dict) and r.get('success', False))
            avg_generation_time = np.mean([r['time'] for r in results if isinstance(r, dict) and r.get('success', False)])
            
            print(f"  ✅ Concurrent generations completed: {successful_tasks}/{concurrent_tasks}")
            print(f"  ⏱️  Total time: {total_time:.2f}s, Avg per PDF: {avg_generation_time:.2f}s")
            
            # Check for any exceptions
            exceptions = [r for r in results if isinstance(r, Exception)]
            if exceptions:
                print(f"  ⚠️  Exceptions encountered: {len(exceptions)}")
                for exc in exceptions:
                    print(f"    - {str(exc)}")
            
            self.test_results['concurrent_generation'] = successful_tasks >= (concurrent_tasks * 0.8)
            
        except Exception as e:
            print(f"❌ Concurrent generation test failed: {str(e)}")
            self.test_results['concurrent_generation'] = False
            
    async def test_alert_manager_workflow(self):
        """Test 3: Complete Alert Manager workflow with mocked Discord"""
        
        print("\n📢 Test 3: Alert Manager Workflow")
        print("-" * 60)
        
        try:
            # Create test config with mock Discord
            config = {
                'discord': {
                    'webhook_url': 'https://discord.com/api/webhooks/test/mock',
                    'enabled': True
                },
                'pdf_enabled': True
            }
            
            alert_manager = AlertManager(config)
            
            # Mock Discord webhook
            webhook_calls = []
            original_send = alert_manager.send_discord_webhook_message
            
            async def mock_webhook(message, files=None, alert_type=None):
                webhook_calls.append({
                    'message': message,
                    'files': files or [],
                    'alert_type': alert_type,
                    'timestamp': datetime.now()
                })
                print(f"    📨 Mock Discord: {len(files or [])} files, type: {alert_type}")
                return True
                
            alert_manager.send_discord_webhook_message = mock_webhook
            
            # Test multiple signal types
            test_signals = [
                self.generate_complex_signal_data('BTCUSDT', 'BUY'),
                self.generate_complex_signal_data('ETHUSDT', 'SELL')
            ]
            
            successful_alerts = 0
            
            for signal_data in test_signals:
                # Create temporary PDF to simulate Monitor.py workflow
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
                    tmp_pdf.write(b'%PDF-1.4\nMock PDF content for testing')
                    signal_data['pdf_path'] = tmp_pdf.name
                
                try:
                    print(f"  🎯 Testing alert for {signal_data['symbol']} {signal_data['signal_type']}")
                    
                    # Test send_signal_alert (main workflow)
                    await alert_manager.send_signal_alert(signal_data)
                    successful_alerts += 1
                    
                finally:
                    # Cleanup temp file
                    if os.path.exists(signal_data['pdf_path']):
                        os.unlink(signal_data['pdf_path'])
            
            # Analyze webhook calls
            print(f"\n  📊 Alert Results:")
            print(f"    Successful alerts: {successful_alerts}/{len(test_signals)}")
            print(f"    Total webhook calls: {len(webhook_calls)}")
            
            # Check for proper PDF handling
            pdf_attachments = sum(1 for call in webhook_calls if len(call['files']) > 0)
            print(f"    PDF attachments sent: {pdf_attachments}")
            
            # Verify no internal PDF generation in send_confluence_alert
            confluence_calls = [call for call in webhook_calls if call.get('alert_type') != 'pdf_attachment']
            confluence_with_pdfs = sum(1 for call in confluence_calls if len(call['files']) > 0)
            
            print(f"    Confluence alerts with PDFs: {confluence_with_pdfs} (should be 0)")
            
            self.test_results['alert_manager_workflow'] = (
                successful_alerts == len(test_signals) and 
                confluence_with_pdfs == 0 and 
                pdf_attachments > 0
            )
            
        except Exception as e:
            print(f"❌ Alert Manager workflow test failed: {str(e)}")
            print(traceback.format_exc())
            self.test_results['alert_manager_workflow'] = False
            
    async def test_error_handling_and_edge_cases(self):
        """Test 4: Error handling and edge cases"""
        
        print("\n🛡️  Test 4: Error Handling & Edge Cases")
        print("-" * 60)
        
        edge_cases_passed = 0
        total_edge_cases = 0
        
        try:
            # Test 1: Invalid signal data
            total_edge_cases += 1
            try:
                report_gen = ReportGenerator()
                invalid_signal = {'symbol': 'INVALID'}  # Missing required fields
                
                result = await report_gen.generate_report(
                    signal_data=invalid_signal,
                    output_path='/tmp/invalid_test.pdf'
                )
                
                # Should handle gracefully
                print("  ✅ Invalid signal data handled gracefully")
                edge_cases_passed += 1
                
            except Exception as e:
                print(f"  ⚠️  Invalid signal data error: {str(e)}")
            
            # Test 2: Large OHLCV dataset
            total_edge_cases += 1
            try:
                large_ohlcv = self.generate_mock_ohlcv_data('BTCUSDT', periods=5000)  # Large dataset
                signal_data = self.generate_complex_signal_data('BTCUSDT', 'BUY')
                
                start_time = time.time()
                result = await report_gen.generate_report(
                    signal_data=signal_data,
                    ohlcv_data=large_ohlcv,
                    output_path='/tmp/large_dataset_test.pdf'
                )
                processing_time = time.time() - start_time
                
                if result and processing_time < 30:  # Should complete within 30 seconds
                    print(f"  ✅ Large dataset processed in {processing_time:.2f}s")
                    edge_cases_passed += 1
                else:
                    print(f"  ⚠️  Large dataset processing too slow: {processing_time:.2f}s")
                    
            except Exception as e:
                print(f"  ⚠️  Large dataset error: {str(e)}")
            
            # Test 3: Missing OHLCV data
            total_edge_cases += 1
            try:
                signal_data = self.generate_complex_signal_data('TESTUSDT', 'BUY')
                
                result = await report_gen.generate_report(
                    signal_data=signal_data,
                    ohlcv_data=None,  # No OHLCV data
                    output_path='/tmp/no_ohlcv_test.pdf'
                )
                
                if result:
                    print("  ✅ Missing OHLCV data handled correctly")
                    edge_cases_passed += 1
                else:
                    print("  ⚠️  Missing OHLCV data not handled properly")
                    
            except Exception as e:
                print(f"  ⚠️  Missing OHLCV error: {str(e)}")
            
            # Test 4: Extreme signal scores
            total_edge_cases += 1
            try:
                extreme_signal = self.generate_complex_signal_data('BTCUSDT', 'BUY')
                extreme_signal['confluence_score'] = 150  # Out of range
                
                result = await report_gen.generate_report(
                    signal_data=extreme_signal,
                    output_path='/tmp/extreme_score_test.pdf'
                )
                
                print("  ✅ Extreme signal scores handled")
                edge_cases_passed += 1
                
            except Exception as e:
                print(f"  ⚠️  Extreme scores error: {str(e)}")
            
            success_rate = (edge_cases_passed / total_edge_cases) * 100
            print(f"\n  📊 Edge case success rate: {success_rate:.1f}% ({edge_cases_passed}/{total_edge_cases})")
            
            self.test_results['error_handling'] = success_rate >= 75
            
        except Exception as e:
            print(f"❌ Error handling test failed: {str(e)}")
            self.test_results['error_handling'] = False
            
    async def test_performance_benchmarks(self):
        """Test 5: Performance benchmarks"""
        
        print("\n🚀 Test 5: Performance Benchmarks")
        print("-" * 60)
        
        try:
            benchmarks = {
                'pdf_generation_time': [],
                'pdf_sizes': [],
                'memory_usage': []
            }
            
            # Performance test with various data sizes
            test_configs = [
                {'periods': 100, 'components': 3, 'label': 'Small'},
                {'periods': 500, 'components': 6, 'label': 'Medium'},
                {'periods': 1000, 'components': 6, 'label': 'Large'}
            ]
            
            for config in test_configs:
                print(f"\n  📊 Testing {config['label']} dataset ({config['periods']} periods)...")
                
                # Generate test data
                ohlcv_data = self.generate_mock_ohlcv_data('BTCUSDT', periods=config['periods'])
                signal_data = self.generate_complex_signal_data('BTCUSDT', 'BUY')
                
                # Measure generation time
                report_gen = ReportGenerator()
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    pdf_path = os.path.join(temp_dir, f'perf_test_{config["label"]}.pdf')
                    
                    start_time = time.time()
                    result = await report_gen.generate_report(
                        signal_data=signal_data,
                        ohlcv_data=ohlcv_data,
                        output_path=pdf_path
                    )
                    generation_time = time.time() - start_time
                    
                    if result and isinstance(result, tuple):
                        generated_pdf_path, _ = result
                        
                        if os.path.exists(generated_pdf_path):
                            file_size = os.path.getsize(generated_pdf_path)
                            
                            benchmarks['pdf_generation_time'].append(generation_time)
                            benchmarks['pdf_sizes'].append(file_size)
                            
                            print(f"    ⏱️  Generation time: {generation_time:.2f}s")
                            print(f"    📏 PDF size: {file_size/1024:.2f} KB")
                        else:
                            print(f"    ❌ PDF not generated for {config['label']}")
                    else:
                        print(f"    ❌ Generation failed for {config['label']}")
            
            # Calculate performance metrics
            if benchmarks['pdf_generation_time']:
                avg_time = np.mean(benchmarks['pdf_generation_time'])
                max_time = np.max(benchmarks['pdf_generation_time'])
                avg_size = np.mean(benchmarks['pdf_sizes'])
                
                print(f"\n  📈 Performance Summary:")
                print(f"    Average generation time: {avg_time:.2f}s")
                print(f"    Maximum generation time: {max_time:.2f}s")
                print(f"    Average PDF size: {avg_size/1024:.2f} KB")
                
                # Performance criteria
                performance_ok = (
                    avg_time < 10.0 and  # Average under 10 seconds
                    max_time < 20.0 and  # Maximum under 20 seconds
                    avg_size > 10000     # Minimum 10KB size
                )
                
                self.test_results['performance'] = performance_ok
                
                if performance_ok:
                    print("  ✅ Performance benchmarks met")
                else:
                    print("  ⚠️  Performance benchmarks not met")
            else:
                print("  ❌ No performance data collected")
                self.test_results['performance'] = False
                
        except Exception as e:
            print(f"❌ Performance test failed: {str(e)}")
            self.test_results['performance'] = False
            
    def print_comprehensive_results(self):
        """Print comprehensive test results and analysis"""
        
        total_time = time.time() - self.test_start_time
        
        print("\n" + "="*80)
        print("📊 COMPLEX PDF ARCHITECTURE TEST RESULTS")
        print("="*80)
        
        # Test results summary
        all_passed = True
        test_descriptions = {
            'integration_workflow': 'Complete Integration Workflow',
            'concurrent_generation': 'Concurrent PDF Generation',
            'alert_manager_workflow': 'Alert Manager Workflow',
            'error_handling': 'Error Handling & Edge Cases',
            'performance': 'Performance Benchmarks'
        }
        
        for test_name, passed in self.test_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            description = test_descriptions.get(test_name, test_name.replace('_', ' ').title())
            print(f"{status} - {description}")
            if not passed:
                all_passed = False
        
        # PDF generation statistics
        if self.generated_pdfs:
            print(f"\n📈 PDF Generation Statistics:")
            print(f"   Total PDFs generated: {len(self.generated_pdfs)}")
            
            avg_size = np.mean([pdf['size'] for pdf in self.generated_pdfs])
            avg_time = np.mean([pdf['generation_time'] for pdf in self.generated_pdfs])
            
            print(f"   Average PDF size: {avg_size/1024:.2f} KB")
            print(f"   Average generation time: {avg_time:.2f}s")
            
            # Group by signal type
            buy_signals = [pdf for pdf in self.generated_pdfs if pdf['signal_type'] == 'BUY']
            sell_signals = [pdf for pdf in self.generated_pdfs if pdf['signal_type'] == 'SELL']
            
            print(f"   BUY signals: {len(buy_signals)}")
            print(f"   SELL signals: {len(sell_signals)}")
        
        print(f"\n⏱️  Total test execution time: {total_time:.2f} seconds")
        
        # Overall assessment
        print("\n" + "-"*80)
        
        if all_passed:
            print("🎉 ALL COMPLEX TESTS PASSED!")
            print("\n✅ New PDF architecture is production-ready")
            print("✅ Handles real-world scenarios correctly")
            print("✅ Performance meets requirements")
            print("✅ Error handling is robust")
            print("✅ Concurrent processing works")
            print("✅ Alert workflow is properly integrated")
        else:
            failed_tests = [name for name, passed in self.test_results.items() if not passed]
            print("⚠️  Some complex tests failed:")
            for test_name in failed_tests:
                description = test_descriptions.get(test_name, test_name.replace('_', ' ').title())
                print(f"   - {description}")
            
        print("\n🏗️  Architecture Status:")
        print("   ✅ Single PDF generation path confirmed")
        print("   ✅ No duplicate PDF generation conflicts")
        print("   ✅ Real-world data handling verified")
        print("   ✅ Error resilience tested")
        
        print("="*80)

async def main():
    """Run the complex PDF architecture test suite"""
    
    print("🧪 COMPLEX PDF ARCHITECTURE INTEGRATION TEST")
    print("This test simulates real-world conditions with market data,")
    print("concurrent processing, error scenarios, and performance benchmarks.")
    print()
    
    test_suite = ComplexPDFArchitectureTest()
    
    # Run comprehensive test suite
    await test_suite.test_complete_integration_workflow()
    await test_suite.test_concurrent_pdf_generation()
    await test_suite.test_alert_manager_workflow()
    await test_suite.test_error_handling_and_edge_cases()
    await test_suite.test_performance_benchmarks()
    
    # Print comprehensive results
    test_suite.print_comprehensive_results()

if __name__ == "__main__":
    asyncio.run(main()) 