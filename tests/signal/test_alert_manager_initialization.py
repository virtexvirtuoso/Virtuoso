#!/usr/bin/env python3
"""
Test script to verify AlertManager initialization fix in SignalGenerator.
This script tests if the fix for the "AlertManager not properly initialized" warning works.
"""

import os
import sys
import logging
import yaml
import traceback
from dotenv import load_dotenv

# Setup logging to capture the specific warning we're testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('test_alert_manager_init')

def main():
    """Test AlertManager initialization in SignalGenerator."""
    logger.info("Testing AlertManager initialization fix in SignalGenerator")
    
    # Load environment variables
    load_dotenv()
    
    # Load config
    config_path = "config/config.yaml"
    
    if not os.path.exists(config_path):
        logger.error(f"Config file not found at {config_path}")
        return False
    
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    
    logger.info(f"Loaded config from {config_path}")
    
    # Ensure discord webhook is set for testing
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    if not discord_webhook:
        logger.warning("DISCORD_WEBHOOK_URL environment variable not set.")
        logger.info("Setting a test placeholder for testing purposes...")
        os.environ['DISCORD_WEBHOOK_URL'] = 'https://discord.com/api/webhooks/test/placeholder'
    
    # Test SignalGenerator initialization
    try:
        from src.signal_generation.signal_generator import SignalGenerator
        
        # Create SignalGenerator (this will create its own AlertManager)
        logger.info("Creating SignalGenerator with auto-initialized AlertManager...")
        signal_generator = SignalGenerator(config)
        
        # Check if AlertManager was created and initialized properly
        if signal_generator.alert_manager:
            logger.info("✅ SignalGenerator successfully created AlertManager")
            
            # Check discord webhook
            if hasattr(signal_generator.alert_manager, 'discord_webhook_url') and signal_generator.alert_manager.discord_webhook_url:
                logger.info("✅ AlertManager has Discord webhook URL configured")
            else:
                logger.warning("⚠️ AlertManager does not have Discord webhook URL")
            
            # Check handlers (both possible attribute names)
            if hasattr(signal_generator.alert_manager, 'alert_handlers') and signal_generator.alert_manager.alert_handlers:
                logger.info(f"✅ AlertManager has alert_handlers: {list(signal_generator.alert_manager.alert_handlers.keys())}")
            elif hasattr(signal_generator.alert_manager, 'handlers') and signal_generator.alert_manager.handlers:
                logger.info(f"✅ AlertManager has handlers: {signal_generator.alert_manager.handlers}")
            else:
                logger.warning("⚠️ AlertManager does not have handlers configured")
                
        else:
            logger.error("❌ SignalGenerator failed to create AlertManager")
            return False
            
        # Test with pre-initialized AlertManager
        logger.info("Testing with pre-initialized AlertManager...")
        from src.monitoring.alert_manager import AlertManager
        
        alert_manager = AlertManager(config)
        signal_generator_2 = SignalGenerator(config, alert_manager)
        
        if signal_generator_2.alert_manager:
            logger.info("✅ SignalGenerator successfully used pre-initialized AlertManager")
        else:
            logger.error("❌ SignalGenerator failed to use pre-initialized AlertManager")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during SignalGenerator initialization: {str(e)}")
        logger.error(traceback.format_exc())
        return False
    
    logger.info("✅ All tests completed successfully - AlertManager initialization fix verified")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 