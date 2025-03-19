#!/usr/bin/env python3
"""Comprehensive test script for the improved Awesome Oscillator calculations."""

import os
import sys
import json
import asyncio
import logging
import pandas as pd
import numpy as np
import talib
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Optional, Union, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Import our indicator code
try:
    from src.indicators.technical_indicators import TechnicalIndicators
    from src.indicators.base_indicator import BaseIndicator
    logger.info("Successfully imported indicator modules")
except ImportError as e:
    logger.error(f"Error importing indicator modules: {str(e)}")
    sys.exit(1)

def create_test_data() -> Dict[str, pd.DataFrame]:
    """Create synthetic market data for testing."""
    
    # Test patterns
    patterns = {}
    
    # Uptrend data
    patterns['uptrend'] = pd.DataFrame({
        'open': np.linspace(100, 120, 200),
        'high': np.linspace(101, 122, 200) + np.random.normal(0, 0.5, 200),
        'low': np.linspace(99, 118, 200) - np.random.normal(0, 0.5, 200),
        'close': np.linspace(100, 120, 200) + np.random.normal(0, 0.3, 200),
        'volume': np.random.randn(200) * 1000 + 5000
    })
    
    # Downtrend data
    patterns['downtrend'] = pd.DataFrame({
        'open': np.linspace(120, 100, 200),
        'high': np.linspace(122, 101, 200) + np.random.normal(0, 0.5, 200),
        'low': np.linspace(118, 99, 200) - np.random.normal(0, 0.5, 200),
        'close': np.linspace(120, 100, 200) + np.random.normal(0, 0.3, 200),
        'volume': np.random.randn(200) * 1000 + 5000
    })
    
    # Sideways data
    patterns['sideways'] = pd.DataFrame({
        'open': np.random.normal(100, 0.5, 200),
        'high': [max(100 + np.random.normal(1, 0.3), o) for o in np.random.normal(100, 0.5, 200)],
        'low': [min(100 - np.random.normal(1, 0.3), o) for o in np.random.normal(100, 0.5, 200)],
        'close': np.random.normal(100, 0.5, 200),
        'volume': np.random.randn(200) * 1000 + 5000
    })
    
    # Zero-crossing data (bullish)
    patterns['zero_cross_bullish'] = pd.DataFrame({
        'open': np.concatenate([np.linspace(110, 100, 100), np.linspace(100, 110, 100)]),
        'high': np.concatenate([np.linspace(112, 101, 100), np.linspace(101, 112, 100)]) + np.random.normal(0, 0.5, 200),
        'low': np.concatenate([np.linspace(108, 99, 100), np.linspace(99, 108, 100)]) - np.random.normal(0, 0.5, 200),
        'close': np.concatenate([np.linspace(110, 100, 100), np.linspace(100, 110, 100)]) + np.random.normal(0, 0.3, 200),
        'volume': np.random.randn(200) * 1000 + 5000
    })
    
    # Bullish saucer pattern
    values = np.random.normal(100, 0.5, 200)
    # Create dip in the middle for saucer
    values[90:110] = values[90:110] * 0.9
    values[110:150] = values[110:150] * 1.1  # Increase after dip
    
    patterns['saucer_bullish'] = pd.DataFrame({
        'open': values - 0.5,
        'high': values + 1,
        'low': values - 1,
        'close': values + 0.5,
        'volume': np.random.randn(200) * 1000 + 5000
    })
    
    # Bearish saucer pattern
    values = np.random.normal(100, 0.5, 200)
    # Create bump in the middle for inverted saucer
    values[90:110] = values[90:110] * 1.1
    values[110:150] = values[110:150] * 0.9  # Decrease after bump
    
    patterns['saucer_bearish'] = pd.DataFrame({
        'open': values + 0.5,
        'high': values + 1,
        'low': values - 1,
        'close': values - 0.5,
        'volume': np.random.randn(200) * 1000 + 5000
    })
    
    # Twin peaks bullish pattern
    values = np.concatenate([
        np.linspace(100, 90, 50),      # First decline
        np.linspace(90, 95, 30),       # First recovery
        np.linspace(95, 85, 30),       # Second decline (higher low)
        np.linspace(85, 110, 90)       # Final recovery
    ])
    
    patterns['twin_peaks_bullish'] = pd.DataFrame({
        'open': values - 0.5,
        'high': values + 1,
        'low': values - 1,
        'close': values + 0.5,
        'volume': np.random.randn(200) * 1000 + 5000
    })
    
    # Twin peaks bearish pattern
    values = np.concatenate([
        np.linspace(100, 110, 50),     # First climb
        np.linspace(110, 105, 30),     # First pullback
        np.linspace(105, 108, 30),     # Second climb (lower high)
        np.linspace(108, 90, 90)       # Final decline
    ])
    
    patterns['twin_peaks_bearish'] = pd.DataFrame({
        'open': values + 0.5,
        'high': values + 1,
        'low': values - 1,
        'close': values - 0.5,
        'volume': np.random.randn(200) * 1000 + 5000
    })
    
    # Add timestamps
    for key in patterns:
        idx = pd.date_range(start='2023-01-01', periods=len(patterns[key]), freq='5min')
        patterns[key].index = idx
    
    return patterns

