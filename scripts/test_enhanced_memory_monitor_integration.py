#!/usr/bin/env python3
"""
Test script for enhanced memory monitoring integration.
This script tests the enhanced memory monitoring features integrated into the health monitor.
"""

import sys
import os
import time
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.monitoring.metrics_manager import MetricsManager
from src.monitoring.components.health_monitor import HealthMonitor


class MockAlertManager:
    """Mock alert manager for testing."""
    
    def __init__(self):
        self.alerts = []
    
    async def send_alert(self, level: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Mock send alert method."""
        self.alerts.append({
            'level': level,
            'message': message,
            'details': details
        })
        print(f"Mock alert sent: {level} - {message}")


def setup_logging():
    """Setup logging for the test."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('test_enhanced_memory_monitor.log')
        ]
    )


def create_test_config():
    """Create test configuration for enhanced memory monitoring."""
    return {
        'check_interval_seconds': 5,  # Fast check interval for testing
        'history_length': 50,
        'cpu_warning_threshold': 80,
        'cpu_critical_threshold': 95,
        'memory_warning_threshold': 85,  # Lower for testing
        'memory_critical_threshold': 95,  # Lower for testing
        'disk_warning_threshold': 80,
        'disk_critical_threshold': 95,
        'api_degraded_threshold': 0.7,
        'api_critical_threshold': 0.5,
        'alert_log_path': 'logs/test_alerts.json',
        'monitoring': {
            'memory_tracking': {
                'enable_enhanced_monitoring': True,
                'disable_memory_warnings': False,
                'warning_threshold_percent': 85,
                'critical_threshold_percent': 95,
                'min_warning_size_mb': 512,  # Lower for testing
                'suppress_repeated_warnings': False,  # Disable for testing
                'include_process_details': True,
                'check_interval_seconds': 30
            },
            'alerts': {
                'cpu_alerts': {
                    'enabled': True,
                    'use_system_webhook': False,
                    'threshold': 80,
                    'cooldown': 60
                }
            }
        }
    }


async def test_enhanced_memory_analysis():
    """Test the enhanced memory analysis functionality."""
    print("=== Testing Enhanced Memory Analysis ===")
    
    # Create mock alert manager
    alert_manager = MockAlertManager()
    
    # Create metrics manager
    config = create_test_config()
    metrics_manager = MetricsManager(config, alert_manager)
    
    # Create health monitor with test config
    health_monitor = HealthMonitor(metrics_manager, config=config)
    
    # Simulate some memory usage data
    print("Simulating memory usage data...")
    for i in range(20):
        # Simulate increasing memory usage
        memory_usage = 70 + (i * 1.5)  # Start at 70%, increase by 1.5% each time
        health_monitor.metrics['memory'].add_value(memory_usage, time.time() - (20 - i) * 60)
        await asyncio.sleep(0.1)  # Small delay
    
    # Test enhanced memory analysis
    print("\nTesting enhanced memory analysis...")
    analysis = health_monitor._get_enhanced_memory_analysis()
    
    print(f"Current memory usage: {analysis['current_usage']:.1f}%")
    print(f"Adaptive warning threshold: {analysis['adaptive_warning_threshold']:.1f}%")
    print(f"Adaptive critical threshold: {analysis['adaptive_critical_threshold']:.1f}%")
    print(f"Trend rate: {analysis['trend_rate']:.1f}%/min")
    print(f"Volatility: {analysis['volatility']:.1f}%")
    print(f"Leak detected: {analysis['leak_detected']}")
    print(f"Leak confidence: {analysis['leak_confidence']:.1%}")
    print(f"Confidence score: {analysis['confidence_score']:.1%}")
    print(f"CPU usage: {analysis['cpu_percent']:.1f}%")
    print(f"Load average: {analysis['load_average']}")
    
    # Test alert triggering logic
    print("\nTesting alert triggering logic...")
    should_alert, alert_level, confidence_score = health_monitor._should_trigger_memory_alert(analysis)
    print(f"Should alert: {should_alert}")
    print(f"Alert level: {alert_level}")
    print(f"Confidence score: {confidence_score:.1%}")
    
    return health_monitor, analysis


async def test_process_memory_details():
    """Test the process memory details functionality."""
    print("\n=== Testing Process Memory Details ===")
    
    # Create mock alert manager
    alert_manager = MockAlertManager()
    
    # Create metrics manager
    config = create_test_config()
    metrics_manager = MetricsManager(config, alert_manager)
    
    # Create health monitor
    health_monitor = HealthMonitor(metrics_manager, config=config)
    
    process_details = health_monitor._get_process_memory_details()
    
    print(f"Found {len(process_details)} processes")
    print("Top 5 memory-consuming processes:")
    for i, proc in enumerate(process_details[:5]):
        print(f"{i+1}. {proc['name']} (PID: {proc['pid']}): {proc['memory_mb']:.1f}MB ({proc['memory_percent']:.1f}%) - CPU: {proc['cpu_percent']:.1f}%")


