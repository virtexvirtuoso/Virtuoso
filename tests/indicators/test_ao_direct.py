#!/usr/bin/env python3
"""Direct test script for the Awesome Oscillator calculation logic."""

import os
import sys
import logging
import pandas as pd
import numpy as np
import talib
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Optional, Union, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_ao(df, fast_period=5, slow_period=34):
    """Calculate Awesome Oscillator."""
    if 'high' not in df or 'low' not in df:
        logger.error("DataFrame must contain 'high' and 'low' columns")
        return None
        
    # Calculate median price
    median_price = (df['high'] + df['low']) / 2
    
    # Calculate AO using SMA
    fast_sma = talib.SMA(median_price, timeperiod=fast_period)
    slow_sma = talib.SMA(median_price, timeperiod=slow_period)
    ao = fast_sma - slow_sma
    
    return ao

def interpret_ao(current_ao: float, prev_ao: float = None, ao_series: pd.Series = None) -> Dict[str, Any]:
    """
    Interpret Awesome Oscillator values and identify patterns.
    
    Args:
        current_ao: Current AO value
        prev_ao: Previous AO value (if available)
        ao_series: Historical AO series for context (if available)
        
    Returns:
        Dictionary with interpretation and detected patterns
    """
    interpretation = ""
    patterns = []
    
    # Handle zero line crossings
    if prev_ao is not None:
        if prev_ao < 0 and current_ao > 0:
            patterns.append({
                "name": "Zero Line Cross (Bullish)",
                "description": "AO crossed above zero line, indicating potential upward momentum",
                "strength": "strong"
            })
            interpretation += "Bullish zero line cross detected. "
        elif prev_ao > 0 and current_ao < 0:
            patterns.append({
                "name": "Zero Line Cross (Bearish)",
                "description": "AO crossed below zero line, indicating potential downward momentum",
                "strength": "strong"
            })
            interpretation += "Bearish zero line cross detected. "
    
    # Evaluate AO significance relative to historical volatility
    if ao_series is not None and len(ao_series) > 10:
        ao_std = ao_series.std()
        if ao_std > 0:
            ao_strength = abs(current_ao) / ao_std
            
            if ao_strength > 2.0:
                significance = "extreme"
            elif ao_strength > 1.5:
                significance = "strong"
            elif ao_strength > 1.0:
                significance = "significant"
            elif ao_strength > 0.5:
                significance = "moderate"
            else:
                significance = "mild"
                
            direction = "bullish" if current_ao > 0 else "bearish"
            interpretation += f"AO shows {significance} {direction} momentum. "
    
    # Detect saucer patterns
    if ao_series is not None and len(ao_series) >= 5:
        last_values = ao_series.tail(5).values
        
        # Bullish saucer (above zero)
        if (all(v > 0 for v in last_values) and 
            last_values[0] > last_values[1] > last_values[2] and
            last_values[2] < last_values[3] < last_values[4]):
            patterns.append({
                "name": "Bullish Saucer",
                "description": "AO formed a bullish saucer pattern above zero line",
                "strength": "strong"
            })
            interpretation += "Bullish saucer pattern detected above zero line. "
            
        # Bearish saucer (below zero)
        if (all(v < 0 for v in last_values) and 
            last_values[0] < last_values[1] < last_values[2] and
            last_values[2] > last_values[3] > last_values[4]):
            patterns.append({
                "name": "Bearish Saucer",
                "description": "AO formed a bearish saucer pattern below zero line",
                "strength": "strong"
            })
            interpretation += "Bearish saucer pattern detected below zero line. "
    
    # Momentum analysis
    if prev_ao is not None:
        ao_change_pct = 0
        if abs(prev_ao) > 0.0001:
            ao_change_pct = ((current_ao - prev_ao) / abs(prev_ao)) * 100
            
        if abs(ao_change_pct) > 50:
            momentum = "rapidly"
        elif abs(ao_change_pct) > 20:
            momentum = "quickly"
        elif abs(ao_change_pct) > 10:
            momentum = "steadily"
        elif abs(ao_change_pct) > 5:
            momentum = "gradually"
        else:
            momentum = "slowly"
            
        if current_ao > prev_ao:
            interpretation += f"AO is {momentum} increasing. "
        elif current_ao < prev_ao:
            interpretation += f"AO is {momentum} decreasing. "
        else:
            interpretation += "AO is unchanged. "
    
    # Summary interpretation if no specific patterns detected
    if not patterns and not interpretation:
        if current_ao > 0:
            interpretation = "AO is positive, suggesting upward momentum."
        elif current_ao < 0:
            interpretation = "AO is negative, suggesting downward momentum."
        else:
            interpretation = "AO is at zero, suggesting neutral momentum."
    
    return {
        "value": current_ao,
        "interpretation": interpretation.strip(),
        "patterns": patterns
    }

def create_test_data():
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
    
    # Add timestamps
    for key in patterns:
        idx = pd.date_range(start='2023-01-01', periods=len(patterns[key]), freq='5min')
        patterns[key].index = idx
    
    return patterns

def plot_ao(df, ao_values, title, output_file):
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

def main():
    """Test the AO calculations and pattern detection."""
    # Create test data
    test_data = create_test_data()
    
    for pattern_name, df in test_data.items():
        logger.info(f"\n===== Testing {pattern_name} pattern =====")
        
        # Calculate AO
        ao_values = calculate_ao(df)
        ao_values = ao_values.dropna()
        
        # Plot chart with AO
        plot_ao(df, ao_values, pattern_name.replace('_', ' ').title(), f'ao_test_{pattern_name}.png')
        
        # Get latest values
        current_ao = ao_values.iloc[-1]
        prev_ao = ao_values.iloc[-2]
        
        # Interpret AO
        ao_interpretation = interpret_ao(current_ao, prev_ao, ao_values)
        
        # Print interpretation
        logger.info(f"AO Raw Value: {current_ao:.6f}")
        logger.info(f"AO Interpretation: {ao_interpretation['interpretation']}")
        
        if ao_interpretation['patterns']:
            logger.info("Detected Patterns:")
            for pattern in ao_interpretation['patterns']:
                logger.info(f"  - {pattern['name']}: {pattern['description']} (Strength: {pattern['strength']})")
        else:
            logger.info("No patterns detected")
    
    # Success message
    logger.info("\nAO testing completed successfully")

if __name__ == "__main__":
    main() 