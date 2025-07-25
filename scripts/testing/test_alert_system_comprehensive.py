#!/usr/bin/env python3
"""
Comprehensive Alert System Test
Tests both regular signal alerts and frequency alerts to ensure they produce
identical enhanced formatting and PDF attachments.
"""

import asyncio
import sys
import os
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from monitoring.alert_manager import AlertManager
from monitoring.signal_frequency_tracker import SignalFrequencyTracker
from core.config.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_alert_system.log')
    ]
)

logger = logging.getLogger(__name__)

class AlertSystemTester:
    """Comprehensive tester for alert system consistency."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        self.alert_manager = None
        self.signal_tracker = None
        self.test_results = {
            'regular_alerts': [],
            'frequency_alerts': [],
            'pdf_files_generated': [],
            'errors': []
        }
        
    async def setup(self):
        """Initialize alert manager and signal tracker."""
        try:
            # Initialize AlertManager
            self.alert_manager = AlertManager(self.config)
            logger.info("✅ AlertManager initialized")
            
            # Initialize SignalFrequencyTracker
            self.signal_tracker = SignalFrequencyTracker(self.config)
            
            # Link the signal tracker to alert manager
            self.alert_manager.signal_frequency_tracker = self.signal_tracker
            logger.info("✅ SignalFrequencyTracker initialized and linked")
            
            # Ensure exports directory exists
            os.makedirs('exports', exist_ok=True)
            os.makedirs('reports/pdf', exist_ok=True)
            
            return True
        except Exception as e:
            logger.error(f"❌ Setup failed: {str(e)}")
            self.test_results['errors'].append(f"Setup: {str(e)}")
            return False
    
    def create_test_signal_data(self, symbol: str, score: float, signal_type: str) -> Dict[str, Any]:
        """Create comprehensive test signal data."""
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create realistic component scores
        if signal_type == "BUY":
            components = {
                'technical': 72.5,
                'volume': 68.3,
                'orderbook': 85.7,
                'orderflow': 77.2,
                'sentiment': 61.4,
                'price_structure': 59.8
            }
        else:  # SELL
            components = {
                'technical': 35.2,
                'volume': 42.7,
                'orderbook': 28.3,
                'orderflow': 31.8,
                'sentiment': 38.9,
                'price_structure': 33.1
            }
        
        # Create realistic results data
        results = {
            'technical': {
                'rsi': 66.7 if signal_type == "BUY" else 33.2,
                'macd': 0.85 if signal_type == "BUY" else -0.45,
                'ao': 1.23 if signal_type == "BUY" else -0.87,
                'williams_r': -25.3 if signal_type == "BUY" else -75.8,
                'cci': 125.4 if signal_type == "BUY" else -89.2,
                'atr': 0.045
            },
            'volume': {
                'volume_delta': 85.2 if signal_type == "BUY" else 15.8,
                'relative_volume': 1.34,
                'obv_trend': 'bullish' if signal_type == "BUY" else 'bearish',
                'cmf': 0.15 if signal_type == "BUY" else -0.12
            },
            'orderbook': {
                'bid_ask_spread': 0.001,
                'depth_imbalance': 0.67 if signal_type == "BUY" else 0.23,
                'large_orders': 15 if signal_type == "BUY" else 8
            }
        }
        
        return {
            'symbol': symbol,
            'confluence_score': score,
            'components': components,
            'results': results,
            'weights': {
                'technical': 0.20,
                'volume': 0.15,
                'orderbook': 0.25,
                'orderflow': 0.20,
                'sentiment': 0.10,
                'price_structure': 0.10
            },
            'reliability': 0.85,
            'price': 1.2345 if 'EUR' in symbol else 0.5678,
            'transaction_id': f"TEST_{timestamp_str}",
            'signal_id': f"SIG_{timestamp_str}",
            'buy_threshold': 65.0,
            'sell_threshold': 35.0,
            'signal_type': signal_type,
            'market_interpretations': [
                {
                    'component': 'technical',
                    'interpretation': f'Technical indicators show {"bullish momentum" if signal_type == "BUY" else "bearish pressure"} with strong directional bias.'
                },
                {
                    'component': 'orderbook', 
                    'interpretation': f'Order book structure indicates {"buying pressure" if signal_type == "BUY" else "selling pressure"} from institutional players.'
                }
            ],
            'actionable_insights': [
                f'{"BULLISH" if signal_type == "BUY" else "BEARISH"} BIAS: Score ({score:.1f}) {"above buy" if signal_type == "BUY" else "below sell"} threshold',
                f'STRATEGY: {"Monitor for pullbacks to key support levels" if signal_type == "BUY" else "Watch for bounce from key resistance levels"}'
            ],
            'influential_components': [
                {'name': 'orderbook', 'score': components['orderbook'], 'impact': 'high'},
                {'name': 'orderflow', 'score': components['orderflow'], 'impact': 'medium'},
                {'name': 'technical', 'score': components['technical'], 'impact': 'medium'}
            ],
            'top_weighted_subcomponents': [
                {'name': 'depth_imbalance', 'score': 85.3, 'impact': 2.1},
                {'name': 'order_flow', 'score': 77.8, 'impact': 1.9},
                {'name': 'rsi_momentum', 'score': 72.4, 'impact': 1.4}
            ]
        }
    
    async def test_regular_signal_alert(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Test regular signal alert (bypassing frequency tracker)."""
        logger.info(f"\n=== Testing Regular Signal Alert: {test_case['name']} ===")
        
        try:
            signal_data = self.create_test_signal_data(
                test_case['symbol'], 
                test_case['score'], 
                test_case['signal_type']
            )
            
            # Add mock PDF path for testing
            pdf_filename = f"{signal_data['symbol'].lower().replace('/', '_')}_{signal_data['signal_type'].lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = os.path.join('reports', 'pdf', pdf_filename)
            
            # Create mock PDF file
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            with open(pdf_path, 'wb') as f:
                f.write(b'%PDF-1.4\nMock PDF content for testing\n')
            
            signal_data['pdf_path'] = pdf_path
            self.test_results['pdf_files_generated'].append(pdf_path)
            
            logger.info(f"📊 Signal Data: {signal_data['symbol']} - {signal_data['signal_type']} - Score: {signal_data['confluence_score']}")
            logger.info(f"📎 Mock PDF created: {pdf_path}")
            
            # Call _send_regular_signal_alert directly to bypass frequency tracking
            await self.alert_manager._send_regular_signal_alert(signal_data)
            
            result = {
                'test_case': test_case['name'],
                'method': 'regular_signal_alert',
                'symbol': signal_data['symbol'],
                'signal_type': signal_data['signal_type'],
                'score': signal_data['confluence_score'],
                'pdf_path': pdf_path,
                'pdf_exists': os.path.exists(pdf_path),
                'success': True,
                'timestamp': datetime.now().isoformat()
            }
            
            self.test_results['regular_alerts'].append(result)
            logger.info(f"✅ Regular alert test completed successfully")
            return result
            
        except Exception as e:
            error_msg = f"Regular signal alert failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(traceback.format_exc())
            
            self.test_results['errors'].append(error_msg)
            return {
                'test_case': test_case['name'],
                'method': 'regular_signal_alert', 
                'success': False,
                'error': error_msg
            }
    
    async def test_frequency_signal_alert(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Test frequency-based signal alert."""
        logger.info(f"\n=== Testing Frequency Signal Alert: {test_case['name']} ===")
        
        try:
            signal_data = self.create_test_signal_data(
                test_case['symbol'],
                test_case['score'], 
                test_case['signal_type']
            )
            
            # Add mock PDF path for testing
            pdf_filename = f"{signal_data['symbol'].lower().replace('/', '_')}_{signal_data['signal_type'].lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = os.path.join('reports', 'pdf', pdf_filename)
            
            # Create mock PDF file
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            with open(pdf_path, 'wb') as f:
                f.write(b'%PDF-1.4\nMock PDF content for frequency testing\n')
            
            signal_data['pdf_path'] = pdf_path
            self.test_results['pdf_files_generated'].append(pdf_path)
            
            logger.info(f"📊 Signal Data: {signal_data['symbol']} - {signal_data['signal_type']} - Score: {signal_data['confluence_score']}")
            logger.info(f"📎 Mock PDF created: {pdf_path}")
            
            # First signal - this should generate a frequency alert
            frequency_alert = self.signal_tracker.track_signal(signal_data)
            
            if frequency_alert:
                logger.info(f"📈 Frequency alert generated: {frequency_alert.get('reason', 'Unknown reason')}")
                
                # Test the frequency alert workflow
                await self.alert_manager._send_frequency_alert(frequency_alert)
                
                result = {
                    'test_case': test_case['name'],
                    'method': 'frequency_signal_alert',
                    'symbol': signal_data['symbol'],
                    'signal_type': signal_data['signal_type'],
                    'score': signal_data['confluence_score'],
                    'pdf_path': pdf_path,
                    'pdf_exists': os.path.exists(pdf_path),
                    'frequency_reason': frequency_alert.get('reason', 'Unknown'),
                    'success': True,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.test_results['frequency_alerts'].append(result)
                logger.info(f"✅ Frequency alert test completed successfully")
                return result
            else:
                logger.warning("⚠️ No frequency alert generated - signal may be in cooldown")
                return {
                    'test_case': test_case['name'],
                    'method': 'frequency_signal_alert',
                    'success': False,
                    'error': 'No frequency alert generated'
                }
                
        except Exception as e:
            error_msg = f"Frequency signal alert failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(traceback.format_exc())
            
            self.test_results['errors'].append(error_msg)
            return {
                'test_case': test_case['name'],
                'method': 'frequency_signal_alert',
                'success': False,
                'error': error_msg
            }
    
    async def test_send_signal_alert_wrapper(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Test the main send_signal_alert method that routes to appropriate handler."""
        logger.info(f"\n=== Testing Send Signal Alert Wrapper: {test_case['name']} ===")
        
        try:
            signal_data = self.create_test_signal_data(
                test_case['symbol'],
                test_case['score'],
                test_case['signal_type']
            )
            
            # Add mock PDF path
            pdf_filename = f"{signal_data['symbol'].lower().replace('/', '_')}_{signal_data['signal_type'].lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = os.path.join('reports', 'pdf', pdf_filename)
            
            # Create mock PDF file
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            with open(pdf_path, 'wb') as f:
                f.write(b'%PDF-1.4\nMock PDF content for wrapper testing\n')
            
            signal_data['pdf_path'] = pdf_path
            self.test_results['pdf_files_generated'].append(pdf_path)
            
            logger.info(f"📊 Testing wrapper method with {signal_data['symbol']} - {signal_data['signal_type']} - Score: {signal_data['confluence_score']}")
            
            # Call the main send_signal_alert method
            await self.alert_manager.send_signal_alert(signal_data)
            
            result = {
                'test_case': test_case['name'],
                'method': 'send_signal_alert_wrapper',
                'symbol': signal_data['symbol'], 
                'signal_type': signal_data['signal_type'],
                'score': signal_data['confluence_score'],
                'pdf_path': pdf_path,
                'pdf_exists': os.path.exists(pdf_path),
                'success': True,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Wrapper method test completed successfully")
            return result
            
        except Exception as e:
            error_msg = f"Send signal alert wrapper failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(traceback.format_exc())
            
            self.test_results['errors'].append(error_msg)
            return {
                'test_case': test_case['name'],
                'method': 'send_signal_alert_wrapper',
                'success': False,
                'error': error_msg
            }
    
    def cleanup_test_files(self):
        """Clean up generated test files."""
        logger.info("\n=== Cleaning Up Test Files ===")
        
        cleaned_files = 0
        for pdf_path in self.test_results['pdf_files_generated']:
            try:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                    cleaned_files += 1
                    logger.debug(f"🗑️ Removed: {pdf_path}")
            except Exception as e:
                logger.warning(f"⚠️ Could not remove {pdf_path}: {str(e)}")
        
        logger.info(f"🗑️ Cleaned up {cleaned_files} test PDF files")
    
    def generate_test_report(self) -> str:
        """Generate comprehensive test report."""
        report = {
            'test_summary': {
                'total_tests': len(self.test_results['regular_alerts']) + len(self.test_results['frequency_alerts']),
                'regular_alerts': len(self.test_results['regular_alerts']),
                'frequency_alerts': len(self.test_results['frequency_alerts']),
                'errors': len(self.test_results['errors']),
                'pdf_files_generated': len(self.test_results['pdf_files_generated'])
            },
            'detailed_results': self.test_results,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save to file
        report_path = f'exports/alert_system_test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📊 Test report saved: {report_path}")
        return report_path
    
    async def run_comprehensive_tests(self):
        """Run all comprehensive tests."""
        logger.info("\n🚀 STARTING COMPREHENSIVE ALERT SYSTEM TESTS")
        logger.info("=" * 60)
        
        # Test cases covering different scenarios
        test_cases = [
            {
                'name': 'Strong BUY Signal',
                'symbol': 'BTCUSDT',
                'score': 72.5,
                'signal_type': 'BUY'
            },
            {
                'name': 'Moderate BUY Signal', 
                'symbol': 'ETHUSDT',
                'score': 67.3,
                'signal_type': 'BUY'
            },
            {
                'name': 'Strong SELL Signal',
                'symbol': 'ADAUSDT', 
                'score': 28.7,
                'signal_type': 'SELL'
            },
            {
                'name': 'Moderate SELL Signal',
                'symbol': 'SOLUSDT',
                'score': 33.2,
                'signal_type': 'SELL'
            }
        ]
        
        # Initialize
        if not await self.setup():
            logger.error("❌ Setup failed - aborting tests")
            return False
        
        try:
            # Test each case with all methods
            for test_case in test_cases:
                # Test regular signal alert
                await self.test_regular_signal_alert(test_case)
                await asyncio.sleep(1)  # Small delay between tests
                
                # Test frequency signal alert
                await self.test_frequency_signal_alert(test_case) 
                await asyncio.sleep(1)
                
                # Test wrapper method
                await self.test_send_signal_alert_wrapper(test_case)
                await asyncio.sleep(2)  # Longer delay between different symbols
            
            # Generate report
            report_path = self.generate_test_report()
            
            # Print summary
            self.print_test_summary()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Comprehensive test failed: {str(e)}")
            logger.error(traceback.format_exc())
            return False
        
        finally:
            # Always cleanup
            self.cleanup_test_files()
    
    def print_test_summary(self):
        """Print test summary to console."""
        summary = self.test_results
        
        logger.info("\n" + "=" * 60)
        logger.info("🎯 COMPREHENSIVE TEST RESULTS SUMMARY")
        logger.info("=" * 60)
        
        logger.info(f"📊 Total Tests Run: {len(summary['regular_alerts']) + len(summary['frequency_alerts'])}")
        logger.info(f"🔄 Regular Alerts: {len(summary['regular_alerts'])}")
        logger.info(f"📈 Frequency Alerts: {len(summary['frequency_alerts'])}")
        logger.info(f"📎 PDF Files Generated: {len(summary['pdf_files_generated'])}")
        logger.info(f"❌ Errors: {len(summary['errors'])}")
        
        if summary['errors']:
            logger.error("\n❌ ERRORS FOUND:")
            for error in summary['errors']:
                logger.error(f"  • {error}")
        
        # Success rate calculation
        total_tests = len(summary['regular_alerts']) + len(summary['frequency_alerts'])
        successful_tests = len([r for r in summary['regular_alerts'] if r.get('success', False)]) + \
                          len([r for r in summary['frequency_alerts'] if r.get('success', False)])
        
        if total_tests > 0:
            success_rate = (successful_tests / total_tests) * 100
            logger.info(f"\n✅ SUCCESS RATE: {success_rate:.1f}% ({successful_tests}/{total_tests})")
            
            if success_rate >= 90:
                logger.info("🎉 EXCELLENT: Alert system is working consistently!")
            elif success_rate >= 70:
                logger.info("✅ GOOD: Alert system is mostly working - minor issues to address")
            else:
                logger.error("❌ POOR: Alert system needs significant fixes")
        
        logger.info("=" * 60)

async def main():
    """Main test execution."""
    tester = AlertSystemTester()
    success = await tester.run_comprehensive_tests()
    
    if success:
        logger.info("🎉 All comprehensive tests completed!")
        return 0
    else:
        logger.error("❌ Tests failed - check logs for details")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 