def plot_ao(df: pd.DataFrame, ao_values: pd.Series, title: str, output_file: str) -> None:
    """Plot price chart and AO indicator."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
    
    # Plot price data
    ax1.plot(df.index, df['close'], label='Close Price')
    ax1.set_title(f'{title} - Price Chart')
    ax1.legend()
    ax1.grid(True)
    
    # Plot AO
    colors = ['green' if ao_values.iloc[i] > ao_values.iloc[i-1] else 'red' for i in range(1, len(ao_values))]
    colors.insert(0, 'green')  # Default color for first bar
    
    ax2.bar(ao_values.index, ao_values, color=colors)
    ax2.axhline(y=0, color='black', linestyle='-')
    ax2.set_title('Awesome Oscillator')
    ax2.grid(True)
    
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()
    logger.info(f"Chart saved to {output_file}")

async def test_ao_calculations() -> None:
    """Test the AO calculations and signal generation."""
    # Create test data
    test_data = create_test_data()
    
    # Create config for indicators
    config = {
        'ao_fast': 5,
        'ao_slow': 34,
        'timeframes': {
            'ltf': {
                'interval': 5,  # 5-minute interval
                'weight': 0.5,  # Weight for this timeframe
                'validation': {
                    'min_candles': 100
                }
            },
            'mtf': {
                'interval': 15,  # 15-minute interval
                'weight': 0.3,  # Weight for this timeframe
                'validation': {
                    'min_candles': 100
                }
            },
            'htf': {
                'interval': 60,  # 60-minute interval
                'weight': 0.2,  # Weight for this timeframe
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
    
    # Initialize the technical indicators
    indicators = TechnicalIndicators(config)
    
    results = {}
    
    for pattern_name, df in test_data.items():
        logger.info(f"\n===== Testing {pattern_name} pattern =====")
        
        # Calculate median price and raw AO values
        median_price = (df['high'] + df['low']) / 2
        ao_fast_sma = talib.SMA(median_price, timeperiod=config['ao_fast'])
        ao_slow_sma = talib.SMA(median_price, timeperiod=config['ao_slow'])
        ao_values = ao_fast_sma - ao_slow_sma
        ao_values = ao_values.dropna()
        
        # Plot chart with AO
        plot_ao(df, ao_values, pattern_name.replace('_', ' ').title(), f'ao_test_{pattern_name}.png')
        
        # Calculate AO score and signals
        market_data = {
            'ohlcv': {
                'ltf': df,
                'mtf': df,  # Using same data for simplicity in testing
                'htf': df   # Using same data for simplicity in testing
            }
        }
        
        # Store AO data in cache for interpretation
        indicators._data_cache = {'ltf': df, 'mtf': df, 'htf': df}
        
        # Calculate AO score
        ao_score = indicators._calculate_ao_score(df)
        logger.info(f"AO Score: {ao_score:.2f}")
        
        # Get all signals
        signals = await indicators.get_signals(market_data)
        
        # Print AO signals and patterns
        if 'ao' in signals:
            ao_signal = signals['ao']
            logger.info(f"AO Signal: {ao_signal['signal']}")
            logger.info(f"AO Raw Value: {ao_signal['raw_value']:.6f}")
            logger.info(f"AO Interpretation: {ao_signal.get('interpretation', 'N/A')}")
            
            if 'patterns' in ao_signal and ao_signal['patterns']:
                logger.info("Detected Patterns:")
                for pattern in ao_signal['patterns']:
                    logger.info(f"  - {pattern['name']}: {pattern['description']} (Strength: {pattern['strength']})")
            else:
                logger.info("No patterns detected")
        
        # Store results for comparison
        results[pattern_name] = {
            'score': ao_score,
            'signals': signals
        }
    
    # Compare results
    logger.info("\n===== Result Summary =====")
    for pattern, result in results.items():
        logger.info(f"{pattern.replace('_', ' ').title()}: Score={result['score']:.2f}, Signal={result['signals'].get('ao', {}).get('signal', 'N/A')}")
    
    # Success message
    logger.info("\nAO testing completed successfully")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_ao_calculations()) 