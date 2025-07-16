#!/usr/bin/env python3
"""
Test script to verify Discord webhook URL configuration
"""

import os
import sys
import logging
from src.monitoring.alert_manager import AlertManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('webhook_test')

def test_webhook_config():
    """Test that webhook URL is properly loaded from environment variables"""
    
    # Save original environment variable if it exists
    original_env = os.environ.get('DISCORD_WEBHOOK_URL', '')
    
    try:
        # Test with environment variable
        test_webhook = "https://discord.com/api/webhooks/test_webhook_url"
        logger.info(f"Setting test webhook URL in environment: {test_webhook[:20]}...")
        os.environ['DISCORD_WEBHOOK_URL'] = test_webhook
        
        # Create config with correct structure - Note the AlertManager expects this specific structure:
        # config['monitoring']['alerts'] for alert configuration
        config = {
            'monitoring': {
                'alerts': {
                    # Leave discord_webhook_url unset to force using environment variable
                }
            }
        }
        
        # Initialize alert manager
        logger.info("Creating AlertManager with environment variable...")
        alert_manager = AlertManager(config)
        
        # Check if webhook URL was properly set from environment
        if alert_manager.discord_webhook_url == test_webhook:
            logger.info("✅ SUCCESS: Webhook URL loaded correctly from environment variable")
        else:
            logger.error(f"❌ FAILURE: Webhook URL not loaded correctly from environment")
            logger.error(f"Expected: {test_webhook}")
            logger.error(f"Actual: {alert_manager.discord_webhook_url}")
            return False
        
        # Test with config value (not environment variable)
        logger.info("Testing with config value...")
        os.environ.pop('DISCORD_WEBHOOK_URL', None)
        
        # Create config with direct webhook URL
        config_webhook = "https://discord.com/api/webhooks/config_webhook_url"
        config = {
            'monitoring': {
                'alerts': {
                    'discord_webhook_url': config_webhook
                }
            }
        }
        
        # Initialize alert manager
        logger.info("Creating AlertManager with config value...")
        alert_manager = AlertManager(config)
        
        # Check if webhook URL was properly set from config
        if alert_manager.discord_webhook_url == config_webhook:
            logger.info("✅ SUCCESS: Webhook URL loaded correctly from config")
        else:
            logger.error(f"❌ FAILURE: Webhook URL not loaded correctly from config")
            logger.error(f"Expected: {config_webhook}")
            logger.error(f"Actual: {alert_manager.discord_webhook_url}")
            return False
            
        return True
        
    finally:
        # Restore original environment variable
        if original_env:
            os.environ['DISCORD_WEBHOOK_URL'] = original_env
        else:
            os.environ.pop('DISCORD_WEBHOOK_URL', None)

if __name__ == "__main__":
    logger.info("Starting webhook configuration test")
    
    if test_webhook_config():
        logger.info("All webhook configuration tests passed!")
        sys.exit(0)
    else:
        logger.error("Webhook configuration tests failed!")
        sys.exit(1) 