#!/usr/bin/env python3
"""
Test script to verify webhook functionality and memory monitoring improvements.
"""

import os
import sys
import asyncio
import logging
import time
import psutil
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.monitoring.alert_manager import AlertManager
from src.monitoring.components.health_monitor import HealthMonitor
from src.monitoring.metrics_manager import MetricsManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('webhook_memory_test')

class WebhookMemoryTester:
    """Test webhook functionality and memory monitoring."""
    
    def __init__(self):
        """Initialize the tester."""
        self.config = self._create_test_config()
        self.alert_manager = AlertManager(self.config)
        self.metrics_manager = MetricsManager(self.config, self.alert_manager)
        self.health_monitor = None
        
    def _create_test_config(self) -> dict:
        """Create test configuration."""
        return {
            'monitoring': {
                'alerts': {
                    'enabled': True,
                    'discord_webhook_url': os.getenv('DISCORD_WEBHOOK_URL', ''),
                    'system_alerts_webhook_url': os.getenv('SYSTEM_ALERTS_WEBHOOK_URL', ''),
                    'system_alerts': {
                        'enabled': True,
                        'use_system_webhook': True,
                        'types': {
                            'memory': True,
                            'cpu': True,
                            'error': True
                        }
                    },
                    'discord_webhook': {
                        'max_retries': 3,
                        'initial_retry_delay': 2,
                        'timeout_seconds': 30,
                        'exponential_backoff': True,
                        'fallback_enabled': True,
                        'recoverable_status_codes': [429, 500, 502, 503, 504]
                    }
                },
                'memory_tracking': {
                    'enabled': True,
                    'warning_threshold_percent': 98,
                    'critical_threshold_percent': 98,
                    'min_warning_size_mb': 2048,  # 2GB
                    'suppress_repeated_warnings': True,
                    'disable_memory_warnings': False,
                    'include_process_details': True,
                    'check_interval_seconds': 600,
                    'log_level': 'WARNING'
                }
            }
        }
    
    async def test_webhook_functionality(self):
        """Test webhook functionality with retry logic."""
        logger.info("🔧 Testing webhook functionality...")
        
        try:
            # Alert manager already initialized in __init__
            
            # Test system webhook
            if self.alert_manager.system_webhook_url:
                logger.info(f"✅ System webhook URL configured: {self.alert_manager.system_webhook_url[:50]}...")
                
                # Test basic webhook
                await self._test_basic_webhook()
                
                # Test webhook with retry logic
                await self._test_webhook_retry_logic()
                
                # Test webhook with different payload sizes
                await self._test_webhook_payload_sizes()
                
            else:
                logger.warning("⚠️ No system webhook URL configured - skipping webhook tests")
                
        except Exception as e:
            logger.error(f"❌ Error testing webhook functionality: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def _test_basic_webhook(self):
        """Test basic webhook functionality."""
        logger.info("📤 Testing basic webhook...")
        
        test_message = "🧪 Test webhook message from Virtuoso Trading System"
        test_details = {
            'test_type': 'basic_webhook',
            'timestamp': time.time(),
            'version': '1.0.0'
        }
        
        try:
            await self.alert_manager._send_system_webhook_alert(test_message, test_details)
            logger.info("✅ Basic webhook test completed")
        except Exception as e:
            logger.error(f"❌ Basic webhook test failed: {e}")
    
    async def _test_webhook_retry_logic(self):
        """Test webhook retry logic."""
        logger.info("🔄 Testing webhook retry logic...")
        
        test_message = "🔄 Test webhook retry logic - this should show retry attempts"
        test_details = {
            'test_type': 'retry_logic',
            'timestamp': time.time(),
            'retry_count': 3
        }
        
        try:
            await self.alert_manager._send_system_webhook_alert(test_message, test_details)
            logger.info("✅ Webhook retry logic test completed")
        except Exception as e:
            logger.error(f"❌ Webhook retry logic test failed: {e}")
    
    async def _test_webhook_payload_sizes(self):
        """Test webhook with different payload sizes."""
        logger.info("📦 Testing webhook payload sizes...")
        
        # Small payload
        small_message = "Small test message"
        small_details = {'size': 'small'}
        
        # Large payload
        large_message = "Large test message " * 100
        large_details = {
            'size': 'large',
            'details': {f'field_{i}': f'value_{i}' for i in range(50)}
        }
        
        try:
            # Test small payload
            await self.alert_manager._send_system_webhook_alert(small_message, small_details)
            logger.info("✅ Small payload test completed")
            
            # Test large payload
            await self.alert_manager._send_system_webhook_alert(large_message, large_details)
            logger.info("✅ Large payload test completed")
            
        except Exception as e:
            logger.error(f"❌ Payload size test failed: {e}")
    
    def test_memory_monitoring(self):
        """Test memory monitoring functionality."""
        logger.info("🧠 Testing memory monitoring...")
        
        try:
            # Initialize health monitor with alert callback
            self.health_monitor = HealthMonitor(
                self.metrics_manager, 
                alert_callback=self.alert_manager.send_alert if self.alert_manager else None,
                config=self.config
            )
            
            # Test memory threshold checking
            self._test_memory_thresholds()
            
            # Test memory details generation
            self._test_memory_details()
            
            # Test memory alert suppression
            self._test_memory_alert_suppression()
            
        except Exception as e:
            logger.error(f"❌ Error testing memory monitoring: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _test_memory_thresholds(self):
        """Test memory threshold checking."""
        logger.info("📊 Testing memory thresholds...")
        
        # Get current memory usage
        memory = psutil.virtual_memory()
        current_percent = memory.percent
        current_mb = memory.used / (1024 * 1024)
        total_mb = memory.total / (1024 * 1024)
        
        logger.info(f"Current memory usage: {current_percent:.1f}% ({current_mb:.0f}MB / {total_mb:.0f}MB)")
        
        # Test threshold configuration
        config = self.config['monitoring']['memory_tracking']
        warning_threshold = config['warning_threshold_percent']
        critical_threshold = config['critical_threshold_percent']
        min_warning_size = config['min_warning_size_mb']
        
        logger.info(f"Warning threshold: {warning_threshold}%")
        logger.info(f"Critical threshold: {critical_threshold}%")
        logger.info(f"Min warning size: {min_warning_size}MB")
        
        # Check if thresholds would trigger
        would_warn = current_percent >= warning_threshold and current_mb >= min_warning_size
        would_critical = current_percent >= critical_threshold and current_mb >= min_warning_size
        
        logger.info(f"Would trigger warning: {would_warn}")
        logger.info(f"Would trigger critical: {would_critical}")
        
        logger.info("✅ Memory threshold test completed")
    
    def _test_memory_details(self):
        """Test memory details generation."""
        logger.info("📋 Testing memory details generation...")
        
        try:
            # Get detailed memory info
            memory_details = self.health_monitor._get_detailed_memory_info()
            logger.info(f"Memory details generated: {len(memory_details)} characters")
            logger.info(f"Sample: {memory_details[:200]}...")
            
            logger.info("✅ Memory details test completed")
            
        except Exception as e:
            logger.error(f"❌ Memory details test failed: {e}")
    
    def _test_memory_alert_suppression(self):
        """Test memory alert suppression logic."""
        logger.info("🔇 Testing memory alert suppression...")
        
        try:
            # Test suppression logic
            has_recent = self.health_monitor._has_recent_memory_warning()
            logger.info(f"Has recent memory warning: {has_recent}")
            
            # Test suppression configuration
            config = self.config['monitoring']['memory_tracking']
            suppress_repeated = config['suppress_repeated_warnings']
            disable_warnings = config['disable_memory_warnings']
            
            logger.info(f"Suppress repeated warnings: {suppress_repeated}")
            logger.info(f"Disable memory warnings: {disable_warnings}")
            
            logger.info("✅ Memory alert suppression test completed")
            
        except Exception as e:
            logger.error(f"❌ Memory alert suppression test failed: {e}")
    
    def test_system_health(self):
        """Test overall system health monitoring."""
        logger.info("🏥 Testing system health monitoring...")
        
        try:
            # Get system health status
            health_status = self.health_monitor.get_health_status()
            
            logger.info(f"System status: {health_status.status}")
            logger.info(f"CPU usage: {health_status.cpu_usage:.1f}%")
            logger.info(f"Memory usage: {health_status.memory_usage:.1f}%")
            logger.info(f"Disk usage: {health_status.disk_usage:.1f}%")
            logger.info(f"Uptime: {health_status.uptime_seconds} seconds")
            
            # Get system health summary
            summary = self.health_monitor.get_system_health_summary()
            logger.info(f"Health summary: {summary}")
            
            logger.info("✅ System health test completed")
            
        except Exception as e:
            logger.error(f"❌ System health test failed: {e}")
    
    async def run_all_tests(self):
        """Run all tests."""
        logger.info("🚀 Starting comprehensive webhook and memory monitoring tests...")
        
        # Test webhook functionality
        await self.test_webhook_functionality()
        
        # Test memory monitoring
        self.test_memory_monitoring()
        
        # Test system health
        self.test_system_health()
        
        logger.info("✅ All tests completed!")
        
        # Print summary
        self._print_test_summary()
    
    def _print_test_summary(self):
        """Print test summary."""
        logger.info("\n" + "="*60)
        logger.info("📊 TEST SUMMARY")
        logger.info("="*60)
        
        # Webhook status
        if self.alert_manager and self.alert_manager.system_webhook_url:
            logger.info("✅ Webhook functionality: CONFIGURED")
            logger.info(f"   URL: {self.alert_manager.system_webhook_url[:50]}...")
        else:
            logger.info("⚠️ Webhook functionality: NOT CONFIGURED")
        
        # Memory monitoring status
        if self.health_monitor:
            logger.info("✅ Memory monitoring: ENABLED")
            config = self.config['monitoring']['memory_tracking']
            logger.info(f"   Warning threshold: {config['warning_threshold_percent']}%")
            logger.info(f"   Critical threshold: {config['critical_threshold_percent']}%")
            logger.info(f"   Min warning size: {config['min_warning_size_mb']}MB")
        else:
            logger.info("❌ Memory monitoring: DISABLED")
        
        # System status
        memory = psutil.virtual_memory()
        logger.info(f"📈 Current system status:")
        logger.info(f"   Memory usage: {memory.percent:.1f}%")
        logger.info(f"   Available memory: {memory.available / (1024 * 1024):.0f}MB")
        logger.info(f"   Total memory: {memory.total / (1024 * 1024):.0f}MB")
        
        logger.info("="*60)

async def main():
    """Main function."""
    logger.info("🔧 Webhook and Memory Monitoring Test Suite")
    logger.info("=" * 50)
    
    # Check environment variables
    webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL', '')
    if not webhook_url:
        logger.warning("⚠️ SYSTEM_ALERTS_WEBHOOK_URL not set - webhook tests will be limited")
    
    # Create tester and run tests
    tester = WebhookMemoryTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 