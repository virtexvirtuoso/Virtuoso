#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify market report feature with Discord alerts using a webhook URL.
"""

import os
import sys
import asyncio
import subprocess
import logging
import yaml
from pathlib import Path
from src.monitoring.alert_manager import AlertManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("test_discord_webhook")

async def main():
    """Run the market report test with a Discord webhook."""
    webhook_url = input("Enter your Discord webhook URL: ").strip()
    
    if not webhook_url:
        logger.error("No webhook URL provided. Exiting.")
        return 1
    
    # Set the webhook URL as an environment variable
    os.environ['DISCORD_WEBHOOK_URL'] = webhook_url
    logger.info("Discord webhook URL set as environment variable.")
    
    # Run the market report test script
    logger.info("Running market report test with Discord alerts...")
    cmd = [sys.executable, "test_market_report_live.py"]
    process = subprocess.run(cmd, env=os.environ.copy())
    
    if process.returncode == 0:
        logger.info("✅ Market report sent to Discord successfully!")
        return 0
    else:
        logger.error("❌ Failed to send market report to Discord!")
        return 1

def load_config():
    """Load configuration from YAML file."""
    try:
        config_path = Path("config/config.yaml")
        
        if not config_path.exists():
            logger.error(f"Config file not found at {config_path}")
            return None
            
        logger.info(f"Loading config from {config_path}")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        return config
        
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return None

def test_alert_manager():
    """Test AlertManager initialization and Discord webhook loading."""
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load config")
        return False
    
    # Check if Discord webhook URL is in the config
    if 'monitoring' in config and 'alerts' in config['monitoring']:
        if 'discord_webhook_url' in config['monitoring']['alerts']:
            webhook_url = config['monitoring']['alerts']['discord_webhook_url']
            logger.info(f"Found Discord webhook URL in config: {webhook_url[:20]}...{webhook_url[-10:]}")
        else:
            logger.warning("No discord_webhook_url found in config")
    else:
        logger.warning("No monitoring.alerts section found in config")
    
    # Initialize AlertManager
    logger.info("Initializing AlertManager...")
    alert_manager = AlertManager(config)
    
    # Check if Discord webhook URL was loaded
    if hasattr(alert_manager, 'discord_webhook_url') and alert_manager.discord_webhook_url:
        logger.info(f"AlertManager loaded webhook URL: {alert_manager.discord_webhook_url[:20]}...{alert_manager.discord_webhook_url[-10:]}")
        return True
    else:
        logger.error("AlertManager did not load Discord webhook URL")
        return False

if __name__ == "__main__":
    logger.info("Testing Discord webhook initialization")
    success = test_alert_manager()
    
    if success:
        logger.info("Discord webhook test passed ✓")
        sys.exit(0)
    else:
        logger.error("Discord webhook test failed ✗")
        sys.exit(1) 