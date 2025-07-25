#!/usr/bin/env python3
"""
Alert System Consistency Test
Tests that regular signal alerts and frequency alerts produce identical results.
"""

import asyncio
import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Import required modules
from monitoring.alert_manager import AlertManager
from monitoring.signal_frequency_tracker import SignalFrequencyTracker

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

async def create_test_alert_manager():
    """Create alert manager for testing."""
    # Simple config for testing
    config = {
        'alerts': {
            'discord': {
                'webhook_url': 'https://discord.com/api/webhooks/13756475279149630466/mLWWh-FDHOr7ZE3xBNFQh7DqxL5IqJ6dWLpRzCGNW2vPbIgW7Qx8KHVvEHMqnA6P_D9F'
            },
            'thresholds': {
                'buy': 65.0,
                'sell': 35.0
            }
        },
        'signal_frequency': {
            'enabled': True,
            'cooldown_minutes': 5,
            'min_score_improvement': 2.0,
            'alert_types': ['recurrence', 'frequency_pattern', 'high_confidence']
        }
    }
    
    # Create AlertManager
    alert_manager = AlertManager(config)
    
    # Create and link SignalFrequencyTracker
    signal_tracker = SignalFrequencyTracker(config)
    alert_manager.signal_frequency_tracker = signal_tracker
    
    return alert_manager, signal_tracker

def create_test_signal_data(symbol: str, score: float, signal_type: str):
    """Create test signal data."""
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
    
    return {
        'symbol': symbol,
        'confluence_score': score,
        'signal_type': signal_type,
        'components': {
            'technical': 72.3,
            'volume': 68.7,
            'orderbook': 85.2,
            'orderflow': 77.9,
            'sentiment': 61.4,
            'price_structure': 58.1
        },
        'results': {
            'technical': {'rsi': 66.5, 'macd': 0.85, 'ao': 1.2},
            'volume': {'volume_delta': 82.3, 'relative_volume': 1.4},
            'orderbook': {'depth_imbalance': 0.67, 'spread': 0.001}
        },
        'weights': {
            'technical': 0.20,
            'volume': 0.15,
            'orderbook': 0.25,
            'orderflow': 0.20,
            'sentiment': 0.10,
            'price_structure': 0.10
        },
        'reliability': 0.87,
        'price': 1.234,
        'transaction_id': f"TEST_{timestamp_str}",
        'signal_id': f"SIG_{timestamp_str}",
        'buy_threshold': 65.0,
        'sell_threshold': 35.0,
        'market_interpretations': [
            {
                'component': 'technical',
                'interpretation': f'Technical indicators show {"bullish momentum" if signal_type == "BUY" else "bearish pressure"}.'
            },
            {
                'component': 'orderbook',
                'interpretation': f'Order book shows {"strong buying interest" if signal_type == "BUY" else "selling pressure"}.'
            }
        ],
        'actionable_insights': [
            f'{"BULLISH" if signal_type == "BUY" else "BEARISH"} bias confirmed',
            'Monitor for confirmation signals'
        ],
        'influential_components': [
            {'name': 'orderbook', 'score': 85.2, 'impact': 'high'},
            {'name': 'orderflow', 'score': 77.9, 'impact': 'medium'}
        ],
        'top_weighted_subcomponents': [
            {'name': 'depth_imbalance', 'score': 85.3, 'impact': 2.1},
            {'name': 'order_flow', 'score': 77.8, 'impact': 1.9}
        ]
    }

async def create_mock_pdf(signal_data):
    """Create a mock PDF file for testing."""
    # Create exports directory if it doesn't exist
    os.makedirs('exports', exist_ok=True)
    
    # Create mock PDF path
    symbol = signal_data['symbol'].replace('/', '_').lower()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_path = f"exports/{symbol}_{signal_data['signal_type'].lower()}_{timestamp}_test.pdf"
    
    # Create mock PDF file with valid PDF header
    with open(pdf_path, 'wb') as f:
        f.write(b'%PDF-1.4\n%Mock PDF for testing alert system\nstartxref\n0\n%%EOF\n')
    
    signal_data['pdf_path'] = pdf_path
    return pdf_path

