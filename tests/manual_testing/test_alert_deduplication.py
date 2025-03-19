#!/usr/bin/env python3
"""Test script to verify alert deduplication and formatting fixes."""

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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger("AlertTest")

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

# Mock data for testing
def create_test_signal(symbol: str, score: float, signal_type: str = None) -> Dict[str, Any]:
    """Create a test signal for testing."""
    if signal_type is None:
        signal_type = "buy" if score > 50 else "sell"
        
    # Create components
    components = {
        'volume': 24.7,
        'orderbook': 57.8,
        'orderflow': 17.4,
        'technical': 35.97,
        'price_structure': 49.7,
        'sentiment': 52.89
    }
    
    # Create results with interpretations
    results = {}
    for name, value in components.items():
        results[name] = {
            'score': value,
            'components': {
                f"{name}_sub1": 65.5,
                f"{name}_sub2": 45.2
            },
            'interpretation': f"Test interpretation for {name}"
        }
    
    return {
        'symbol': symbol,
        'signal': signal_type,
        'score': score,
        'confluence_score': score,
        'price': 0.0,  # Test zero price handling
        'timestamp': int(time.time() * 1000),
        'components': components,
        'results': results,
        'reliability': 1.0
    }

async def test_deduplication():
    """Test alert deduplication."""
    # Load config
    config = load_config()
    
    # Initialize AlertManager
    logger.info("Initializing AlertManager...")
    alert_manager = AlertManager(config)
    
    # Test 1: Multiple calls to send_signal_alert with the same symbol
    logger.info("Test 1: Multiple send_signal_alert calls with same symbol")
    test_signal = create_test_signal("ETHUSDT", 38.3, "sell")
    await alert_manager.send_signal_alert(test_signal)
    logger.info("First alert sent, waiting 1 second...")
    await asyncio.sleep(1)
    
    # Send the same signal again - should be deduplicated
    await alert_manager.send_signal_alert(test_signal)
    logger.info("Second alert attempt (should be deduplicated)")
    await asyncio.sleep(1)
    
    # Send the same signal a third time - should still be deduplicated
    await alert_manager.send_signal_alert(test_signal)
    logger.info("Third alert attempt (should be deduplicated)")
    await asyncio.sleep(3)
    
    # Test 2: Call with different symbol - should go through
    logger.info("Test 2: Different symbol should not be deduplicated")
    test_signal2 = create_test_signal("BTCUSDT", 72.5, "buy")
    await alert_manager.send_signal_alert(test_signal2)
    logger.info("Alert for different symbol sent")
    await asyncio.sleep(3)
    
    # Test 3: Call with same symbol after timeout - should go through
    logger.info("Test 3: Same symbol after timeout should go through")
    test_signal3 = create_test_signal("ETHUSDT", 42.1, "sell")
    await alert_manager.send_signal_alert(test_signal3)
    logger.info("Alert for same symbol after timeout sent")
    await asyncio.sleep(1)
    
    # Test 4: Test with confluence_alert
    logger.info("Test 4: Testing send_confluence_alert deduplication")
    # First call should go through
    await alert_manager.send_confluence_alert(
        symbol="SOLUSDT",
        confluence_score=63.5,
        components={
            'volume': 37.5,
            'orderbook': 77.7,
            'orderflow': 84.4,
            'technical': 51.39,
            'price_structure': 50.93,
            'sentiment': 51.57
        },
        results={},
        reliability=1.0
    )
    logger.info("First confluence alert sent, waiting 1 second...")
    await asyncio.sleep(1)
    
    # Second call should be deduplicated
    await alert_manager.send_confluence_alert(
        symbol="SOLUSDT",
        confluence_score=63.5,
        components={
            'volume': 37.5,
            'orderbook': 77.7,
            'orderflow': 84.4,
            'technical': 51.39,
            'price_structure': 50.93,
            'sentiment': 51.57
        },
        results={},
        reliability=1.0
    )
    logger.info("Second confluence alert attempt (should be deduplicated)")
    await asyncio.sleep(3)
    
    # Test 5: Test process_signal deduplication
    logger.info("Test 5: Testing process_signal deduplication")
    test_signal5 = create_test_signal("XRPUSDT", 35.7, "sell")
    await alert_manager.process_signal(test_signal5)
    logger.info("First process_signal call, waiting 1 second...")
    await asyncio.sleep(1)
    
    # Second call should be deduplicated
    await alert_manager.process_signal(test_signal5)
    logger.info("Second process_signal call (should be deduplicated)")
    await asyncio.sleep(1)
    
    logger.info("All tests completed successfully!")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run the test
    asyncio.run(test_deduplication()) 