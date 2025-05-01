#!/usr/bin/env python
"""
Test script for the weighted sub-components feature.

This script tests the calculation and display of sub-components
with the most weight on the overall confluence score.
"""

import os
import sys
import asyncio
import logging
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import required modules
from src.monitoring.alert_manager import AlertManager
from src.signal_generation.signal_generator import SignalGenerator
from src.utils.serializers import serialize_for_json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_weighted_subcomponents')

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
    """Create test signal data with realistic components."""
    return {
        'symbol': 'BTCUSDT',
        'confluence_score': 78.5,
        'timestamp': int(datetime.now().timestamp() * 1000),
        'reliability': 0.85,
        'price': 67890.5,
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
                    'buy_volume': 83.2,
                    'volume_delta': 88.1,
                    'cmf': 79.5
                },
                'interpretation': 'Strong buying pressure with increasing volume'
            },
            'technical': {
                'score': 75.2,
                'components': {
                    'macd': 77.8,
                    'rsi': 72.3,
                    'ma_cross': 76.5,
                    'momentum': 79.1,
                    'bollinger': 65.8
                },
                'interpretation': 'Bullish trend with strong momentum'
            },
            'orderflow': {
                'score': 79.8,
                'components': {
                    'delta': 81.2,
                    'imbalance': 77.5,
                    'pressure': 80.7,
                    'cvd': 82.3,
                    'buying_aggression': 79.9
                },
                'interpretation': 'Strong buying pressure with accumulation'
            },
            'orderbook': {
                'score': 76.3,
                'components': {
                    'depth_ratio': 74.5,
                    'support_strength': 78.2,
                    'liquidity': 72.8,
                    'book_imbalance': 75.9
                },
                'interpretation': 'Solid support with bullish bias in the order book'
            },
            'price_structure': {
                'score': 77.6,
                'components': {
                    'key_levels': 76.2,
                    'fibonacci': 78.5,
                    'market_structure': 79.1,
                    'vwap_relation': 74.9
                },
                'interpretation': 'Bullish structure with strong support levels'
            },
            'sentiment': {
                'score': 80.1,
                'components': {
                    'funding_rate': 77.3,
                    'long_short_ratio': 82.5,
                    'fear_greed': 83.2,
                    'social_sentiment': 79.8
                },
                'interpretation': 'Positive market sentiment with strong interest'
            }
        }
    }

async def save_signal_data(signal_data: Dict[str, Any], filename: str = None) -> str:
    """Save signal data to a JSON file for inspection."""
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"weighted_signal_{timestamp}.json"
        
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

async def test_weighted_subcomponents():
    """Test that the weighted sub-components feature works correctly."""
    # Load config 
    config = load_config()
    
    # Step 1: Override component weights in config
    logger.info("\nStep 1: Setting up test component weights...")
    if 'confluence' not in config:
        config['confluence'] = {}
    if 'weights' not in config['confluence']:
        config['confluence']['weights'] = {}
    if 'components' not in config['confluence']['weights']:
        config['confluence']['weights']['components'] = {}
    
    # Set different weights for components to test weighted impact
    config['confluence']['weights']['components'] = {
        'volume': 0.25,        # 25% weight
        'technical': 0.20,     # 20% weight
        'orderflow': 0.18,     # 18% weight
        'orderbook': 0.15,     # 15% weight
        'price_structure': 0.12, # 12% weight
        'sentiment': 0.10      # 10% weight
    }
    logger.info(f"Set component weights: {config['confluence']['weights']['components']}")
    
    # Step 2: Initialize components
    logger.info("\nStep 2: Initializing components...")
    alert_manager = AlertManager(config)
    signal_generator = SignalGenerator(config, alert_manager)
    
    # Step 3: Create test signal data
    logger.info("\nStep 3: Creating test signal data...")
    test_signal = create_test_signal_data()
    logger.info(f"Created test signal for {test_signal['symbol']} with score {test_signal['confluence_score']}")
    
    # Save original signal data
    original_filepath = await save_signal_data(test_signal, 'original_weighted_signal.json')
    logger.info(f"Saved original signal data to {original_filepath}")
    
    # Step 4: Generate enhanced data directly to test weighted subcomponents
    logger.info("\nStep 4: Testing _generate_enhanced_formatted_data...")
    
    # Set thresholds
    signal_generator.thresholds = {'buy': 65.0, 'sell': 40.0}
    
    enhanced_data = signal_generator._generate_enhanced_formatted_data(
        symbol=test_signal['symbol'],
        confluence_score=test_signal['confluence_score'],
        components=test_signal['components'],
        results=test_signal['results'],
        reliability=test_signal['reliability'],
        buy_threshold=signal_generator.thresholds['buy'],
        sell_threshold=signal_generator.thresholds['sell']
    )
    
    # Print the weighted sub-components
    if 'top_weighted_subcomponents' in enhanced_data:
        logger.info("\nTop Weighted Sub-Components:")
        for i, sub_comp in enumerate(enhanced_data['top_weighted_subcomponents']):
            sub_name = sub_comp.get('display_name', 'Unknown')
            parent_name = sub_comp.get('parent_display_name', 'Unknown')
            raw_score = sub_comp.get('score', 0)
            parent_weight = sub_comp.get('parent_weight', 0)
            impact = sub_comp.get('weighted_impact', 0) * 100  # Convert to percentage
            
            logger.info(f"{i+1}. {sub_name} ({parent_name}):")
            logger.info(f"   - Raw Score: {raw_score:.1f}")
            logger.info(f"   - Parent Weight: {parent_weight:.3f}")
            logger.info(f"   - Weighted Impact: {impact:.2f}% of total score")
    else:
        logger.error("No top_weighted_subcomponents found in enhanced data!")
        
    # Save enhanced data
    enhanced_test_signal = test_signal.copy()
    enhanced_test_signal.update(enhanced_data)
    enhanced_filepath = await save_signal_data(enhanced_test_signal, 'enhanced_weighted_signal.json')
    logger.info(f"Saved enhanced signal data to {enhanced_filepath}")
    
    # Step 5: Process signal with AlertManager
    logger.info("\nStep 5: Processing signal through complete flow...")
    
    # Test the integration with the actual signal processing flow
    try:
        logger.info("Testing process_signal method...")
        await signal_generator.process_signal(test_signal)
        logger.info("Signal processed successfully")
    except Exception as e:
        logger.error(f"Error in process_signal: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("\nTest completed!")

if __name__ == "__main__":
    logger.info("Starting weighted sub-components test...")
    asyncio.run(test_weighted_subcomponents()) 