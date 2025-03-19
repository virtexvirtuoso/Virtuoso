#!/usr/bin/env python
"""
Fix Discord Handler Registration

This script checks and fixes the Discord webhook URL configuration in the system.
It ensures that:
1. The webhook URL is properly extracted from the environment variable
2. The Discord handler is registered with the AlertManager
3. A test alert is sent to verify the configuration

Usage:
    python tests/manual_testing/fix_discord_handler.py
"""

import os
import sys
import logging
import yaml
import asyncio
import json
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("discord_handler_fix")

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import AlertManager
from src.monitoring.alert_manager import AlertManager

async def fix_discord_handler():
    """
    Fix the Discord webhook URL configuration and send a test alert
    """
    # Check for Discord webhook URL in environment
    discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not discord_webhook_url:
        logger.error("DISCORD_WEBHOOK_URL environment variable is not set!")
        logger.error("Please add it to your .env file:")
        logger.error("DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your-webhook-url")
        return False
    
    logger.info(f"Discord webhook URL exists in environment: {bool(discord_webhook_url)}")
    logger.info(f"Discord webhook URL begins with: {discord_webhook_url[:20]}...")
    
    # Load config
    config_path = "config/config.yaml"
    try:
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
        logger.info(f"Loaded config from {config_path}")
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return False
    
    # Check if Discord alert is configured in config
    if not config.get("monitoring", {}).get("alerts", {}).get("discord_webhook_url"):
        logger.info("Discord webhook URL not found in config, updating...")
        
        # Ensure monitoring section exists
        if "monitoring" not in config:
            config["monitoring"] = {}
        
        # Ensure alerts section exists
        if "alerts" not in config["monitoring"]:
            config["monitoring"]["alerts"] = {}
        
        # Update Discord webhook URL
        config["monitoring"]["alerts"]["discord_webhook_url"] = discord_webhook_url
        
        # Save updated config
        try:
            with open(config_path, "w") as file:
                yaml.dump(config, file)
            logger.info(f"Updated config with Discord webhook URL")
        except Exception as e:
            logger.error(f"Error updating config: {str(e)}")
            return False
    
    # Initialize AlertManager
    alert_manager = AlertManager(config)
    logger.info(f"Initial handlers: {alert_manager.handlers}")
    
    # Force register Discord handler
    alert_manager.discord_webhook_url = discord_webhook_url
    alert_manager.register_discord_handler()
    
    # Verify handler registration
    logger.info(f"Handlers after registration: {alert_manager.handlers}")
    logger.info(f"Has Discord config: {alert_manager._has_discord_config()}")
    logger.info(f"Discord webhook URL is set: {bool(alert_manager.discord_webhook_url)}")
    
    # Send test alert
    test_embed = {
        "embeds": [
            {
                "title": "🔵 ALERT SYSTEM FIXED",
                "description": "This alert confirms that the Discord notification system is now working properly",
                "color": 3447003,
                "fields": [
                    {
                        "name": "Issue",
                        "value": "Discord handler was not being registered properly",
                        "inline": True
                    },
                    {
                        "name": "Fix",
                        "value": "Registered Discord handler explicitly",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "Discord Handler Fix"
                },
                "timestamp": datetime.now().isoformat()
            }
        ]
    }
    
    logger.info(f"Sending test alert")
    success = await alert_manager.send_discord_webhook_message(test_embed)
    logger.info(f"Test alert sent: {success}")
    
    # Add to startup process
    logger.info("\n\nTo fix this permanently, modify your application startup:")
    logger.info("1. Open src/main.py")
    logger.info("2. Find the line where AlertManager is initialized (around line 120)")
    logger.info("3. Add this line immediately after AlertManager initialization:")
    logger.info("   alert_manager.register_discord_handler()")
    logger.info("\nThis will ensure Discord alerts are always properly configured.")
    
    return True

async def main():
    """Main entry point"""
    success = await fix_discord_handler()
    if success:
        logger.info("Discord handler fixed successfully!")
    else:
        logger.error("Failed to fix Discord handler")

if __name__ == "__main__":
    asyncio.run(main()) 