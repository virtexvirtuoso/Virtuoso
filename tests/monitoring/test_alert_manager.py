#!/usr/bin/env python3
"""
Test script to verify AlertManager initialization in SignalGenerator.
This script tests if the fix for the "AlertManager not properly initialized" warning works.
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
logger = logging.getLogger('test_alert_manager')

def main():
    """Run test of AlertManager initialization."""
    logger.info("Testing AlertManager initialization in SignalGenerator")
    
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
    
    # Import AlertManager here to avoid circular imports
    try:
        from src.monitoring.alert_manager import AlertManager
        
        # Test creation of AlertManager directly
        alert_manager = AlertManager(config)
        logger.info("AlertManager created successfully")
        
        # Check discord webhook
        if hasattr(alert_manager, 'discord_webhook_url') and alert_manager.discord_webhook_url:
            logger.info(f"AlertManager has Discord webhook URL")
        else:
            logger.warning("AlertManager does not have Discord webhook URL")
        
        # Check handlers
        if hasattr(alert_manager, 'handlers'):
            logger.info(f"Registered handlers: {alert_manager.handlers}")
        else:
            logger.warning("No handlers found in AlertManager")
    except Exception as e:
        logger.error(f"Error creating AlertManager: {str(e)}")
        return False
    
    # Import SignalGenerator here to avoid circular imports
    try:
        from src.signal_generation.signal_generator import SignalGenerator
        
        # Test SignalGenerator with no AlertManager
        signal_generator = SignalGenerator(config)
        
        # Check if AlertManager was created
        if signal_generator.alert_manager:
            logger.info("SignalGenerator created AlertManager successfully")
            
            # Check discord webhook
            if hasattr(signal_generator.alert_manager, 'discord_webhook_url') and signal_generator.alert_manager.discord_webhook_url:
                logger.info("AlertManager in SignalGenerator has Discord webhook URL")
            else:
                logger.warning("AlertManager in SignalGenerator does not have Discord webhook URL")
            
            # Check handlers
            if hasattr(signal_generator.alert_manager, 'handlers'):
                logger.info(f"Registered handlers in SignalGenerator's AlertManager: {signal_generator.alert_manager.handlers}")
            else:
                logger.warning("No handlers found in SignalGenerator's AlertManager")
        else:
            logger.error("SignalGenerator failed to create AlertManager")
            return False
    except Exception as e:
        logger.error(f"Error creating SignalGenerator: {str(e)}")
        logger.error(traceback.format_exc())
        return False
    
    logger.info("Tests completed successfully")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 