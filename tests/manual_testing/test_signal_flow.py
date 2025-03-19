#!/usr/bin/env python3
"""Test script to verify the improved signal flow without duplication."""

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
logger = logging.getLogger("SignalFlowTest")

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

# Create a mock analysis result for testing
def create_mock_analysis(symbol: str, score: float):
    """Create a mock analysis result for testing."""
    return {
        'symbol': symbol,
        'score': score,
        'confluence_score': score,
        'reliability': 1.0,
        'components': {
            'volume': 75.5 if score > 60 else 25.5,
            'orderbook': 82.3 if score > 60 else 32.3,
            'orderflow': 78.1 if score > 60 else 28.1,
            'technical': 73.5 if score > 60 else 33.5,
            'price_structure': 77.2 if score > 60 else 37.2,
            'sentiment': 79.8 if score > 60 else 39.8
        },
        'metadata': {
            'timeframes_analyzed': ['1m', '5m', '15m', '1h'],
            'calculation_time_ms': 235,
            'timestamp': int(time.time() * 1000)
        },
        'timestamp': int(time.time() * 1000)
    }

# Create a simpler test that doesn't rely on MarketMonitor
async def test_signal_flow():
    """Test the improved signal flow."""
    # Load config
    config = load_config()
    
    # Step 1: Initialize components
    logger.info("\nStep 1: Initializing components...")
    alert_manager = AlertManager(config)
    signal_generator = SignalGenerator(config, alert_manager)
    
    # Step 2: Test sending a signal directly through SignalGenerator
    logger.info("\nStep 2: Testing signal flow directly through SignalGenerator...")
    
    # Create a buy signal that crosses the threshold
    buy_signal = {
        'symbol': 'BTCUSDT',
        'confluence_score': 75.0,
        'timestamp': int(time.time() * 1000),
        'reliability': 1.0,
        'components': {
            'volume': 75.5,
            'orderbook': 82.3,
            'orderflow': 78.1,
            'technical': 73.5,
            'price_structure': 77.2,
            'sentiment': 79.8
        }
    }
    
    logger.info(f"Generated buy signal for BTCUSDT with score {buy_signal['confluence_score']}")
    await signal_generator.process_signal(buy_signal)
    logger.info("Signal processed through SignalGenerator")
    
    # Wait to see alerts
    logger.info("Waiting for alerts to be processed...")
    await asyncio.sleep(1)
    
    # Step 3: Create a sell signal
    logger.info("\nStep 3: Creating a sell signal...")
    sell_signal = {
        'symbol': 'ETHUSDT',
        'confluence_score': 25.0,
        'timestamp': int(time.time() * 1000),
        'reliability': 1.0,
        'components': {
            'volume': 25.5,
            'orderbook': 32.3,
            'orderflow': 28.1,
            'technical': 33.5,
            'price_structure': 37.2,
            'sentiment': 39.8
        }
    }
    
    logger.info(f"Generated sell signal for ETHUSDT with score {sell_signal['confluence_score']}")
    await signal_generator.process_signal(sell_signal)
    logger.info("Signal processed through SignalGenerator")
    
    # Wait to see alerts
    logger.info("Waiting for alerts to be processed...")
    await asyncio.sleep(1)
    
    # Step 4: Test signal flow through AlertManager directly 
    logger.info("\nStep 4: Testing signal flow directly through AlertManager...")
    
    # Create a buy signal and process directly through AlertManager
    direct_signal = {
        'symbol': 'SOLUSDT',
        'confluence_score': 70.0,
        'timestamp': int(time.time() * 1000),
        'reliability': 1.0,
        'components': {
            'volume': 75.5,
            'orderbook': 82.3,
            'orderflow': 78.1,
            'technical': 73.5,
            'price_structure': 77.2,
            'sentiment': 79.8
        }
    }
    
    logger.info(f"Generated direct signal for SOLUSDT with score {direct_signal['confluence_score']}")
    await alert_manager.process_signal(direct_signal)
    logger.info("Signal processed directly through AlertManager")
    
    # Wait to see alerts
    logger.info("Waiting for alerts to be processed...")
    await asyncio.sleep(1)
    
    # Step 5: Now try to process the same signal again through both paths
    logger.info("\nStep 5: Testing duplicate signal detection...")
    
    # Try to process directly through AlertManager again
    logger.info("Attempting to process the same SOLUSDT signal through AlertManager (should be deduplicated)")
    await alert_manager.process_signal(direct_signal)
    logger.info("Duplicate AlertManager attempt completed")
    
    # Try through SignalGenerator with same signal
    logger.info("Attempting to process the same SOLUSDT signal through SignalGenerator (should be deduplicated)")
    direct_signal['processed_by'] = None  # Reset this to test deduplication logic
    await signal_generator.process_signal(direct_signal)
    logger.info("Duplicate SignalGenerator attempt completed")
    
    # Wait to see any alerts (should be none for duplicates)
    logger.info("Waiting to see if duplicate alerts occur...")
    await asyncio.sleep(1)
    
    logger.info("\nAll signal flow tests completed!")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run the test
    asyncio.run(test_signal_flow()) 