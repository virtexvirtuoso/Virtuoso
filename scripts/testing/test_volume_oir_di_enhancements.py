#!/usr/bin/env python3

"""
Test script to demonstrate volume and OIR/DI enhancements.

This script tests the enhanced non-linear transformations for:
1. Volume indicators (trend, volatility, relative volume)
2. Orderbook indicators (OIR, DI)

The enhancements fix linear scoring problems by using:
- Sigmoid transformations for smooth extreme value handling
- Exponential decay for volume spikes
- Hyperbolic tangent scaling with confidence weighting
"""

import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.orderbook_indicators import OrderbookIndicators

def test_volume_enhancements():
    """Test enhanced volume indicator methods."""
    print("=" * 80)
    print("TESTING VOLUME ENHANCEMENTS")
    print("=" * 80)
    
    # Create volume indicators instance
    config = {
        'analysis': {
            'indicators': {
                'volume': {
                    'parameters': {
                        'rel_vol_period': 20
                    }
                }
            }
        },
        'timeframes': {
            'base': {'weight': 0.5, 'interval': 60},
            'ltf': {'weight': 0.15, 'interval': 15},
            'mtf': {'weight': 0.20, 'interval': 240},
            'htf': {'weight': 0.15, 'interval': 1440}
        }
    }
    
    volume_indicators = VolumeIndicators(config)
    
    # Test data - simulating different volume scenarios
    test_scenarios = [
        {"name": "Normal Volume (1.0x)", "rel_vol": 1.0},
        {"name": "High Volume (2.5x)", "rel_vol": 2.5},
        {"name": "Extreme Volume (5.0x)", "rel_vol": 5.0},
        {"name": "Very Extreme Volume (10.0x)", "rel_vol": 10.0},
        {"name": "Low Volume (0.5x)", "rel_vol": 0.5},
    ]
    
    # Create mock market data
    dates = pd.date_range('2024-01-01', periods=50, freq='1H')
    
    for scenario in test_scenarios:
        print(f"\n--- {scenario['name']} ---")
        
        # Create DataFrame with varying volume
        base_volume = 1000
        volumes = np.random.normal(base_volume, base_volume * 0.1, 49)
        volumes = np.append(volumes, base_volume * scenario['rel_vol'])  # Last candle has test volume
        
        df = pd.DataFrame({
            'open': np.random.normal(50000, 1000, 50),
            'high': np.random.normal(50500, 1000, 50),
            'low': np.random.normal(49500, 1000, 50),
            'close': np.random.normal(50000, 1000, 50),
            'volume': volumes
        }, index=dates)
        
        market_data = {
            'ohlcv': {
                'base': df
            }
        }
        
        # Test enhanced relative volume
        try:
            enhanced_score = volume_indicators._calculate_enhanced_relative_volume_score(market_data)
            print(f"Enhanced Relative Volume Score: {enhanced_score:.2f}")
        except Exception as e:
            print(f"Error in enhanced relative volume: {e}")
        
        # Test enhanced volume trend
        try:
            trend_score = volume_indicators._calculate_enhanced_volume_trend_score(df)
            print(f"Enhanced Volume Trend Score: {trend_score:.2f}")
        except Exception as e:
            print(f"Error in enhanced volume trend: {e}")
        
        # Test enhanced volume volatility
        try:
            volatility_score = volume_indicators._calculate_enhanced_volume_volatility_score(df)
            print(f"Enhanced Volume Volatility Score: {volatility_score:.2f}")
        except Exception as e:
            print(f"Error in enhanced volume volatility: {e}")

def test_oir_di_enhancements():
    """Test enhanced OIR and DI methods."""
    print("\n" + "=" * 80)
    print("TESTING OIR/DI ENHANCEMENTS")
    print("=" * 80)
    
    # Create orderbook indicators instance
    config = {
        'orderbook': {
            'depth_levels': 10
        }
    }
    
    orderbook_indicators = OrderbookIndicators(config)
    
    # Test scenarios for orderbook imbalances
    test_scenarios = [
        {
            "name": "Balanced Orderbook",
            "bid_volumes": [1000, 800, 600, 400, 200],
            "ask_volumes": [1000, 800, 600, 400, 200]
        },
        {
            "name": "Strong Bid Imbalance",
            "bid_volumes": [2000, 1500, 1000, 800, 600],
            "ask_volumes": [500, 400, 300, 200, 100]
        },
        {
            "name": "Strong Ask Imbalance", 
            "bid_volumes": [500, 400, 300, 200, 100],
            "ask_volumes": [2000, 1500, 1000, 800, 600]
        },
        {
            "name": "Extreme Bid Imbalance",
            "bid_volumes": [5000, 3000, 2000, 1000, 500],
            "ask_volumes": [200, 150, 100, 50, 25]
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n--- {scenario['name']} ---")
        
        # Create mock orderbook data
        bid_prices = [50000 - i * 10 for i in range(5)]
        ask_prices = [50000 + i * 10 for i in range(5)]
        
        bids = np.array([[price, volume] for price, volume in zip(bid_prices, scenario['bid_volumes'])])
        asks = np.array([[price, volume] for price, volume in zip(ask_prices, scenario['ask_volumes'])])
        
        # Test original methods
        try:
            original_oir = orderbook_indicators._calculate_oir_score(bids, asks)
            original_di = orderbook_indicators._calculate_di_score(bids, asks)
            print(f"Original OIR Score: {original_oir:.2f}")
            print(f"Original DI Score: {original_di:.2f}")
        except Exception as e:
            print(f"Error in original methods: {e}")
        
        # Test enhanced methods
        try:
            enhanced_oir = orderbook_indicators._calculate_enhanced_oir_score(bids, asks)
            enhanced_di = orderbook_indicators._calculate_enhanced_di_score(bids, asks)
            print(f"Enhanced OIR Score: {enhanced_oir:.2f}")
            print(f"Enhanced DI Score: {enhanced_di:.2f}")
        except Exception as e:
            print(f"Error in enhanced methods: {e}")
        
        # Calculate raw metrics for comparison
        total_bid_volume = sum(scenario['bid_volumes'])
        total_ask_volume = sum(scenario['ask_volumes'])
        raw_oir = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)
        raw_di = total_bid_volume - total_ask_volume
        
        print(f"Raw OIR: {raw_oir:.4f}")
        print(f"Raw DI: {raw_di:.0f}")
        print(f"Enhancement Difference - OIR: {enhanced_oir - original_oir:.2f}, DI: {enhanced_di - original_di:.2f}")

def main():
    """Run all enhancement tests."""
    print("Testing Volume and OIR/DI Enhancements")
    print("This demonstrates the non-linear transformations that fix linear scoring problems")
    print()
    
    # Test volume enhancements
    test_volume_enhancements()
    
    # Test OIR/DI enhancements
    test_oir_di_enhancements()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("✅ Volume Enhancements:")
    print("   - Enhanced relative volume with exponential decay for extreme values")
    print("   - Enhanced volume trend with sigmoid transformation")
    print("   - Enhanced volume volatility with extreme value handling")
    print()
    print("✅ OIR/DI Enhancements:")
    print("   - Enhanced OIR with confidence weighting and improved tanh scaling")
    print("   - Enhanced DI with market context and combined absolute/relative scaling")
    print()
    print("These enhancements fix the linear scoring problems identified in the analysis")
    print("by providing better differentiation at extreme values and smoother transitions.")

if __name__ == "__main__":
    main() 