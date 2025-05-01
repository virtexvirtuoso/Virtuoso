#!/usr/bin/env python
"""
Test module for enhanced signal data with formatted components.

This test verifies that top influential components, market interpretations, 
and actionable trading insights are properly stored in the signal data structure
and can be passed through the signal alert flow.
"""

import os
import sys
import asyncio
import logging
import json
import time
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import required modules
from src.monitoring.alert_manager import AlertManager
from src.signal_generation.signal_generator import SignalGenerator
from src.core.analysis.interpretation_generator import InterpretationGenerator
from src.utils.serializers import serialize_for_json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_enhanced_signal_data')

def load_config() -> dict:
    """Load configuration from YAML file."""
    try:
        # Try loading from config/config.yaml first
        config_path = Path("config/config.yaml")
        if not config_path.exists():
            # Fallback to src/config/config.yaml
            config_path = Path("src/config/config.yaml")
            
        if not config_path.exists():
            raise FileNotFoundError("Config file not found in config/ or src/config/")
            
        logger.info(f"Loading config from {config_path}")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        return config
        
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return {}

def create_test_signal_data() -> Dict[str, Any]:
    """Create test signal data with all required components."""
    return {
        'symbol': 'BTCUSDT',
        'confluence_score': 78.5,
        'timestamp': int(time.time() * 1000),
        'reliability': 0.85,
        'price': 45678.9,
        'components': {
            'volume': 82.5,
            'orderbook': 76.3,
            'orderflow': 79.8,
            'technical': 75.2,
            'price_structure': 77.6,
            'sentiment': 80.1
        },
        'results': {
            'volume': {
                'score': 82.5,
                'components': {
                    'volume_change': 85.3,
                    'relative_volume': 78.9,
                    'buy_volume': 83.2
                },
                'interpretation': 'Strong buy volume with increasing trend'
            },
            'technical': {
                'score': 75.2,
                'components': {
                    'macd': 77.8,
                    'rsi': 72.3,
                    'ma_cross': 76.5
                },
                'interpretation': 'Bullish trend with strong momentum'
            },
            'orderflow': {
                'score': 79.8,
                'components': {
                    'delta': 81.2,
                    'imbalance': 77.5,
                    'pressure': 80.7
                },
                'interpretation': 'Strong buying pressure with accumulation'
            }
        }
    }

async def save_signal_data(signal_data: Dict[str, Any], filename: str = None) -> str:
    """Save signal data to a JSON file for inspection."""
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"enhanced_signal_{timestamp}.json"
        
    # Create exports directory if it doesn't exist
    exports_dir = os.path.join(os.getcwd(), 'exports', 'signal_data')
    os.makedirs(exports_dir, exist_ok=True)
    
    # Create filepath
    filepath = os.path.join(exports_dir, filename)
    
    # Use serializer to prepare data for JSON
    json_ready_data = serialize_for_json(signal_data)
    
    # Write to file with pretty formatting
    with open(filepath, 'w') as f:
        json.dump(json_ready_data, f, indent=2, default=str)
    
    logger.info(f"Saved signal data to {filepath}")
    return filepath

async def test_enhanced_signal_data():
    """Test that enhanced formatting data is added to the signal structure."""
    # Load config 
    config = load_config()
    
    # Step 1: Initialize components
    logger.info("\nStep 1: Initializing components...")
    alert_manager = AlertManager(config)
    signal_generator = SignalGenerator(config, alert_manager)
    
    # Step 2: Create test signal data
    logger.info("\nStep 2: Creating test signal data...")
    test_signal = create_test_signal_data()
    logger.info(f"Created test signal for {test_signal['symbol']} with score {test_signal['confluence_score']}")
    
    # Save original signal data
    original_filepath = await save_signal_data(test_signal, 'original_signal.json')
    logger.info(f"Saved original signal data to {original_filepath}")
    
    # Step 3: Process signal and check if enhanced data is added
    logger.info("\nStep 3: Processing signal...")
    
    # Set thresholds
    signal_generator.thresholds = {'buy': 65.0, 'sell': 40.0}
    
    # Process the signal
    await signal_generator.process_signal(test_signal)
    logger.info("Signal processed through SignalGenerator")
    
    # Wait for a moment to let processing complete
    await asyncio.sleep(2)
    
    # Step 4: Run a direct test of the enhanced data generation
    logger.info("\nStep 4: Directly testing enhanced data generation...")
    enhanced_data = signal_generator._generate_enhanced_formatted_data(
        symbol=test_signal['symbol'],
        confluence_score=test_signal['confluence_score'],
        components=test_signal['components'],
        results=test_signal['results'],
        reliability=test_signal['reliability'],
        buy_threshold=signal_generator.thresholds['buy'],
        sell_threshold=signal_generator.thresholds['sell']
    )
    
    # Print the enhanced data
    logger.info("Generated enhanced data:")
    
    if 'influential_components' in enhanced_data:
        logger.info("\nTop Influential Components:")
        for comp in enhanced_data['influential_components']:
            logger.info(f"  • {comp['display_name']} ({comp['score']:.1f}):")
            
            # Log sub-components if they exist
            if 'sub_components' in comp and comp['sub_components']:
                for sub in comp['sub_components']:
                    logger.info(f"    - {sub['display_name']}: {sub['score']:.1f} {sub.get('indicator', '')}")
            else:
                logger.info(f"    - No sub-components found")
    
    if 'market_interpretations' in enhanced_data:
        logger.info("\nMarket Interpretations:")
        for interp in enhanced_data['market_interpretations']:
            logger.info(f"  • {interp}")
    
    if 'actionable_insights' in enhanced_data:
        logger.info("\nActionable Trading Insights:")
        for insight in enhanced_data['actionable_insights']:
            logger.info(f"  • {insight}")
    
    # Save enhanced data
    enhanced_test_signal = test_signal.copy()
    enhanced_test_signal.update(enhanced_data)
    enhanced_filepath = await save_signal_data(enhanced_test_signal, 'enhanced_signal.json')
    logger.info(f"Saved enhanced signal data to {enhanced_filepath}")
    
    logger.info("\nTest completed!")

if __name__ == "__main__":
    logger.info("Starting enhanced signal data test...")
    asyncio.run(test_enhanced_signal_data()) 