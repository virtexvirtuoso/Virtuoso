#!/usr/bin/env python3
"""
Comprehensive test for buy and signal alerts with current configuration.

This test verifies:
1. Configuration loading and validation
2. AlertManager initialization with Discord webhook
3. SignalGenerator initialization and thresholds
4. Buy signal generation and alert delivery
5. Sell signal generation and alert delivery

Usage:
    export DISCORD_WEBHOOK_URL="your_webhook_url_here"
    python scripts/testing/test_buy_signal_alerts.py
"""

import os
import sys
import asyncio
import logging
import yaml
import time
from datetime import datetime
from typing import Dict, Any

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
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Make sure you're running from the project root directory")
    sys.exit(1)

class AlertTestSuite:
    """Test suite for buy and signal alerts."""
    
    def __init__(self):
        self.config = None
        self.alert_manager = None
        self.signal_generator = None
        self.test_results = {}
        
    async def run_test(self) -> Dict[str, bool]:
        """Run the complete test suite."""
        logger.info("🚀 Starting buy and signal alerts test")
        logger.info("=" * 60)
        
        try:
            # Test 1: Load Configuration
            await self._test_config_loading()
            
            # Test 2: Initialize AlertManager
            await self._test_alert_manager_init()
            
            # Test 3: Initialize SignalGenerator
            await self._test_signal_generator_init()
            
            # Test 4: Test Discord Webhook
            await self._test_discord_webhook()
            
            # Test 5: Test Buy Signal
            await self._test_buy_signal()
            
            # Test 6: Test Sell Signal
            await self._test_sell_signal()
            
            # Summary
            self._print_summary()
            
        except Exception as e:
            logger.error(f"Critical error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
        finally:
            await self._cleanup()
            
        return self.test_results
    
    async def _test_config_loading(self):
        """Test configuration loading."""
        logger.info("📋 Test 1: Configuration Loading")
        
        try:
            config_path = "config/config.yaml"
            if not os.path.exists(config_path):
                logger.error(f"❌ Config file not found: {config_path}")
                self.test_results['config_loading'] = False
                return
                
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
                
            # Check required sections
            if 'confluence' not in self.config or 'monitoring' not in self.config:
                logger.error("❌ Missing required config sections")
                self.test_results['config_loading'] = False
                return
                
            # Get thresholds
            thresholds = self.config.get('confluence', {}).get('thresholds', {})
            buy_threshold = thresholds.get('buy', 0)
            sell_threshold = thresholds.get('sell', 0)
            
            logger.info(f"✅ Configuration loaded successfully")
            logger.info(f"   Buy threshold: {buy_threshold}")
            logger.info(f"   Sell threshold: {sell_threshold}")
            
            self.test_results['config_loading'] = True
            
        except Exception as e:
            logger.error(f"❌ Config loading failed: {str(e)}")
            self.test_results['config_loading'] = False
    
    async def _test_alert_manager_init(self):
        """Test AlertManager initialization."""
        logger.info("🔔 Test 2: AlertManager Initialization")
        
        try:
            if not self.config:
                logger.error("❌ Cannot test without config")
                self.test_results['alert_manager_init'] = False
                return
                
            self.alert_manager = AlertManager(self.config)
            
            logger.info("✅ AlertManager initialized successfully")
            self.test_results['alert_manager_init'] = True
            
        except Exception as e:
            logger.error(f"❌ AlertManager initialization failed: {str(e)}")
            self.test_results['alert_manager_init'] = False
    
    async def _test_signal_generator_init(self):
        """Test SignalGenerator initialization."""
        logger.info("📊 Test 3: SignalGenerator Initialization")
        
        try:
            if not self.config or not self.alert_manager:
                logger.error("❌ Cannot test without config and AlertManager")
                self.test_results['signal_generator_init'] = False
                return
                
            self.signal_generator = SignalGenerator(self.config, self.alert_manager)
            
            thresholds = getattr(self.signal_generator, 'thresholds', {})
            logger.info("✅ SignalGenerator initialized successfully")
            logger.info(f"   Buy threshold: {thresholds.get('buy', 0)}")
            logger.info(f"   Sell threshold: {thresholds.get('sell', 0)}")
            
            self.test_results['signal_generator_init'] = True
            
        except Exception as e:
            logger.error(f"❌ SignalGenerator initialization failed: {str(e)}")
            self.test_results['signal_generator_init'] = False
    
    async def _test_discord_webhook(self):
        """Test Discord webhook configuration."""
        logger.info("💬 Test 4: Discord Webhook Configuration")
        
        try:
            webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
            if not webhook_url:
                logger.warning("⚠️  DISCORD_WEBHOOK_URL not set")
                self.test_results['discord_webhook'] = False
                return
                
            if not self.alert_manager or not self.alert_manager.discord_webhook_url:
                logger.error("❌ AlertManager webhook URL not configured")
                self.test_results['discord_webhook'] = False
                return
                
            # Test connectivity
            test_message = {
                "content": "🧪 **Alert System Test**\nTesting webhook connectivity...",
                "username": "Virtuoso Test Bot"
            }
            
            logger.info("   Testing webhook connectivity...")
            success, response = await self.alert_manager.send_discord_webhook_message(test_message)
            
            if success:
                logger.info("✅ Discord webhook test passed")
                self.test_results['discord_webhook'] = True
            else:
                logger.error(f"❌ Discord webhook test failed: {response}")
                self.test_results['discord_webhook'] = False
                
        except Exception as e:
            logger.error(f"❌ Discord webhook test failed: {str(e)}")
            self.test_results['discord_webhook'] = False
    
    async def _test_buy_signal(self):
        """Test buy signal generation and alert."""
        logger.info("📈 Test 5: Buy Signal Generation and Alert")
        
        try:
            if not self.signal_generator:
                logger.error("❌ Cannot test without SignalGenerator")
                self.test_results['buy_signal'] = False
                return
                
            # Create buy signal that exceeds threshold
            buy_threshold = self.signal_generator.thresholds.get('buy', 68)
            test_score = buy_threshold + 5
            
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
                    'technical': {'score': 75.0},
                    'volume': {'score': 70.0},
                    'orderbook': {'score': 80.0},
                    'orderflow': {'score': 78.0},
                    'sentiment': {'score': 65.0},
                    'price_structure': {'score': 72.0}
                },
                'buy_threshold': buy_threshold,
                'sell_threshold': self.signal_generator.thresholds.get('sell', 35),
                'signal_type': 'BUY'
            }
            
            logger.info(f"   Generating BUY signal with score {test_score} (threshold: {buy_threshold})")
            
            # Process the signal
            await self.signal_generator.process_signal(buy_signal_data)
            
            logger.info("✅ Buy signal generated and processed successfully")
            self.test_results['buy_signal'] = True
            
            # Wait for alert delivery
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Buy signal test failed: {str(e)}")
            self.test_results['buy_signal'] = False
    
    async def _test_sell_signal(self):
        """Test sell signal generation and alert."""
        logger.info("📉 Test 6: Sell Signal Generation and Alert")
        
        try:
            if not self.signal_generator:
                logger.error("❌ Cannot test without SignalGenerator")
                self.test_results['sell_signal'] = False
                return
                
            # Create sell signal that falls below threshold
            sell_threshold = self.signal_generator.thresholds.get('sell', 35)
            test_score = sell_threshold - 5
            
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
                    'technical': {'score': 25.0},
                    'volume': {'score': 30.0},
                    'orderbook': {'score': 35.0},
                    'orderflow': {'score': 28.0},
                    'sentiment': {'score': 40.0},
                    'price_structure': {'score': 32.0}
                },
                'buy_threshold': self.signal_generator.thresholds.get('buy', 68),
                'sell_threshold': sell_threshold,
                'signal_type': 'SELL'
            }
            
            logger.info(f"   Generating SELL signal with score {test_score} (threshold: {sell_threshold})")
            
            # Process the signal
            await self.signal_generator.process_signal(sell_signal_data)
            
            logger.info("✅ Sell signal generated and processed successfully")
            self.test_results['sell_signal'] = True
            
            # Wait for alert delivery
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Sell signal test failed: {str(e)}")
            self.test_results['sell_signal'] = False
    
    def _print_summary(self):
        """Print test summary."""
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
    results = await test_suite.run_test()
    
    # Return overall success
    return all(results.values())

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 