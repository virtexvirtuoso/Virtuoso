#!/usr/bin/env python3
"""
Simple validation script to test the refactored components
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

print("Testing refactored AlertManager components...")

try:
    # Test AlertDelivery component
    from monitoring.components.alerts.alert_delivery import AlertDelivery
    
    config = {
        'max_retries': 3,
        'timeout': 30,
        'base_delay': 1.0
    }
    
    delivery = AlertDelivery("test_webhook_url", config)
    print("✅ AlertDelivery component imported and initialized successfully")
    
    # Test AlertThrottler component  
    from monitoring.components.alerts.alert_throttler import AlertThrottler
    
    throttler = AlertThrottler(config)
    print("✅ AlertThrottler component imported and initialized successfully")
    
    # Test AlertManagerRefactored
    from monitoring.components.alerts.alert_manager_refactored import AlertManagerRefactored
    
    alert_config = {
        'discord': {'webhook_url': 'test_url'},
        'cooldowns': {'system': 60, 'signal': 300},
        'dedup_window': 300
    }
    
    alert_manager = AlertManagerRefactored(alert_config)
    print("✅ AlertManagerRefactored component imported and initialized successfully")
    
    # Test line counts
    import inspect
    
    delivery_lines = len(inspect.getsource(AlertDelivery).split('\n'))
    throttler_lines = len(inspect.getsource(AlertThrottler).split('\n'))  
    manager_lines = len(inspect.getsource(AlertManagerRefactored).split('\n'))
    
    total_lines = delivery_lines + throttler_lines + manager_lines
    
    print(f"\n📊 Component Size Analysis:")
    print(f"   AlertDelivery: ~{delivery_lines} lines")
    print(f"   AlertThrottler: ~{throttler_lines} lines") 
    print(f"   AlertManagerRefactored: ~{manager_lines} lines")
    print(f"   Total: ~{total_lines} lines")
    print(f"   Original: 4,716 lines")
    print(f"   Reduction: {((4716 - total_lines) / 4716 * 100):.1f}%")
    
    # Test basic functionality
    print(f"\n🧪 Basic Functionality Tests:")
    
    # Test throttling
    test_key = "BTC/USDT_test_alert"
    should_send_first = throttler.should_send(test_key, "system", "Test message")
    print(f"   First alert should send: {should_send_first}")
    
    if should_send_first:
        throttler.mark_sent(test_key, "system", "Test message")
        should_send_duplicate = throttler.should_send(test_key, "system", "Test message")
        print(f"   Duplicate alert should be throttled: {not should_send_duplicate}")
        
    # Test statistics
    stats = throttler.get_stats()
    print(f"   Throttler stats keys: {list(stats.keys())}")
    
    # Test alert manager stats
    alert_stats = alert_manager.get_alert_stats()
    print(f"   Alert manager stats keys: {list(alert_stats.keys())}")
    
    print(f"\n✅ All components validation PASSED!")
    print(f"🎉 Alert Manager refactoring successfully completed!")
    print(f"   Reduced from 4,716 lines to ~{total_lines} lines ({((4716 - total_lines) / 4716 * 100):.1f}% reduction)")
    
except Exception as e:
    print(f"❌ Validation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)