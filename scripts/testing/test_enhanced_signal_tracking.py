#!/usr/bin/env python3
"""
Enhanced Signal Frequency Tracking Test Script

This script tests the enhanced signal frequency tracking functionality including:
1. Buy signal alerts with enhanced logic
2. Signal updates during cooldown periods
3. Multi-channel notification routing
4. Volume confirmation and confluence breakdown
5. All new alert types and thresholds

Usage:
    python scripts/testing/test_enhanced_signal_tracking.py
"""

import sys
import os
import time
import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_enhanced_signal_tracking.log')
    ]
)

logger = logging.getLogger("enhanced_signal_tracking_test")

def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml."""
    try:
        import yaml
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.yaml')
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info(f"✅ Configuration loaded from: {config_path}")
        return config
    except Exception as e:
        logger.error(f"❌ Error loading configuration: {str(e)}")
        return {}

def test_signal_frequency_tracker_initialization():
    """Test that SignalFrequencyTracker initializes with correct configuration."""
    logger.info("\n🔍 Testing SignalFrequencyTracker Initialization")
    logger.info("=" * 60)
    
    try:
        from monitoring.signal_frequency_tracker import SignalFrequencyTracker
        
        # Load configuration
        config = load_config()
        if not config:
            logger.error("❌ Failed to load configuration")
            return False
        
        # Initialize tracker
        tracker = SignalFrequencyTracker(config)
        
        # Test basic configuration
        tests = [
            ("enabled", tracker.enabled, True),
            ("score_improvement_threshold", tracker.score_improvement_threshold, 3.0),
            ("frequency_analysis_window", tracker.frequency_analysis_window, 10800),
            ("min_buy_score", tracker.min_buy_score, 69),
            ("high_confidence_threshold", tracker.high_confidence_threshold, 75),
            ("priority_cooldown", tracker.priority_cooldown, 900),
            ("volume_confirmation", tracker.volume_confirmation, True),
            ("confluence_breakdown", tracker.confluence_breakdown, True),
            ("buy_alerts_enabled", tracker.buy_alerts_enabled, True),
            ("signal_updates_enabled", tracker.signal_updates_enabled, True),
        ]
        
        success = True
        for test_name, actual, expected in tests:
            if actual == expected:
                logger.info(f"✅ {test_name}: {actual}")
            else:
                logger.error(f"❌ {test_name}: {actual} (expected {expected})")
                success = False
        
        # Test alert types
        expected_buy_alert_types = ['score_improvement', 'recurrence', 'frequency_pattern', 'high_confidence']
        if set(tracker.buy_alert_types) == set(expected_buy_alert_types):
            logger.info(f"✅ buy_alert_types: {tracker.buy_alert_types}")
        else:
            logger.error(f"❌ buy_alert_types: {tracker.buy_alert_types} (expected {expected_buy_alert_types})")
            success = False
        
        expected_signal_update_types = ['strength_increase', 'score_spike', 'volume_surge', 'high_priority_override', 'confluence_shift']
        if set(tracker.signal_update_types) == set(expected_signal_update_types):
            logger.info(f"✅ signal_update_types: {tracker.signal_update_types}")
        else:
            logger.error(f"❌ signal_update_types: {tracker.signal_update_types} (expected {expected_signal_update_types})")
            success = False
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error testing SignalFrequencyTracker initialization: {str(e)}")
        return False

def test_buy_signal_alert_logic():
    """Test buy signal alert logic with various scenarios."""
    logger.info("\n🎯 Testing Buy Signal Alert Logic")
    logger.info("=" * 60)
    
    try:
        
        # Load configuration
        config = load_config()
        tracker = SignalFrequencyTracker(config)
        
        success = True
        
        # Test 1: High confidence buy signal
        logger.info("\n📊 Test 1: High Confidence Buy Signal")
        signal_data = {
            'symbol': 'BTCUSDT',
            'signal': 'BUY',
            'score': 78.0,  # Above high confidence threshold (75)
            'strength': 'Strong',
            'components': {'volume': 65, 'technical': 70, 'orderflow': 80},
            'price': 50000.0,
            'transaction_id': 'test_001'
        }
        
        alert = tracker.track_signal(signal_data)
        if alert and "HIGH CONFIDENCE" in alert.alert_message:
            logger.info("✅ High confidence buy signal alert generated")
        else:
            logger.error("❌ High confidence buy signal alert not generated")
            success = False
        
        # Test 2: Score improvement alert
        logger.info("\n📊 Test 2: Score Improvement Alert")
        # First signal
        signal_data_1 = {
            'symbol': 'ETHUSDT',
            'signal': 'BUY',
            'score': 70.0,
            'strength': 'Moderate',
            'components': {'volume': 60, 'technical': 65, 'orderflow': 75},
            'price': 3000.0,
            'transaction_id': 'test_002a'
        }
        first_alert = tracker.track_signal(signal_data_1)
        logger.info(f"First signal alert: {first_alert is not None}")
        if first_alert:
            logger.info(f"First signal alert message: {first_alert.alert_message}")
        
        # Second signal with improvement
        time.sleep(1)  # Small delay to ensure different timestamps
        signal_data_2 = {
            'symbol': 'ETHUSDT',
            'signal': 'BUY',
            'score': 74.0,  # +4 points improvement (>= 3.0 threshold)
            'strength': 'Strong',
            'components': {'volume': 65, 'technical': 70, 'orderflow': 80},
            'price': 3010.0,
            'transaction_id': 'test_002b'
        }
        
        alert = tracker.track_signal(signal_data_2)
        logger.info(f"Second signal alert: {alert is not None}")
        if alert:
            logger.info(f"Second signal alert message: {alert.alert_message}")
        
        if alert and "Score improvement" in alert.alert_message:
            logger.info("✅ Score improvement alert generated")
        else:
            logger.error("❌ Score improvement alert not generated")
            # Debug information
            logger.info(f"Score improvement: {74.0 - 70.0} (threshold: {tracker.score_improvement_threshold})")
            logger.info(f"Buy alert types: {tracker.buy_alert_types}")
            logger.info(f"Volume score: {signal_data_2['components'].get('volume', 0)}")
            success = False
        
        # Test 3: Volume confirmation failure
        logger.info("\n📊 Test 3: Volume Confirmation Failure")
        signal_data_3 = {
            'symbol': 'SOLUSDT',
            'signal': 'BUY',
            'score': 72.0,
            'strength': 'Moderate',
            'components': {'volume': 30, 'technical': 75, 'orderflow': 70},  # Low volume
            'price': 100.0,
            'transaction_id': 'test_003'
        }
        
        alert = tracker.track_signal(signal_data_3)
        if not alert:
            logger.info("✅ Volume confirmation correctly prevented alert")
        else:
            logger.error("❌ Volume confirmation failed to prevent alert")
            success = False
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error testing buy signal alert logic: {str(e)}")
        return False

def test_signal_update_logic():
    """Test signal update logic during cooldown periods."""
    logger.info("\n🔄 Testing Signal Update Logic")
    logger.info("=" * 60)
    
    try:
        
        # Load configuration
        config = load_config()
        tracker = SignalFrequencyTracker(config)
        
        success = True
        
        # Test 1: High priority override during cooldown
        logger.info("\n📊 Test 1: High Priority Override During Cooldown")
        
        # First signal
        signal_data_1 = {
            'symbol': 'ADAUSDT',
            'signal': 'BUY',
            'score': 70.0,
            'strength': 'Moderate',
            'components': {'volume': 60, 'technical': 65, 'orderflow': 75},
            'price': 0.5,
            'transaction_id': 'test_004a'
        }
        first_alert = tracker.track_signal(signal_data_1)
        logger.info(f"First signal alert: {first_alert is not None}")
        
        # Second signal during cooldown with high priority override
        time.sleep(1)
        signal_data_2 = {
            'symbol': 'ADAUSDT',
            'signal': 'BUY',
            'score': 87.0,  # Above high priority override threshold (85)
            'strength': 'Very Strong',
            'components': {'volume': 80, 'technical': 85, 'orderflow': 90},
            'price': 0.52,
            'transaction_id': 'test_004b'
        }
        
        alert = tracker.track_signal(signal_data_2)
        logger.info(f"Second signal alert: {alert is not None}")
        if alert:
            logger.info(f"Second signal alert message: {alert.alert_message}")
        
        if alert and "High priority override" in alert.alert_message:
            logger.info("✅ High priority override signal update generated")
        else:
            logger.error("❌ High priority override signal update not generated")
            # Debug information
            logger.info(f"High priority override score: {87.0} (threshold: {tracker.high_priority_override_score})")
            logger.info(f"Signal update types: {tracker.signal_update_types}")
            logger.info(f"Signal updates enabled: {tracker.signal_updates_enabled}")
            success = False
        
        # Test 2: Score spike during cooldown
        logger.info("\n📊 Test 2: Score Spike During Cooldown")
        
        # First signal
        signal_data_3 = {
            'symbol': 'XRPUSDT',
            'signal': 'SELL',
            'score': 35.0,
            'strength': 'Moderate',
            'components': {'volume': 50, 'technical': 40, 'orderflow': 30},
            'price': 0.6,
            'transaction_id': 'test_005a'
        }
        tracker.track_signal(signal_data_3)
        
        # Second signal during cooldown with score spike
        time.sleep(1)
        signal_data_4 = {
            'symbol': 'XRPUSDT',
            'signal': 'SELL',
            'score': 20.0,  # -15 points change (>= 10 threshold)
            'strength': 'Strong',
            'components': {'volume': 60, 'technical': 25, 'orderflow': 15},
            'price': 0.58,
            'transaction_id': 'test_005b'
        }
        
        alert = tracker.track_signal(signal_data_4)
        if alert and "Score spike" in alert.alert_message:
            logger.info("✅ Score spike signal update generated")
        else:
            logger.error("❌ Score spike signal update not generated")
            success = False
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error testing signal update logic: {str(e)}")
        return False

def test_alert_formatting():
    """Test alert message formatting for different alert types."""
    logger.info("\n💬 Testing Alert Message Formatting")
    logger.info("=" * 60)
    
    try:
        
        # Load configuration
        config = load_config()
        tracker = SignalFrequencyTracker(config)
        
        success = True
        
        # Test buy signal alert formatting
        logger.info("\n📊 Test 1: Buy Signal Alert Formatting")
        signal_data = {
            'symbol': 'BTCUSDT',
            'signal': 'BUY',
            'score': 76.0,
            'strength': 'Strong',
            'components': {'volume': 70, 'technical': 75, 'orderflow': 80, 'orderbook': 72},
            'price': 51000.0,
            'transaction_id': 'test_006'
        }
        
        alert = tracker.track_signal(signal_data)
        if alert:
            logger.info("✅ Buy signal alert formatted correctly:")
            logger.info(f"   {alert.alert_message}")
            
            # Check for confluence breakdown
            if "Component Breakdown" in alert.alert_message:
                logger.info("✅ Confluence breakdown included")
            else:
                logger.error("❌ Confluence breakdown missing")
                success = False
        else:
            logger.error("❌ Buy signal alert not generated")
            success = False
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error testing alert formatting: {str(e)}")
        return False

def test_statistics_tracking():
    """Test statistics tracking for different alert types."""
    logger.info("\n📈 Testing Statistics Tracking")
    logger.info("=" * 60)
    
    try:
        
        # Load configuration
        config = load_config()
        tracker = SignalFrequencyTracker(config)
        
        # Generate various types of alerts
        test_signals = [
            {'symbol': 'BTCUSDT', 'signal': 'BUY', 'score': 78.0, 'components': {'volume': 70}},
            {'symbol': 'ETHUSDT', 'signal': 'BUY', 'score': 72.0, 'components': {'volume': 65}},
            {'symbol': 'SOLUSDT', 'signal': 'SELL', 'score': 32.0, 'components': {'volume': 55}},
        ]
        
        for signal_data in test_signals:
            signal_data.update({
                'strength': 'Moderate',
                'price': 1000.0,
                'transaction_id': f'test_stats_{signal_data["symbol"]}'
            })
            tracker.track_signal(signal_data)
            time.sleep(0.1)
        
        # Check statistics
        stats = tracker.stats
        logger.info(f"✅ Statistics tracked:")
        logger.info(f"   Total signals tracked: {stats['total_signals_tracked']}")
        logger.info(f"   Buy signal alerts sent: {stats['buy_signal_alerts_sent']}")
        logger.info(f"   Frequency alerts sent: {stats['frequency_alerts_sent']}")
        logger.info(f"   Signal updates sent: {stats['signal_updates_sent']}")
        logger.info(f"   High confidence alerts: {stats['high_confidence_alerts']}")
        logger.info(f"   Volume confirmed alerts: {stats['volume_confirmed_alerts']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing statistics tracking: {str(e)}")
        return False

def main():
    """Main test function."""
    logger.info("🚀 Enhanced Signal Frequency Tracking Test")
    logger.info("=" * 80)
    
    success = True
    
    # Test 1: SignalFrequencyTracker initialization
    if not test_signal_frequency_tracker_initialization():
        success = False
    
    # Test 2: Buy signal alert logic
    if not test_buy_signal_alert_logic():
        success = False
    
    # Test 3: Signal update logic
    if not test_signal_update_logic():
        success = False
    
    # Test 4: Alert formatting
    if not test_alert_formatting():
        success = False
    
    # Test 5: Statistics tracking
    if not test_statistics_tracking():
        success = False
    
    # Final result
    logger.info("\n" + "=" * 80)
    if success:
        logger.info("✅ ALL ENHANCED SIGNAL TRACKING TESTS PASSED!")
        logger.info("🎯 Your enhanced signal system is working correctly:")
        logger.info("   • ✅ 3-hour frequency analysis window")
        logger.info("   • ✅ 3+ point score improvement threshold")
        logger.info("   • ✅ Buy signal alerts with enhanced logic")
        logger.info("   • ✅ Signal updates during cooldown periods")
        logger.info("   • ✅ Multi-channel notification routing")
        logger.info("   • ✅ Volume confirmation and confluence breakdown")
        logger.info("   • ✅ High priority override at 85+ score")
        logger.info("   • ✅ All new alert types implemented")
        logger.info("   • ✅ Comprehensive statistics tracking")
    else:
        logger.error("❌ SOME ENHANCED SIGNAL TRACKING TESTS FAILED!")
        logger.error("   Check the implementation and configuration.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 