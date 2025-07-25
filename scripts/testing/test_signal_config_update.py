#!/usr/bin/env python3
"""
Test script for updated signal frequency tracking configuration.

This script tests the new signal update alerts and 3-hour frequency analysis window.
"""

import os
import sys
import yaml
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger("test_signal_config_update")

def load_config() -> Dict[str, Any]:
    """Load the configuration file."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), '../../config/config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}

def test_signal_frequency_config():
    """Test the signal frequency tracking configuration."""
    logger.info("🔍 Testing Signal Frequency Configuration")
    logger.info("=" * 60)
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("❌ Failed to load configuration")
        return False
    
    # Check signal frequency tracking config
    sft_config = config.get('signal_frequency_tracking', {})
    
    if not sft_config:
        logger.error("❌ signal_frequency_tracking section not found")
        return False
    
    # Test 1: Check if enabled
    enabled = sft_config.get('enabled', False)
    logger.info(f"✅ Enabled: {enabled}")
    
    # Test 2: Check 3-hour analysis window
    analysis_window = sft_config.get('frequency_analysis_window', 0)
    expected_window = 10800  # 3 hours in seconds
    
    if analysis_window == expected_window:
        logger.info(f"✅ Analysis window: {analysis_window} seconds (3 hours)")
    else:
        logger.error(f"❌ Analysis window: {analysis_window} (expected {expected_window})")
        return False
    
    # Test 3: Check score improvement threshold
    score_threshold = sft_config.get('score_improvement_threshold', 0)
    expected_threshold = 3.0
    
    if score_threshold == expected_threshold:
        logger.info(f"✅ Score improvement threshold: {score_threshold} points")
    else:
        logger.error(f"❌ Score improvement threshold: {score_threshold} (expected {expected_threshold})")
        return False
    
    # Test 4: Check buy signal alerts configuration
    buy_alerts = sft_config.get('buy_signal_alerts', {})
    
    if buy_alerts:
        logger.info("✅ Buy signal alerts configuration found")
        
        # Check alert types
        alert_types = buy_alerts.get('alert_types', [])
        expected_types = ['score_improvement', 'recurrence', 'frequency_pattern', 'high_confidence']
        
        if all(t in alert_types for t in expected_types):
            logger.info(f"✅ Alert types: {alert_types}")
        else:
            logger.error(f"❌ Alert types missing: {alert_types}")
            return False
        
        # Check buy specific settings
        buy_settings = buy_alerts.get('buy_specific_settings', {})
        
        min_buy_score = buy_settings.get('min_buy_score', 0)
        if min_buy_score == 69:
            logger.info(f"✅ Minimum buy score: {min_buy_score}")
        else:
            logger.error(f"❌ Minimum buy score: {min_buy_score} (expected 69)")
            return False
        
        high_confidence = buy_settings.get('high_confidence_threshold', 0)
        if high_confidence == 75:
            logger.info(f"✅ High confidence threshold: {high_confidence}")
        else:
            logger.error(f"❌ High confidence threshold: {high_confidence} (expected 75)")
            return False
    else:
        logger.error("❌ Buy signal alerts configuration not found")
        return False
    
    # Test 5: Check signal updates configuration
    signal_updates = buy_alerts.get('signal_updates', {})
    
    if signal_updates:
        logger.info("✅ Signal updates configuration found")
        
        # Check thresholds
        thresholds = signal_updates.get('thresholds', {})
        
        high_priority_score = thresholds.get('high_priority_override_score', 0)
        if high_priority_score == 85.0:
            logger.info(f"✅ High priority override score: {high_priority_score}")
        else:
            logger.error(f"❌ High priority override score: {high_priority_score} (expected 85.0)")
            return False
        
        score_spike = thresholds.get('score_spike_threshold', 0)
        if score_spike == 10.0:
            logger.info(f"✅ Score spike threshold: {score_spike}")
        else:
            logger.error(f"❌ Score spike threshold: {score_spike} (expected 10.0)")
            return False
        
        volume_surge = thresholds.get('volume_surge_multiplier', 0)
        if volume_surge == 3.0:
            logger.info(f"✅ Volume surge multiplier: {volume_surge}")
        else:
            logger.error(f"❌ Volume surge multiplier: {volume_surge} (expected 3.0)")
            return False
        
        # Check notification style
        notification_style = signal_updates.get('notification_style', {})
        prefix = notification_style.get('prefix', '')
        
        if prefix == "📊 SIGNAL UPDATE":
            logger.info(f"✅ Notification prefix: {prefix}")
        else:
            logger.error(f"❌ Notification prefix: {prefix} (expected '📊 SIGNAL UPDATE')")
            return False
    else:
        logger.error("❌ Signal updates configuration not found")
        return False
    
    return True

def test_signal_tracking_config():
    """Test the signal tracking configuration."""
    logger.info("\n🔍 Testing Signal Tracking Configuration")
    logger.info("=" * 60)
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("❌ Failed to load configuration")
        return False
    
    # Check signal tracking config
    st_config = config.get('signal_tracking', {})
    
    if not st_config:
        logger.error("❌ signal_tracking section not found")
        return False
    
    # Test enabled status
    enabled = st_config.get('enabled', False)
    if enabled:
        logger.info(f"✅ Signal tracking enabled: {enabled}")
    else:
        logger.error(f"❌ Signal tracking disabled: {enabled}")
        return False
    
    # Test API URL
    api_url = st_config.get('api_url', '')
    expected_url = 'http://localhost:8001/api/signal-tracking'
    
    if api_url == expected_url:
        logger.info(f"✅ API URL: {api_url}")
    else:
        logger.error(f"❌ API URL: {api_url} (expected {expected_url})")
        return False
    
    return True

def simulate_signal_scenarios():
    """Simulate different signal scenarios to test configuration."""
    logger.info("\n🎯 Simulating Signal Scenarios")
    logger.info("=" * 60)
    
    # Load configuration
    config = load_config()
    sft_config = config.get('signal_frequency_tracking', {})
    
    # Scenario 1: Score improvement alert
    logger.info("\n📊 Scenario 1: Score Improvement Alert")
    prev_score = 70.0
    new_score = 73.5
    improvement = new_score - prev_score
    threshold = sft_config.get('score_improvement_threshold', 5.0)
    
    if improvement >= threshold:
        logger.info(f"✅ Would trigger alert: {improvement:.1f} >= {threshold}")
    else:
        logger.info(f"⚠️  Would NOT trigger alert: {improvement:.1f} < {threshold}")
    
    # Scenario 2: High priority override
    logger.info("\n📊 Scenario 2: High Priority Override")
    buy_alerts = sft_config.get('buy_signal_alerts', {})
    signal_updates = buy_alerts.get('signal_updates', {})
    thresholds = signal_updates.get('thresholds', {})
    high_priority_score = thresholds.get('high_priority_override_score', 85.0)
    
    test_score = 87.0
    if test_score >= high_priority_score:
        logger.info(f"✅ Would trigger high priority alert: {test_score} >= {high_priority_score}")
    else:
        logger.info(f"⚠️  Would NOT trigger high priority alert: {test_score} < {high_priority_score}")
    
    # Scenario 3: Volume surge
    logger.info("\n📊 Scenario 3: Volume Surge")
    volume_multiplier = thresholds.get('volume_surge_multiplier', 3.0)
    
    test_volume_increase = 4.2  # 420% increase
    if test_volume_increase >= volume_multiplier:
        logger.info(f"✅ Would trigger volume surge alert: {test_volume_increase}x >= {volume_multiplier}x")
    else:
        logger.info(f"⚠️  Would NOT trigger volume surge alert: {test_volume_increase}x < {volume_multiplier}x")
    
    # Scenario 4: Buy signal threshold
    logger.info("\n📊 Scenario 4: Buy Signal Threshold")
    buy_alerts = sft_config.get('buy_signal_alerts', {})
    buy_settings = buy_alerts.get('buy_specific_settings', {})
    min_buy_score = buy_settings.get('min_buy_score', 69)
    
    test_buy_score = 72.0
    if test_buy_score >= min_buy_score:
        logger.info(f"✅ Would trigger buy alert: {test_buy_score} >= {min_buy_score}")
    else:
        logger.info(f"⚠️  Would NOT trigger buy alert: {test_buy_score} < {min_buy_score}")
    
    return True

def main():
    """Main test function."""
    logger.info("🚀 Signal Configuration Update Test")
    logger.info("=" * 80)
    
    success = True
    
    # Test 1: Signal frequency tracking configuration
    if not test_signal_frequency_config():
        success = False
    
    # Test 2: Signal tracking configuration
    if not test_signal_tracking_config():
        success = False
    
    # Test 3: Simulate signal scenarios
    if not simulate_signal_scenarios():
        success = False
    
    # Final result
    logger.info("\n" + "=" * 80)
    if success:
        logger.info("✅ ALL TESTS PASSED! Configuration is working correctly.")
        logger.info("🎯 Your signal update system is ready for:")
        logger.info("   • 3-hour frequency analysis window")
        logger.info("   • 3+ point score improvement alerts")
        logger.info("   • High priority override at 85+ score")
        logger.info("   • Volume surge alerts at 3x+ increase")
        logger.info("   • Buy signal alerts at 69+ score")
        logger.info("   • Signal updates with clean notification style")
    else:
        logger.error("❌ SOME TESTS FAILED! Check configuration.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 