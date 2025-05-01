#!/usr/bin/env python3
"""Test script for signal flow."""

import asyncio
import yaml
import logging
from src.monitoring.alert_manager import AlertManager
from src.signal_generation.signal_generator import SignalGenerator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_signal_flow():
    """Test the signal flow from signal generator to alert manager."""
    try:
        # Load configuration
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Initialize components
        logger.info("Initializing AlertManager")
        alert_manager = AlertManager(config)
        
        logger.info("Initializing SignalGenerator")
        signal_generator = SignalGenerator(config, alert_manager)
        
        # Create test signal data
        signal_data = {
            'symbol': 'BTC/USDT',
            'score': 75,
            'direction': 'BUY',
            'signal': 'BUY',
            'confluence_score': 75,
            'current_price': 65000,
            'volume_score': 80,
            'technical_score': 75,
            'orderflow_score': 65,
            'orderbook_score': 70,
            'sentiment_score': 80,
            'price_structure_score': 72,
            'timestamp': 1717267302000
        }
        
        # Process the signal
        logger.info(f"Processing signal for {signal_data['symbol']}")
        await signal_generator.process_signal(signal_data)
        
        logger.info("Signal processed successfully")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_signal_flow())
