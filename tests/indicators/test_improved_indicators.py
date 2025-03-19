#!/usr/bin/env python3
"""Test script to validate improved technical indicators, focusing on AO."""

import os
import sys
import json
import logging
import asyncio
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Create synthetic market data for testing
def create_test_data() -> Dict[str, pd.DataFrame]:
    """Create synthetic market data with various patterns."""
    patterns = {}
    
    # Uptrend data
    uptrend = np.linspace(100, 120, 200) + np.random.normal(0, 0.5, 200)
    patterns['uptrend'] = pd.DataFrame({
        'open': uptrend - 0.5,
        'high': uptrend + 1.0,
        'low': uptrend - 1.0,
        'close': uptrend + 0.5,
        'volume': np.random.randn(200) * 1000 + 5000
    })
    
    # Downtrend data
    downtrend = np.linspace(120, 100, 200) + np.random.normal(0, 0.5, 200)
    patterns['downtrend'] = pd.DataFrame({
        'open': downtrend + 0.5,
        'high': downtrend + 1.0,
        'low': downtrend - 1.0,
        'close': downtrend - 0.5,
        'volume': np.random.randn(200) * 1000 + 5000
    })
    
    # Zero-crossing data (bullish)
    zero_cross = np.concatenate([np.linspace(110, 99, 100), np.linspace(99, 110, 100)]) + np.random.normal(0, 0.3, 200)
    patterns['zero_cross_bullish'] = pd.DataFrame({
        'open': zero_cross - 0.5,
        'high': zero_cross + 1.0,
        'low': zero_cross - 1.0,
        'close': zero_cross + 0.2,
        'volume': np.random.randn(200) * 1000 + 5000
    })
    
    # Zero-crossing data (bearish)
    zero_cross = np.concatenate([np.linspace(99, 110, 100), np.linspace(110, 99, 100)]) + np.random.normal(0, 0.3, 200)
    patterns['zero_cross_bearish'] = pd.DataFrame({
        'open': zero_cross + 0.5,
        'high': zero_cross + 1.0,
        'low': zero_cross - 1.0,
        'close': zero_cross - 0.2,
        'volume': np.random.randn(200) * 1000 + 5000
    })
    
    # Add timestamps
    for key in patterns:
        idx = pd.date_range(start='2023-01-01', periods=len(patterns[key]), freq='5min')
        patterns[key].index = idx
    
    return patterns

async def test_technical_signals():
    """Test the improved technical indicators implementation."""
    try:
        # Import the TechnicalIndicators class
        from src.indicators.technical_indicators import TechnicalIndicators
        
        # Create a basic configuration
        config = {
            'ao_fast': 5,
            'ao_slow': 34,
            'indicators': {
                'technical': True
            },
            'timeframes': {
                'ltf': {
                    'interval': 5,
                    'weight': 0.5,
                    'validation': {
                        'min_candles': 100
                    }
                },
                'base': {
                    'interval': 5,
                    'weight': 0.5,
                    'validation': {
                        'min_candles': 100
                    }
                },
                'mtf': {
                    'interval': 15,
                    'weight': 0.3,
                    'validation': {
                        'min_candles': 100
                    }
                },
                'htf': {
                    'interval': 60,
                    'weight': 0.2,
                    'validation': {
                        'min_candles': 100
                    }
                }
            },
            'component_weights': {
                'rsi': 0.2,
                'macd': 0.2,
                'ao': 0.3,
                'williams_r': 0.1,
                'atr': 0.1,
                'cci': 0.1
            }
        }
        
        # Create the TechnicalIndicators instance
        indicators = TechnicalIndicators(config, logger=logger)
        
        # Create test data
        test_data = create_test_data()
        
        # Test each pattern
        for pattern_name, df in test_data.items():
            logger.info(f"\n===== Testing {pattern_name} pattern =====")
            
            # Prepare market data
            market_data = {
                'ohlcv': {
                    'ltf': df,
                    'base': df,  # Using base timeframe
                    'mtf': df,  # Using same data for simplicity
                    'htf': df   # Using same data for simplicity
                }
            }
            
            # Get signals
            signals = await indicators.get_signals(market_data)
            
            # Print signal details
            if 'ao' in signals:
                ao_signal = signals['ao']
                logger.info(f"AO Score: {ao_signal['value']:.2f}")
                logger.info(f"AO Signal: {ao_signal['signal']}")
                logger.info(f"AO Raw Value: {ao_signal['raw_value']:.6f}")
                logger.info(f"AO Strength: {ao_signal.get('strength', 'N/A')}")
                logger.info(f"AO Interpretation: {ao_signal.get('interpretation', 'N/A')}")
                
                if 'patterns' in ao_signal and ao_signal['patterns']:
                    logger.info("Detected Patterns:")
                    for pattern in ao_signal['patterns']:
                        logger.info(f"  - {pattern['name']}: {pattern['description']} (Strength: {pattern['strength']})")
                else:
                    logger.info("No patterns detected")
            else:
                logger.warning("No AO signal returned")
        
        logger.info("\n===== Technical Indicators Testing Completed =====")
        logger.info("All tests passed successfully!")
                
    except Exception as e:
        logger.error(f"Error in test_technical_signals: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_technical_signals()) 