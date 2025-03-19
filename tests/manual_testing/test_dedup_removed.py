#!/usr/bin/env python
"""Test script to verify that deduplication has been removed from the AlertManager.

This script sends multiple identical signals in quick succession to verify
that duplicate signals are now being processed and sent.
"""

import sys
import os
import time
import logging
import asyncio
import yaml
from typing import Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to the path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import project modules
from src.monitoring.alert_manager import AlertManager
from src.signal_generation.signal_generator import SignalGenerator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("DedupRemovedTest")

# Load environment variables
load_dotenv()

async def main():
    """Run the deduplication removal test."""
    logger.info("Starting deduplication removal test")
    
    # Load configuration
    config_file = os.path.join(os.path.dirname(__file__), '../../config/config.yaml')
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from {config_file}")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return

    # Check for Discord webhook URL
    discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if discord_webhook_url:
        logger.info("Found Discord webhook URL in environment variables")
    else:
        logger.warning("No Discord webhook URL found, alerts will not be sent")
        return

    # Initialize components
    logger.info("Initializing AlertManager and SignalGenerator...")
    alert_manager = AlertManager(config)
    signal_generator = SignalGenerator(config, alert_manager)
    
    # Register Discord handler
    logger.info("Registering Discord handler...")
    alert_manager.register_discord_handler()
    logger.info(f"Handlers after registration: {alert_manager.handlers}")
    logger.info(f"Alert handlers dictionary: {list(alert_manager.alert_handlers.keys())}")
    
    # Define a test signal
    def create_test_signal(symbol: str, score: float) -> Dict[str, Any]:
        """Create a test trading signal."""
        signal = {
            'symbol': symbol,
            'score': score,
            'reliability': 0.85,
            'confluence_score': score,
            'signal': 'BUY' if score > 60 else 'SELL' if score < 40 else 'NEUTRAL',
            'timestamp': int(datetime.now().timestamp() * 1000),
            'components': {
                'volume': 83.7,
                'orderbook': 77.2,
                'orderflow': 68.1,
                'technical': 72.5,
                'price_structure': 65.8,
                'sentiment': 62.4
            },
            'metadata': {
                'test': True,
                'volume': {
                    'value': 83.7,
                    'interpretation': 'Strong buying volume indicating bullish pressure'
                },
                'orderbook': {
                    'value': 77.2,
                    'interpretation': 'Significant buy orders stacked near current price'
                },
                'orderflow': {
                    'value': 68.1,
                    'interpretation': 'More buyers than sellers in recent trades'
                },
                'technical': {
                    'value': 72.5,
                    'interpretation': 'Multiple technical indicators showing bullish signals'
                },
                'price_structure': {
                    'value': 65.8,
                    'interpretation': 'Price forming higher lows pattern'
                },
                'sentiment': {
                    'value': 62.4,
                    'interpretation': 'Positive market sentiment with low funding rates'
                }
            }
        }
        return signal
    
    # Send the same signal multiple times in quick succession
    logger.info("\nStep 1: Sending identical signals in quick succession...")
    
    # Create test signals
    btc_signal = create_test_signal("BTCUSDT", 71.0)
    logger.info(f"Created test signal for {btc_signal['symbol']} with score {btc_signal['score']}")
    
    # Initialize client session in AlertManager
    await alert_manager._init_client_session()
    
    # Send the same signal multiple times in quick succession
    for i in range(3):
        logger.info(f"\nSending identical signal #{i+1} for BTCUSDT...")
        await signal_generator.process_signal(btc_signal)
        logger.info(f"Signal #{i+1} sent")
        # Short delay between identical signals
        await asyncio.sleep(1)
    
    # Send a completion message
    logger.info("\nSending completion message...")
    await alert_manager.send_discord_webhook_message({
        "content": f"✅ Deduplication removal test completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nVerify that all 3 identical BTCUSDT signals were sent to Discord."
    })
    
    # Clean up
    logger.info("\nCleaning up resources...")
    await alert_manager.cleanup()
    logger.info("Test completed!")

if __name__ == "__main__":
    asyncio.run(main()) 