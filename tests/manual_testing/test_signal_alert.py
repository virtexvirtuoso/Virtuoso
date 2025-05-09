#!/usr/bin/env python
"""
Test Signal Alert

This script tests that signal alerts are properly sent to Discord
after fixing the handler registration issue.

Usage:
    python tests/manual_testing/test_signal_alert.py
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
logger = logging.getLogger("signal_alert_test")

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import required components
from src.monitoring.alert_manager import AlertManager
from src.signal_generation.signal_generator import SignalGenerator

async def test_signal_alert():
    """
    Test that signal alerts are properly sent to Discord
    """
    # Check for Discord webhook URL in environment
    discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not discord_webhook_url:
        logger.error("DISCORD_WEBHOOK_URL environment variable is not set!")
        return False
    
    logger.info(f"Discord webhook URL exists in environment: {bool(discord_webhook_url)}")
    
    # Load config
    config_path = "config/config.yaml"
    try:
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
        logger.info(f"Loaded config from {config_path}")
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return False
    
    # Initialize AlertManager
    alert_manager = AlertManager(config)
    logger.info(f"Initial handlers: {alert_manager.handlers}")
    
    # Register Discord handler
    alert_manager.discord_webhook_url = discord_webhook_url
    alert_manager.register_discord_handler()
    
    # Verify handler registration
    logger.info(f"Handlers after registration: {alert_manager.handlers}")
    logger.info(f"Has Discord webhook URL: {bool(alert_manager.discord_webhook_url)}")
    
    # Initialize SignalGenerator
    signal_generator = SignalGenerator(config, alert_manager)
    
    # Create test signal for ETHUSDT
    signal = {
        "symbol": "ETHUSDT",
        "score": 70.66,
        "signal_type": "BUY",
        "price": 3450.25,
        "timestamp": datetime.now().timestamp(),
        "components": {
            "volume": 65,
            "orderbook": 72,
            "orderflow": 68,
            "technical": 75,
            "price_structure": 70,
            "sentiment": 74
        },
        "analysis": {
            "summary": "Strong buy signal based on multiple indicators",
            "key_levels": {
                "support": [3400, 3350],
                "resistance": [3500, 3550]
            },
            "risk_reward": 2.5
        }
    }
    
    # Send signal alert directly
    logger.info(f"Sending signal alert for {signal['symbol']} with score {signal['score']}")
    result = await alert_manager.send_signal_alert(signal)
    logger.info(f"Signal alert sent: {result}")
    
    # Send through SignalGenerator
    logger.info(f"Sending signal through SignalGenerator")
    await signal_generator.process_signal(signal)
    logger.info(f"Signal processed through SignalGenerator")
    
    return True

async def main():
    """Main entry point"""
    success = await test_signal_alert()
    if success:
        logger.info("Signal alert test completed successfully!")
    else:
        logger.error("Signal alert test failed")

if __name__ == "__main__":
    asyncio.run(main()) 