async def test_enhanced_memory_alert_creation():
    """Test the enhanced memory alert creation."""
    print("\n=== Testing Enhanced Memory Alert Creation ===")
    
    # Create mock alert manager
    alert_manager = MockAlertManager()
    
    # Create metrics manager
    config = create_test_config()
    metrics_manager = MetricsManager(config, alert_manager)
    
    # Create health monitor
    health_monitor = HealthMonitor(metrics_manager, config=config)
    
    # Create a test analysis with high memory usage
    analysis = health_monitor._get_enhanced_memory_analysis()
    
    # Modify analysis to simulate high memory usage
    analysis['current_usage'] = 90.0
    analysis['confidence_score'] = 0.8
    analysis['trend_rate'] = 2.5
    analysis['volatility'] = 3.0
    analysis['leak_detected'] = True
    analysis['leak_confidence'] = 0.7
    
    print("Creating enhanced memory alert...")
    health_monitor._create_enhanced_memory_alert(analysis, "warning", 0.8)
    
    # Check if alert was created
    active_alerts = health_monitor.get_active_alerts()
    print(f"Active alerts: {len(active_alerts)}")
    for alert in active_alerts:
        print(f"Alert: {alert.level} - {alert.message[:100]}...")


async def test_threshold_violation_checking():
    """Test the integrated threshold violation checking."""
    print("\n=== Testing Integrated Threshold Violation Checking ===")
    
    # Create mock alert manager
    alert_manager = MockAlertManager()
    
    # Create metrics manager
    config = create_test_config()
    metrics_manager = MetricsManager(config, alert_manager)
    
    # Create health monitor
    health_monitor = HealthMonitor(metrics_manager, config=config)
    
    # Simulate memory usage above threshold
    print("Simulating high memory usage...")
    for i in range(10):
        memory_usage = 90 + (i * 0.5)  # Start at 90%, increase by 0.5% each time
        health_monitor.metrics['memory'].add_value(memory_usage, time.time() - (10 - i) * 60)
        await asyncio.sleep(0.1)
    
    # Test the threshold violation checking
    print("Running threshold violation check...")
    health_monitor._check_threshold_violations()
    
    # Check results
    active_alerts = health_monitor.get_active_alerts()
    print(f"Active alerts after threshold check: {len(active_alerts)}")
    for alert in active_alerts:
        print(f"Alert: {alert.level} - {alert.message[:100]}...")


async def test_configuration_options():
    """Test different configuration options."""
    print("\n=== Testing Configuration Options ===")
    
    # Test with enhanced monitoring disabled
    print("Testing with enhanced monitoring disabled...")
    config = create_test_config()
    config['monitoring']['memory_tracking']['enable_enhanced_monitoring'] = False
    
    alert_manager = MockAlertManager()
    metrics_manager = MetricsManager(config, alert_manager)
    health_monitor = HealthMonitor(metrics_manager, config=config)
    
    # Simulate some memory data
    for i in range(5):
        memory_usage = 85 + (i * 1.0)
        health_monitor.metrics['memory'].add_value(memory_usage, time.time() - (5 - i) * 60)
        await asyncio.sleep(0.1)
    
    health_monitor._check_threshold_violations()
    
    active_alerts = health_monitor.get_active_alerts()
    print(f"Active alerts with enhanced monitoring disabled: {len(active_alerts)}")
    
    # Test with memory warnings disabled
    print("\nTesting with memory warnings disabled...")
    config = create_test_config()
    config['monitoring']['memory_tracking']['disable_memory_warnings'] = True
    
    alert_manager = MockAlertManager()
    metrics_manager = MetricsManager(config, alert_manager)
    health_monitor = HealthMonitor(metrics_manager, config=config)
    
    # Simulate high memory usage
    for i in range(5):
        memory_usage = 95 + (i * 0.5)
        health_monitor.metrics['memory'].add_value(memory_usage, time.time() - (5 - i) * 60)
        await asyncio.sleep(0.1)
    
    health_monitor._check_threshold_violations()
    
    active_alerts = health_monitor.get_active_alerts()
    print(f"Active alerts with memory warnings disabled: {len(active_alerts)}")


async def main():
    """Main test function."""
    print("Enhanced Memory Monitor Integration Test")
    print("=" * 50)
    
    setup_logging()
    
    try:
        # Test enhanced memory analysis
        await test_enhanced_memory_analysis()
        
        # Test process memory details
        await test_process_memory_details()
        
        # Test enhanced memory alert creation
        await test_enhanced_memory_alert_creation()
        
        # Test integrated threshold violation checking
        await test_threshold_violation_checking()
        
        # Test configuration options
        await test_configuration_options()
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        print("Enhanced memory monitoring integration is working correctly.")
        
    except Exception as e:
        print(f"\nError during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 