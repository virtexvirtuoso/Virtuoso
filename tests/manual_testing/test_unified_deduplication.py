#!/usr/bin/env python3
"""Test script to verify the unified deduplication system."""

import os
import sys
import asyncio
import logging
import time
import hashlib
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
logger = logging.getLogger("UnifiedDeduplicationTest")

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

def create_test_signal(symbol: str, score: float, signal_type: str = None) -> Dict[str, Any]:
    """Create a test signal for testing."""
    if signal_type is None:
        signal_type = "buy" if score > 50 else "sell"
        
    components = {
        'volume': 65.5 if score > 60 else 35.5,
        'orderbook': 72.3 if score > 60 else 32.3,
        'orderflow': 58.1 if score > 60 else 28.1,
        'technical': 63.5 if score > 60 else 33.5,
        'price_structure': 67.2 if score > 60 else 37.2,
        'sentiment': 69.8 if score > 60 else 39.8
    }
    
    return {
        'symbol': symbol,
        'signal': signal_type,
        'score': score,
        'confluence_score': score,
        'price': 0.0,  # Test zero price handling
        'timestamp': int(time.time() * 1000),
        'components': components
    }

async def test_unified_deduplication():
    """Test the unified deduplication system."""
    # Load config
    config = load_config()
    
    # Initialize components
    logger.info("\nInitializing components...")
    alert_manager = AlertManager(config)
    signal_generator = SignalGenerator(config, alert_manager)
    
    # Verify _is_duplicate_alert method
    logger.info("\nTest 1: Direct deduplication check with _is_duplicate_alert...")
    symbol = "BTCUSDT"
    content_hash = f"{symbol}_BUY_75"
    
    # First call should not be a duplicate
    is_duplicate = await alert_manager._is_duplicate_alert(symbol, content_hash)
    logger.info(f"First check result - is duplicate: {is_duplicate} (should be False)")
    
    # Second immediate call should be a duplicate
    is_duplicate = await alert_manager._is_duplicate_alert(symbol, content_hash)
    logger.info(f"Second check result - is duplicate: {is_duplicate} (should be True)")
    
    # Different symbol should not be a duplicate
    different_symbol = "ETHUSDT"
    different_hash = f"{different_symbol}_SELL_25"
    is_duplicate = await alert_manager._is_duplicate_alert(different_symbol, different_hash)
    logger.info(f"Different symbol check - is duplicate: {is_duplicate} (should be False)")
    
    # Test 2: Check send_signal_alert deduplication
    logger.info("\nTest 2: Testing send_signal_alert deduplication...")
    
    # Create a signal and send it
    test_signal = create_test_signal("SOLUSDT", 72.5, "buy")
    success = await alert_manager.send_signal_alert(test_signal)
    logger.info(f"First alert sent successfully: {success}")
    
    # Try to send the same signal again
    success = await alert_manager.send_signal_alert(test_signal)
    logger.info(f"Duplicate alert attempt result: {success} (should be False/rejected)")
    
    # Test 3: Check send_confluence_alert deduplication
    logger.info("\nTest 3: Testing send_confluence_alert deduplication...")
    
    # Send a confluence alert
    await alert_manager.send_confluence_alert(
        symbol="DOGEUSDT",
        confluence_score=35.0,
        components={
            'volume': 35.5,
            'orderbook': 42.3,
            'orderflow': 28.1,
            'technical': 33.5,
            'price_structure': 37.2,
            'sentiment': 39.8
        },
        results={},
        reliability=1.0
    )
    logger.info("First confluence alert sent")
    
    # Try to send the same confluence alert again
    await alert_manager.send_confluence_alert(
        symbol="DOGEUSDT",
        confluence_score=35.0,
        components={
            'volume': 35.5,
            'orderbook': 42.3,
            'orderflow': 28.1,
            'technical': 33.5,
            'price_structure': 37.2,
            'sentiment': 39.8
        },
        results={},
        reliability=1.0
    )
    logger.info("Attempted to send duplicate confluence alert (should be rejected)")
    
    # Test 4: Check process_signal deduplication
    logger.info("\nTest 4: Testing process_signal deduplication...")
    
    # Process a signal
    process_signal = create_test_signal("MATICUSDT", 68.5, "buy")
    await alert_manager.process_signal(process_signal)
    logger.info("First process_signal call completed")
    
    # Try to process the same signal again
    await alert_manager.process_signal(process_signal)
    logger.info("Duplicate process_signal call attempted (should be rejected)")
    
    # Test 5: End-to-end test through SignalGenerator
    logger.info("\nTest 5: Testing end-to-end flow through SignalGenerator...")
    
    # Create a signal and process it through SignalGenerator
    sg_signal = create_test_signal("ADAUSDT", 38.2, "sell")
    await signal_generator.process_signal(sg_signal)
    logger.info("Signal processed through SignalGenerator")
    
    # Try to process the same signal through AlertManager
    await alert_manager.process_signal(sg_signal)
    logger.info("Same signal sent to AlertManager (should be rejected)")
    
    # Try a second time through SignalGenerator
    await signal_generator.process_signal(sg_signal)
    logger.info("Signal processed again through SignalGenerator (should be rejected)")
    
    logger.info("\nAll unified deduplication tests completed!")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run the test
    asyncio.run(test_unified_deduplication()) 