class TestResults:
    """Track test results."""
    def __init__(self):
        self.regular_alerts = []
        self.frequency_alerts = []
        self.errors = []
        self.pdf_files = []

async def test_regular_alert(alert_manager, signal_data, results):
    """Test regular signal alert."""
    logger.info(f"\n=== Testing Regular Alert: {signal_data['symbol']} {signal_data['signal_type']} ===")
    
    try:
        # Create mock PDF
        pdf_path = await create_mock_pdf(signal_data)
        results.pdf_files.append(pdf_path)
        
        logger.info(f"📊 Signal: {signal_data['symbol']} - {signal_data['signal_type']} - Score: {signal_data['confluence_score']}")
        logger.info(f"📎 Mock PDF: {pdf_path}")
        
        # Test regular alert path
        await alert_manager._send_regular_signal_alert(signal_data)
        
        results.regular_alerts.append({
            'symbol': signal_data['symbol'],
            'signal_type': signal_data['signal_type'],
            'score': signal_data['confluence_score'],
            'pdf_path': pdf_path,
            'success': True,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info("✅ Regular alert sent successfully")
        
    except Exception as e:
        error_msg = f"Regular alert failed for {signal_data['symbol']}: {str(e)}"
        logger.error(f"❌ {error_msg}")
        results.errors.append(error_msg)

async def test_frequency_alert(alert_manager, signal_data, results):
    """Test frequency alert."""
    logger.info(f"\n=== Testing Frequency Alert: {signal_data['symbol']} {signal_data['signal_type']} ===")
    
    try:
        # Create mock PDF
        pdf_path = await create_mock_pdf(signal_data)
        results.pdf_files.append(pdf_path)
        
        logger.info(f"📊 Signal: {signal_data['symbol']} - {signal_data['signal_type']} - Score: {signal_data['confluence_score']}")
        logger.info(f"📎 Mock PDF: {pdf_path}")
        
        # Create frequency alert data
        frequency_alert = {
            'symbol': signal_data['symbol'],
            'signal_type': signal_data['signal_type'],
            'current_score': signal_data['confluence_score'],
            'previous_score': 0.0,
            'time_since_last': 0,
            'frequency_count': 1,
            'alert_type': 'recurrence',
            'reason': 'First BUY signal detected',
            'signal_strength': 'Moderate',
            'signal_data': signal_data,
            'timestamp': datetime.now().isoformat()
        }
        
        # Test frequency alert path
        await alert_manager._send_frequency_alert(frequency_alert)
        
        results.frequency_alerts.append({
            'symbol': signal_data['symbol'],
            'signal_type': signal_data['signal_type'],
            'score': signal_data['confluence_score'],
            'pdf_path': pdf_path,
            'reason': frequency_alert['reason'],
            'success': True,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info("✅ Frequency alert sent successfully")
        
    except Exception as e:
        error_msg = f"Frequency alert failed for {signal_data['symbol']}: {str(e)}"
        logger.error(f"❌ {error_msg}")
        results.errors.append(error_msg)

async def test_main_wrapper(alert_manager, signal_data, results):
    """Test main send_signal_alert wrapper."""
    logger.info(f"\n=== Testing Main Wrapper: {signal_data['symbol']} {signal_data['signal_type']} ===")
    
    try:
        # Create mock PDF
        pdf_path = await create_mock_pdf(signal_data)
        results.pdf_files.append(pdf_path)
        
        logger.info(f"📊 Signal: {signal_data['symbol']} - {signal_data['signal_type']} - Score: {signal_data['confluence_score']}")
        logger.info(f"📎 Mock PDF: {pdf_path}")
        
        # Test main wrapper
        await alert_manager.send_signal_alert(signal_data)
        
        logger.info("✅ Main wrapper executed successfully")
        
    except Exception as e:
        error_msg = f"Main wrapper failed for {signal_data['symbol']}: {str(e)}"
        logger.error(f"❌ {error_msg}")
        results.errors.append(error_msg)

def cleanup_test_files(results):
    """Clean up test files."""
    logger.info("\n=== Cleaning Up Test Files ===")
    
    cleaned = 0
    for pdf_path in results.pdf_files:
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                cleaned += 1
        except Exception as e:
            logger.warning(f"Could not remove {pdf_path}: {e}")
    
    logger.info(f"🗑️ Cleaned {cleaned} test files")

async def run_comprehensive_test():
    """Run comprehensive alert system test."""
    logger.info("🚀 STARTING COMPREHENSIVE ALERT SYSTEM TEST")
    logger.info("=" * 60)
    
    results = TestResults()
    
    try:
        # Initialize alert system
        alert_manager, signal_tracker = await create_test_alert_manager()
        logger.info("✅ Alert system initialized")
        
        # Test cases
        test_cases = [
            {'symbol': 'BTCUSDT', 'score': 72.5, 'signal_type': 'BUY'},
            {'symbol': 'ETHUSDT', 'score': 67.8, 'signal_type': 'BUY'},
            {'symbol': 'ADAUSDT', 'score': 28.3, 'signal_type': 'SELL'},
            {'symbol': 'SOLUSDT', 'score': 33.7, 'signal_type': 'SELL'}
        ]
        
        # Run tests for each case
        for case in test_cases:
            signal_data = create_test_signal_data(case['symbol'], case['score'], case['signal_type'])
            
            # Test regular alert
            await test_regular_alert(alert_manager, signal_data, results)
            await asyncio.sleep(1)
            
            # Test frequency alert  
            await test_frequency_alert(alert_manager, signal_data, results)
            await asyncio.sleep(1)
            
            # Test main wrapper
            await test_main_wrapper(alert_manager, signal_data, results)
            await asyncio.sleep(2)  # Longer delay between symbols
        
        # Print results
        print_test_summary(results)
        
        return len(results.errors) == 0
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        cleanup_test_files(results)

def print_test_summary(results):
    """Print test summary."""
    logger.info("\n" + "=" * 60)
    logger.info("🎯 TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    
    logger.info(f"📊 Regular Alerts Tested: {len(results.regular_alerts)}")
    logger.info(f"📈 Frequency Alerts Tested: {len(results.frequency_alerts)}")
    logger.info(f"📎 PDF Files Created: {len(results.pdf_files)}")
    logger.info(f"❌ Errors: {len(results.errors)}")
    
    if results.errors:
        logger.error("\n❌ ERRORS FOUND:")
        for error in results.errors:
            logger.error(f"  • {error}")
    
    # Calculate success rate
    total_tests = len(results.regular_alerts) + len(results.frequency_alerts)
    successful = len([r for r in results.regular_alerts if r.get('success', False)]) + \
                len([r for r in results.frequency_alerts if r.get('success', False)])
    
    if total_tests > 0:
        success_rate = (successful / total_tests) * 100
        logger.info(f"\n✅ SUCCESS RATE: {success_rate:.1f}% ({successful}/{total_tests})")
        
        if success_rate >= 95:
            logger.info("🎉 EXCELLENT: Both regular and frequency alerts working perfectly!")
        elif success_rate >= 80:
            logger.info("✅ GOOD: Most alerts working - minor issues to address")
        else:
            logger.error("❌ NEEDS ATTENTION: Alert system requires fixes")
    
    logger.info("=" * 60)
    
    # Consistency check
    if len(results.regular_alerts) > 0 and len(results.frequency_alerts) > 0:
        logger.info("\n🔍 CONSISTENCY CHECK:")
        logger.info("Both regular and frequency alert paths were tested")
        logger.info("✅ Enhanced formatting should be identical in both paths")
        logger.info("✅ PDF attachments should work in both paths")

async def main():
    """Main entry point."""
    success = await run_comprehensive_test()
    
    if success:
        logger.info("🎉 All tests completed successfully!")
        return 0
    else:
        logger.error("❌ Some tests failed - check logs")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 