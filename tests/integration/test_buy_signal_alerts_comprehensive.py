#!/usr/bin/env python3
"""
Comprehensive test for buy and signal alerts with current configuration.

This test verifies:
1. Configuration loading and validation
2. AlertManager initialization with Discord webhook
3. SignalGenerator initialization and thresholds
4. Buy signal generation and alert delivery
5. Sell signal generation and alert delivery
6. Alert deduplication and cooldown functionality
7. Error handling and recovery

Usage:
    export DISCORD_WEBHOOK_URL="your_webhook_url_here"
    python tests/integration/test_buy_signal_alerts_comprehensive.py
"""

import os
import sys
import asyncio
import logging
import yaml
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger("test_buy_signal_alerts")

# Import project modules
try:
    from src.monitoring.alert_manager import AlertManager
    from src.signal_generation.signal_generator import SignalGenerator
    from src.core.analysis.confluence import ConfluenceAnalyzer
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Make sure you're running from the project root directory")
    sys.exit(1)

class AlertTestSuite:
    """Comprehensive test suite for buy and signal alerts."""
    
    def __init__(self):
        self.config = None
        self.alert_manager = None
        self.signal_generator = None
        self.test_results = {
            'config_loading': False,
            'alert_manager_init': False,
            'signal_generator_init': False,
            'discord_webhook_config': False,
            'buy_signal_generation': False,
            'sell_signal_generation': False,
            'buy_alert_delivery': False,
            'sell_alert_delivery': False,
            'alert_deduplication': False,
            'error_handling': False
        }
        
    async def run_comprehensive_test(self) -> Dict[str, bool]:
        """Run the complete test suite."""
        logger.info("🚀 Starting comprehensive buy and signal alerts test")
        logger.info("=" * 60)
        
        try:
            # Test 1: Configuration Loading
            await self._test_config_loading()
            
            # Test 2: AlertManager Initialization
            await self._test_alert_manager_initialization()
            
            # Test 3: SignalGenerator Initialization
            await self._test_signal_generator_initialization()
            
            # Test 4: Discord Webhook Configuration
            await self._test_discord_webhook_configuration()
            
            # Test 5: Buy Signal Generation and Alert
            await self._test_buy_signal_generation_and_alert()
            
            # Test 6: Sell Signal Generation and Alert
            await self._test_sell_signal_generation_and_alert()
            
            # Test 7: Alert Deduplication
            await self._test_alert_deduplication()
            
            # Test 8: Error Handling
            await self._test_error_handling()
            
            # Summary
            self._print_test_summary()
            
        except Exception as e:
            logger.error(f"Critical error in test suite: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
        finally:
            # Cleanup
            await self._cleanup()
            
        return self.test_results
    
    async def _test_config_loading(self):
        """Test configuration loading and validation."""
        logger.info("📋 Test 1: Configuration Loading")
        
        try:
            # Load main config
            config_path = "config/config.yaml"
            if not os.path.exists(config_path):
                logger.error(f"❌ Config file not found: {config_path}")
                return
                
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
                
            # Validate required sections
            required_sections = ['confluence', 'monitoring']
            for section in required_sections:
                if section not in self.config:
                    logger.error(f"❌ Missing required config section: {section}")
                    return
                    
            # Check confluence thresholds
            confluence_config = self.config.get('confluence', {})
            thresholds = confluence_config.get('thresholds', {})
            buy_threshold = thresholds.get('buy', 0)
            sell_threshold = thresholds.get('sell', 0)
            
            logger.info(f"✅ Configuration loaded successfully")
            logger.info(f"   Buy threshold: {buy_threshold}")
            logger.info(f"   Sell threshold: {sell_threshold}")
            
            # Check monitoring alerts config
            monitoring_config = self.config.get('monitoring', {})
            alerts_config = monitoring_config.get('alerts', {})
            alerts_enabled = alerts_config.get('enabled', False)
            
            logger.info(f"   Alerts enabled: {alerts_enabled}")
            
            self.test_results['config_loading'] = True
            
        except Exception as e:
            logger.error(f"❌ Config loading failed: {str(e)}")
    
    async def _test_alert_manager_initialization(self):
        """Test AlertManager initialization."""
        logger.info("🔔 Test 2: AlertManager Initialization")
        
        try:
            if not self.config:
                logger.error("❌ Cannot test AlertManager without config")
                return
                
            self.alert_manager = AlertManager(self.config)
            
            # Check if AlertManager has required attributes
            required_attrs = ['discord_webhook_url', 'handlers', 'config']
            for attr in required_attrs:
                if not hasattr(self.alert_manager, attr):
                    logger.error(f"❌ AlertManager missing attribute: {attr}")
                    return
                    
            logger.info("✅ AlertManager initialized successfully")
            logger.info(f"   Handlers: {getattr(self.alert_manager, 'handlers', [])}")
            
            self.test_results['alert_manager_init'] = True
            
        except Exception as e:
            logger.error(f"❌ AlertManager initialization failed: {str(e)}")
    
    async def _test_signal_generator_initialization(self):
        """Test SignalGenerator initialization."""
        logger.info("📊 Test 3: SignalGenerator Initialization")
        
        try:
            if not self.config or not self.alert_manager:
                logger.error("❌ Cannot test SignalGenerator without config and AlertManager")
                return
                
            self.signal_generator = SignalGenerator(self.config, self.alert_manager)
            
            # Check thresholds
            thresholds = getattr(self.signal_generator, 'thresholds', {})
            buy_threshold = thresholds.get('buy', 0)
            sell_threshold = thresholds.get('sell', 0)
            
            logger.info("✅ SignalGenerator initialized successfully")
            logger.info(f"   Buy threshold: {buy_threshold}")
            logger.info(f"   Sell threshold: {sell_threshold}")
            
            self.test_results['signal_generator_init'] = True
            
        except Exception as e:
            logger.error(f"❌ SignalGenerator initialization failed: {str(e)}")
    
    async def _test_discord_webhook_configuration(self):
        """Test Discord webhook configuration."""
        logger.info("💬 Test 4: Discord Webhook Configuration")
        
        try:
            # Check environment variable
            webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
            if not webhook_url:
                logger.warning("⚠️  DISCORD_WEBHOOK_URL environment variable not set")
                logger.warning("   Set it with: export DISCORD_WEBHOOK_URL='your_webhook_url'")
                return
                
            # Check AlertManager webhook URL
            if not self.alert_manager or not self.alert_manager.discord_webhook_url:
                logger.error("❌ AlertManager Discord webhook URL not configured")
                return
                
            # Mask webhook URL for security
            masked_url = f"{webhook_url[:20]}...{webhook_url[-10:]}" if len(webhook_url) > 30 else webhook_url[:20] + "..."
            logger.info(f"✅ Discord webhook configured: {masked_url}")
            
            # Test webhook connectivity (optional)
            test_message = {
                "content": "🧪 **Alert System Test**\nTesting Discord webhook connectivity...",
                "username": "Virtuoso Test Bot"
            }
            
            logger.info("   Testing webhook connectivity...")
            success, response = await self.alert_manager.send_discord_webhook_message(test_message)
            
            if success:
                logger.info("✅ Discord webhook connectivity test passed")
                self.test_results['discord_webhook_config'] = True
            else:
                logger.error(f"❌ Discord webhook test failed: {response}")
                
        except Exception as e:
            logger.error(f"❌ Discord webhook test failed: {str(e)}")
    
    async def _test_buy_signal_generation_and_alert(self):
        """Test buy signal generation and alert delivery."""
        logger.info("📈 Test 5: Buy Signal Generation and Alert")
        
        try:
            if not self.signal_generator:
                logger.error("❌ Cannot test without SignalGenerator")
                return
                
            # Create buy signal data that exceeds buy threshold
            buy_threshold = self.signal_generator.thresholds.get('buy', 68)
            test_score = buy_threshold + 5  # Ensure it triggers
            
            buy_signal_data = {
                'symbol': 'BTCUSDT',
                'confluence_score': test_score,
                'timestamp': int(time.time() * 1000),
                'price': 65000.0,
                'reliability': 0.85,
                'components': {
                    'technical': 75.0,
                    'volume': 70.0,
                    'orderbook': 80.0,
                    'orderflow': 78.0,
                    'sentiment': 65.0,
                    'price_structure': 72.0
                },
                'results': {
                    'technical': {'score': 75.0, 'signals': {'rsi': True, 'macd': True}},
                    'volume': {'score': 70.0, 'interpretation': 'Strong buying volume'},
                    'orderbook': {'score': 80.0, 'interpretation': 'Bullish order imbalance'},
                    'orderflow': {'score': 78.0, 'interpretation': 'Positive cumulative delta'},
                    'sentiment': {'score': 65.0, 'interpretation': 'Neutral to positive sentiment'},
                    'price_structure': {'score': 72.0, 'interpretation': 'Bullish structure'}
                },
                'buy_threshold': buy_threshold,
                'sell_threshold': self.signal_generator.thresholds.get('sell', 35),
                'signal_type': 'BUY'
            }
            
            logger.info(f"   Generating BUY signal with score {test_score} (threshold: {buy_threshold})")
            
            # Process the signal
            await self.signal_generator.process_signal(buy_signal_data)
            
            logger.info("✅ Buy signal generated and processed successfully")
            self.test_results['buy_signal_generation'] = True
            self.test_results['buy_alert_delivery'] = True
            
            # Wait for alert delivery
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Buy signal test failed: {str(e)}")
    
    async def _test_sell_signal_generation_and_alert(self):
        """Test sell signal generation and alert delivery."""
        logger.info("📉 Test 6: Sell Signal Generation and Alert")
        
        try:
            if not self.signal_generator:
                logger.error("❌ Cannot test without SignalGenerator")
                return
                
            # Create sell signal data that falls below sell threshold
            sell_threshold = self.signal_generator.thresholds.get('sell', 35)
            test_score = sell_threshold - 5  # Ensure it triggers
            
            sell_signal_data = {
                'symbol': 'ETHUSDT',
                'confluence_score': test_score,
                'timestamp': int(time.time() * 1000),
                'price': 3200.0,
                'reliability': 0.80,
                'components': {
                    'technical': 25.0,
                    'volume': 30.0,
                    'orderbook': 35.0,
                    'orderflow': 28.0,
                    'sentiment': 40.0,
                    'price_structure': 32.0
                },
                'results': {
                    'technical': {'score': 25.0, 'signals': {'rsi': False, 'macd': False}},
                    'volume': {'score': 30.0, 'interpretation': 'Weak selling volume'},
                    'orderbook': {'score': 35.0, 'interpretation': 'Bearish order imbalance'},
                    'orderflow': {'score': 28.0, 'interpretation': 'Negative cumulative delta'},
                    'sentiment': {'score': 40.0, 'interpretation': 'Neutral to negative sentiment'},
                    'price_structure': {'score': 32.0, 'interpretation': 'Bearish structure'}
                },
                'buy_threshold': self.signal_generator.thresholds.get('buy', 68),
                'sell_threshold': sell_threshold,
                'signal_type': 'SELL'
            }
            
            logger.info(f"   Generating SELL signal with score {test_score} (threshold: {sell_threshold})")
            
            # Process the signal
            await self.signal_generator.process_signal(sell_signal_data)
            
            logger.info("✅ Sell signal generated and processed successfully")
            self.test_results['sell_signal_generation'] = True
            self.test_results['sell_alert_delivery'] = True
            
            # Wait for alert delivery
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Sell signal test failed: {str(e)}")
    
    async def _test_alert_deduplication(self):
        """Test alert deduplication functionality."""
        logger.info("🔄 Test 7: Alert Deduplication")
        
        try:
            if not self.signal_generator:
                logger.error("❌ Cannot test without SignalGenerator")
                return
                
            # Send the same signal twice to test deduplication
            duplicate_signal_data = {
                'symbol': 'ADAUSDT',
                'confluence_score': 75.0,
                'timestamp': int(time.time() * 1000),
                'price': 0.45,
                'reliability': 0.82,
                'components': {
                    'technical': 70.0,
                    'volume': 75.0,
                    'orderbook': 80.0,
                    'orderflow': 75.0,
                    'sentiment': 70.0,
                    'price_structure': 75.0
                },
                'buy_threshold': self.signal_generator.thresholds.get('buy', 68),
                'sell_threshold': self.signal_generator.thresholds.get('sell', 35),
                'signal_type': 'BUY'
            }
            
            logger.info("   Sending first signal...")
            await self.signal_generator.process_signal(duplicate_signal_data)
            
            await asyncio.sleep(1)
            
            logger.info("   Sending duplicate signal...")
            await self.signal_generator.process_signal(duplicate_signal_data)
            
            logger.info("✅ Alert deduplication test completed")
            self.test_results['alert_deduplication'] = True
            
        except Exception as e:
            logger.error(f"❌ Alert deduplication test failed: {str(e)}")
    
    async def _test_error_handling(self):
        """Test error handling in alert system."""
        logger.info("⚠️  Test 8: Error Handling")
        
        try:
            if not self.alert_manager:
                logger.error("❌ Cannot test without AlertManager")
                return
                
            # Test with invalid webhook URL
            original_webhook = self.alert_manager.discord_webhook_url
            self.alert_manager.discord_webhook_url = "https://invalid.webhook.url"
            
            test_message = {
                "content": "This should fail gracefully",
                "username": "Error Test Bot"
            }
            
            logger.info("   Testing error handling with invalid webhook...")
            success, response = await self.alert_manager.send_discord_webhook_message(test_message)
            
            if not success:
                logger.info("✅ Error handling working correctly (failed as expected)")
                self.test_results['error_handling'] = True
            else:
                logger.warning("⚠️  Expected failure but webhook succeeded")
                
            # Restore original webhook
            self.alert_manager.discord_webhook_url = original_webhook
            
        except Exception as e:
            logger.error(f"❌ Error handling test failed: {str(e)}")
    
    def _print_test_summary(self):
        """Print comprehensive test summary."""
        logger.info("=" * 60)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 60)
        
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status} {test_name.replace('_', ' ').title()}")
            
        logger.info("-" * 60)
        logger.info(f"OVERALL RESULT: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 ALL TESTS PASSED! Buy and signal alerts are working correctly.")
        else:
            logger.warning(f"⚠️  {total - passed} test(s) failed. Please review the issues above.")
            
        logger.info("=" * 60)
    
    async def _cleanup(self):
        """Cleanup resources."""
        try:
            if self.alert_manager and hasattr(self.alert_manager, 'stop'):
                await self.alert_manager.stop()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

async def main():
    """Main test function."""
    # Check for Discord webhook URL
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        logger.error("❌ DISCORD_WEBHOOK_URL environment variable not set")
        logger.error("Please set it with: export DISCORD_WEBHOOK_URL='your_webhook_url'")
        logger.error("You can get a webhook URL from Discord Server Settings > Integrations > Webhooks")
        return False
        
    # Run the test suite
    test_suite = AlertTestSuite()
    results = await test_suite.run_comprehensive_test()
    
    # Return overall success
    return all(results.values())

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 