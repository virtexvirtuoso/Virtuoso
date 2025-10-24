#!/usr/bin/env python3
"""Test script to verify the integration between SignalGenerator and AlertManager."""

import os
import sys
import asyncio
import logging
import time
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config.manager import ConfigManager
from src.monitoring.alert_manager import AlertManager
from src.signal_generation.signal_generator import SignalGenerator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger("IntegrationTest")

# Load config
def load_config():
    """Load configuration from file."""
    try:
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        config_path = base_dir / 'config.yaml'
        
        if not config_path.exists():
            logger.warning(f"Config file not found at {config_path}, trying alternative path...")
            config_path = base_dir / 'config' / 'config.yaml'
            
        if not config_path.exists():
            logger.error("Config file not found")
            raise FileNotFoundError("Config file not found")
            
        # Load configuration
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        raise

# Mock indicators for testing
def create_mock_indicators(symbol: str, score: float):
    """Create mock indicators for signal generation testing."""
    return {
        'symbol': symbol,
        'current_price': 25000.0,
        'score': score,  # Add the score explicitly for the signal generator
        'components': {
            'volume': 65.5 if score > 50 else 35.5,
            'orderbook': 72.3 if score > 50 else 42.3,
            'orderflow': 58.1 if score > 50 else 28.1,
            'technical': 63.5 if score > 50 else 33.5,
            'price_structure': 67.2 if score > 50 else 37.2,
            'sentiment': 69.8 if score > 50 else 39.8
        },
        'volume_score': 65.5 if score > 50 else 35.5,
        'orderbook_score': 72.3 if score > 50 else 42.3,
        'orderflow_score': 58.1 if score > 50 else 28.1,
        'technical_score': 63.5 if score > 50 else 33.5,
        'price_structure_score': 67.2 if score > 50 else 37.2,
        'sentiment_score': 69.8 if score > 50 else 39.8,
        'last_orderbook_update': int(time.time() * 1000),
        'symbol_info': {'precision': {'price': 2, 'amount': 6}},
        'reliability': 1.0,
        'timestamp': int(time.time() * 1000)
    }

async def test_signal_integration():
    """Test integration between SignalGenerator and AlertManager."""
    # Load config
    config = load_config()
    
    # Initialize components
    logger.info("Initializing AlertManager and SignalGenerator...")
    alert_manager = AlertManager(config)
    signal_generator = SignalGenerator(config)
    
    # Set AlertManager in SignalGenerator
    signal_generator.alert_manager = alert_manager
    
    # Set thresholds for testing
    signal_generator.long_threshold = 60.0
    signal_generator.short_threshold = 40.0
    
    # Test 1: Generate a buy signal
    logger.info("Test 1: Generate a buy signal")
    buy_indicators = create_mock_indicators("BTCUSDT", 65.5)
    
    # Generate signal (handle as async)
    buy_signal = await signal_generator.generate_signal(buy_indicators)
    
    if buy_signal is None:
        logger.warning("No buy signal was generated - check threshold settings")
    else:
        logger.info(f"Generated signal: {buy_signal['signal']} with score {buy_signal['score']}")
        
        # Process signal through the alert manager
        await alert_manager.process_signal(buy_signal)
        logger.info("Buy signal processed")
    await asyncio.sleep(1)
    
    # Test 2: Generate the same signal again - should be deduplicated
    logger.info("Test 2: Generate the same buy signal again (should be deduplicated)")
    buy_signal_2 = await signal_generator.generate_signal(buy_indicators)
    
    if buy_signal_2 is not None:
        await alert_manager.process_signal(buy_signal_2)
        logger.info("Duplicate buy signal processed")
    else:
        logger.warning("No duplicate buy signal was generated")
    await asyncio.sleep(3)
    
    # Test 3: Generate a sell signal for a different symbol
    logger.info("Test 3: Generate a sell signal for a different symbol")
    sell_indicators = create_mock_indicators("ETHUSDT", 35.0)
    sell_signal = await signal_generator.generate_signal(sell_indicators)
    
    if sell_signal is None:
        logger.warning("No sell signal was generated - check threshold settings")
    else:
        logger.info(f"Generated signal: {sell_signal['signal']} with score {sell_signal['score']}")
        
        # Process signal through the alert manager
        await alert_manager.process_signal(sell_signal)
        logger.info("Sell signal processed")
    await asyncio.sleep(1)
    
    # Test 4: Generate a signal that doesn't meet the threshold (no alert should be sent)
    logger.info("Test 4: Generate a signal that doesn't meet threshold (no alert)")
    neutral_indicators = create_mock_indicators("SOLUSDT", 50.0)
    neutral_signal = await signal_generator.generate_signal(neutral_indicators)
    
    if neutral_signal is None:
        logger.info("As expected, no signal was generated for neutral score")
    else:
        logger.info(f"Generated signal: {neutral_signal.get('signal', 'None')} with score {neutral_signal.get('score', 'N/A')}")
        
        # Process signal through the alert manager
        await alert_manager.process_signal(neutral_signal)
        logger.info("Neutral signal processed")
    
    await asyncio.sleep(1)
    
    logger.info("All integration tests completed successfully!")

class TestSignalGenerator:
    def __init__(self, config, alert_manager=None):
        self.config = config
        self.alert_manager = alert_manager
        self.thresholds = config.get('thresholds', {'buy': 70, 'sell': 30})
        
    async def process_signal(self, signal_data):
        """Test implementation that simulates processing a signal."""
        symbol = signal_data.get('symbol', 'UNKNOWN')
        score = signal_data.get('score', 0)
        price = signal_data.get('price')
        components = signal_data.get('components', {})
        results = signal_data.get('results', {})
        reliability = signal_data.get('reliability', 0.8)
        
        # Only process BUY or SELL signals
        if score >= self.thresholds['buy'] or score <= self.thresholds['sell']:
            if self.alert_manager and hasattr(self.alert_manager, 'send_confluence_alert'):
                await self.alert_manager.send_confluence_alert(
                    symbol=symbol,
                    confluence_score=score,
                    components=components,
                    results=results,
                    reliability=reliability if reliability <= 1 else reliability / 100.0,  # Match new normalization
                    buy_threshold=self.thresholds['buy'],
                    sell_threshold=self.thresholds['sell'],
                    price=price
                )
        return None

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run the test
    asyncio.run(test_signal_integration()) 