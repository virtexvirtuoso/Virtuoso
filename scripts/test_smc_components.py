#!/usr/bin/env python3
"""
Test script for Smart Money Concepts (SMC) components in Price Structure Indicators.

This script tests the newly added SMC components:
1. Fair Value Gaps (FVG)
2. Liquidity Zones
3. Break of Structure (BOS) & Change of Character (CHoCH)
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add the project root to the path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.core.logger import Logger

def create_test_data(num_candles=200):
    """Create realistic test OHLCV data with patterns for SMC detection."""
    
    # Generate base price data with trend and volatility
    np.random.seed(42)  # For reproducible results
    
    # Start with a base price
    base_price = 50000.0
    prices = [base_price]
    
    # Generate price movements with some trend and volatility
    for i in range(num_candles - 1):
        # Add some trend (slight upward bias)
        trend = 0.001 if i < num_candles // 2 else -0.001
        
        # Add volatility
        volatility = np.random.normal(0, 0.02)
        
        # Calculate next price
        next_price = prices[-1] * (1 + trend + volatility)
        prices.append(next_price)
    
    # Create timestamps
    start_time = datetime.now() - timedelta(hours=num_candles)
    timestamps = [start_time + timedelta(hours=i) for i in range(num_candles)]
    
    # Generate OHLCV data
    data = []
    for i, (timestamp, close) in enumerate(zip(timestamps, prices)):
        # Generate realistic OHLC from close price
        volatility = abs(np.random.normal(0, 0.01))
        
        high = close * (1 + volatility)
        low = close * (1 - volatility)
        
        # Ensure open is between high and low
        open_price = low + (high - low) * np.random.random()
        
        # Generate volume
        volume = np.random.uniform(1000, 10000)
        
        data.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    
    # Add some specific patterns for testing
    
    # Create a Fair Value Gap around index 50
    if len(df) > 55:
        # Bullish FVG: previous high < next low
        df.loc[df.index[49], 'high'] = df.loc[df.index[49], 'close'] * 0.995  # Lower previous high
        df.loc[df.index[51], 'low'] = df.loc[df.index[51], 'close'] * 1.005   # Higher next low
        df.loc[df.index[50], 'close'] = df.loc[df.index[50], 'open'] * 1.02   # Strong bullish candle
    
    # Create liquidity zones with clustered swing highs around index 100
    if len(df) > 105:
        base_level = df.loc[df.index[100], 'close']
        for i in range(98, 103):
            df.loc[df.index[i], 'high'] = base_level * (1 + np.random.uniform(-0.002, 0.002))
    
    return df

def test_smc_components():
    """Test the Smart Money Concepts components."""
    
    print("=== Testing Smart Money Concepts Components ===\n")
    
    # Create test configuration
    config = {
        'timeframes': {
            'base': {
                'interval': '1h', 
                'weight': 0.4,
                'validation': {'min_candles': 50}
            },
            'ltf': {
                'interval': '15m', 
                'weight': 0.2,
                'validation': {'min_candles': 50}
            },
            'mtf': {
                'interval': '4h', 
                'weight': 0.25,
                'validation': {'min_candles': 50}
            },
            'htf': {
                'interval': '1d', 
                'weight': 0.15,
                'validation': {'min_candles': 50}
            }
        },
        'analysis': {
            'indicators': {
                'price_structure': {
                    'parameters': {
                        'volume_profile': {
                            'value_area_percentage': 0.7
                        },
                        'vwap': {
                            'debug_logging': True,
                            'use_std_bands': True
                        }
                    }
                }
            }
        },
        'confluence': {
            'weights': {
                'sub_components': {
                    'price_structure': {
                        'support_resistance': 0.15,
                        'order_block': 0.15,
                        'trend_position': 0.15,
                        'volume_profile': 0.15,
                        'swing_structure': 0.15,
                        'vwap': 0.10,
                        'composite_value': 0.05,
                        'fair_value_gaps': 0.10,
                        'liquidity_zones': 0.10,
                        'bos_choch': 0.05
                    }
                }
            }
        }
    }
    
    # Create logger
    logger = Logger('test_smc')
    
    # Initialize Price Structure Indicators
    psi = PriceStructureIndicators(config, logger)
    
    # Create test data
    print("1. Creating test data...")
    df = create_test_data(200)
    print(f"   Created {len(df)} candles of test data")
    
    # Prepare market data in the expected format
    market_data = {
        'symbol': 'BTC/USDT',
        'ohlcv': {
            'base': df.copy(),
            'ltf': df.iloc[::2].copy(),   # Every 2nd candle for LTF
            'mtf': df.iloc[::5].copy(),   # Every 5th candle for MTF
            'htf': df.iloc[::10].copy()   # Every 10th candle for HTF
        }
    }
    
    print("\n2. Testing individual SMC components...")
    
    # Test Fair Value Gaps
    print("\n   a) Testing Fair Value Gaps (FVG)...")
    try:
        fvgs = psi._detect_fair_value_gaps(df)
        print(f"      - Detected {len(fvgs['bullish'])} bullish FVGs")
        print(f"      - Detected {len(fvgs['bearish'])} bearish FVGs")
        
        fvg_score = psi._calculate_fvg_score(market_data['ohlcv'])
        print(f"      - FVG Score: {fvg_score:.2f}")
        
    except Exception as e:
        print(f"      - Error testing FVG: {str(e)}")
    
    # Test Liquidity Zones
    print("\n   b) Testing Liquidity Zones...")
    try:
        liquidity_zones = psi._detect_liquidity_zones(df)
        print(f"      - Detected {len(liquidity_zones['bullish'])} bullish liquidity zones")
        print(f"      - Detected {len(liquidity_zones['bearish'])} bearish liquidity zones")
        
        liquidity_score = psi._calculate_liquidity_score(market_data['ohlcv'])
        print(f"      - Liquidity Score: {liquidity_score:.2f}")
        
    except Exception as e:
        print(f"      - Error testing Liquidity Zones: {str(e)}")
    
    # Test BOS/CHoCH
    print("\n   c) Testing Break of Structure (BOS) & Change of Character (CHoCH)...")
    try:
        swing_data = psi._detect_swing_highs_lows(df, swing_length=20)
        bos_choch = psi._detect_bos_choch(df, swing_data)
        print(f"      - Detected {len(bos_choch['bos'])} BOS events")
        print(f"      - Detected {len(bos_choch['choch'])} CHoCH events")
        
        bos_choch_score = psi._calculate_bos_choch_score(market_data['ohlcv'])
        print(f"      - BOS/CHoCH Score: {bos_choch_score:.2f}")
        
    except Exception as e:
        print(f"      - Error testing BOS/CHoCH: {str(e)}")
    
    print("\n3. Testing complete Price Structure analysis with SMC components...")
    
    # Test the complete analysis
    try:
        import asyncio
        
        async def run_analysis():
            result = await psi.calculate(market_data)
            return result
        
        # Run the async analysis
        result = asyncio.run(run_analysis())
        
        print(f"\n   Final Price Structure Score: {result['score']:.2f}")
        print("\n   Component Scores:")
        for component, score in result['components'].items():
            print(f"      - {component}: {score:.2f}")
        
        print(f"\n   Interpretation: {result['interpretation']}")
        
        # Check if SMC components are included
        smc_components = ['fair_value_gaps', 'liquidity_zones', 'bos_choch']
        missing_smc = [comp for comp in smc_components if comp not in result['components']]
        
        if missing_smc:
            print(f"\n   ⚠️  Missing SMC components: {missing_smc}")
        else:
            print(f"\n   ✅ All SMC components successfully integrated!")
            
    except Exception as e:
        print(f"   ❌ Error in complete analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_smc_components() 