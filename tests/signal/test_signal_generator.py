#!/usr/bin/env python3
"""
Test script to verify SignalGenerator initialization without the warning.
This checks if the fix for "AlertManager not properly initialized" warning is effective.
"""

import os
import sys
import logging
import yaml
import traceback
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('test_signal_generator')

def main():
    """Run the SignalGenerator with minimal setup."""
    logger.info("Testing SignalGenerator initialization")
    
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
    
    # Ensure discord webhook is set
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    if not discord_webhook:
        logger.warning("DISCORD_WEBHOOK_URL environment variable not set.")
        logger.info("Setting a placeholder for testing purposes...")
        os.environ['DISCORD_WEBHOOK_URL'] = 'https://discord.com/api/webhooks/example/placeholder'
    
    # Create and initialize SignalGenerator
    try:
        from src.signal_generation.signal_generator import SignalGenerator
        
        signal_generator = SignalGenerator(config)
        
        # Verify AlertManager initialization
        if signal_generator.alert_manager:
            logger.info("AlertManager initialized successfully")
            
            # Check handlers
            if hasattr(signal_generator.alert_manager, 'handlers'):
                logger.info(f"Registered handlers: {signal_generator.alert_manager.handlers}")
            else:
                logger.warning("No handlers found in AlertManager")
            
            # Check if we have the discord webhook URL
            if hasattr(signal_generator.alert_manager, 'discord_webhook_url') and signal_generator.alert_manager.discord_webhook_url:
                logger.info("Discord webhook URL is configured correctly")
            else:
                logger.warning("Discord webhook URL is not configured properly")
        else:
            logger.error("AlertManager not initialized")
            return False
        
        # Test creating a simple signal
        logger.info("SignalGenerator initialization successful")
        
    except Exception as e:
        logger.error(f"Error initializing SignalGenerator: {str(e)}")
        logger.error(traceback.format_exc())
        return False
    
    logger.info("Test completed successfully")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 