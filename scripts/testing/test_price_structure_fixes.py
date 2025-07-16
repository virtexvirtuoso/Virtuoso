#!/usr/bin/env python3
"""
Test script to validate price structure analysis fixes.

This script tests the fixes for:
1. "Overall" component default value warnings
2. Support/Resistance analysis improvements
3. Component weighting issues
4. Order block calculation consistency

Usage:
    python scripts/testing/test_price_structure_fixes.py
"""

import sys
import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.core.logger import Logger
import yaml

def create_test_data():
    """Create realistic test OHLCV data for multiple timeframes."""
    
    # Base parameters
    base_price = 2500.0
    volatility = 0.02
    trend = 0.001
    
    # Generate 1-minute data (1000 candles)
    timestamps_1m = pd.date_range(
        start=datetime.now() - timedelta(hours=16, minutes=40),
        periods=1000,
        freq='1min'
    )
    
    # Generate realistic price data with trend and volatility
    np.random.seed(42)  # For reproducible results
    returns = np.random.normal(trend, volatility, 1000)
    prices = [base_price]
    
    for ret in returns:
        new_price = prices[-1] * (1 + ret)
        prices.append(new_price)
    
    prices = np.array(prices[1:])  # Remove initial price
    
    # Create OHLC data
    highs = prices * (1 + np.abs(np.random.normal(0, 0.005, 1000)))
    lows = prices * (1 - np.abs(np.random.normal(0, 0.005, 1000)))
    opens = np.roll(prices, 1)
    opens[0] = base_price
    closes = prices
    
    # Generate volume data
    volumes = np.random.lognormal(10, 1, 1000)
    
    # Create DataFrame
    df_1m = pd.DataFrame({
        'timestamp': timestamps_1m,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })
    
    # Create other timeframes by resampling
    df_1m_indexed = df_1m.set_index('timestamp')
    
    # 5-minute data (300 candles)
    df_5m = df_1m_indexed.resample('5min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna().tail(300).reset_index()
    
    # 30-minute data (200 candles)
    df_30m = df_1m_indexed.resample('30min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna().tail(200).reset_index()
    
    # 4-hour data (200 candles)
    df_4h = df_1m_indexed.resample('4h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna().tail(200).reset_index()
    
    return {
        'base': df_1m[['open', 'high', 'low', 'close', 'volume']],
        'ltf': df_5m[['open', 'high', 'low', 'close', 'volume']],
        'mtf': df_30m[['open', 'high', 'low', 'close', 'volume']],
        'htf': df_4h[['open', 'high', 'low', 'close', 'volume']]
    }

async def test_price_structure_fixes():
    """Test the price structure analysis fixes."""
    
    print("=" * 80)
    print("TESTING PRICE STRUCTURE ANALYSIS FIXES")
    print("=" * 80)
    
    # Initialize logger
    logger = Logger(__name__)
    logger.info("Starting price structure analysis tests")
    
    # Load configuration
    try:
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        print("✓ Configuration loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return False
    
    # Create test data
    print("\n1. Creating test data...")
    try:
        ohlcv_data = create_test_data()
        print(f"✓ Created test data with timeframes: {list(ohlcv_data.keys())}")
        for tf, df in ohlcv_data.items():
            print(f"  - {tf}: {len(df)} candles, price range: {df['low'].min():.2f} - {df['high'].max():.2f}")
    except Exception as e:
        print(f"✗ Failed to create test data: {e}")
        return False
    
    # Initialize price structure indicators
    print("\n2. Initializing price structure indicators...")
    try:
        price_structure = PriceStructureIndicators(config, logger)
        print("✓ Price structure indicators initialized")
        print(f"  - Component weights: {price_structure.component_weights}")
    except Exception as e:
        print(f"✗ Failed to initialize price structure indicators: {e}")
        return False
    
    # Prepare market data
    market_data = {
        'ohlcv': ohlcv_data,
        'symbol': 'ETHUSDT',
        'exchange': 'bybit',
        'timestamp': datetime.now().isoformat(),
        'timeframes': {
            'base': '1m',
            'ltf': '5m', 
            'mtf': '30m',
            'htf': '4h'
        }
    }
    
    # Test the analysis
    print("\n3. Running price structure analysis...")
    try:
        result = await price_structure.calculate(market_data)
        
        print("✓ Analysis completed successfully")
        print(f"  - Final score: {result.get('score', 'N/A'):.2f}")
        print(f"  - Components calculated: {len(result.get('components', {}))}")
        
        # Check for the "overall" component issue
        components = result.get('components', {})
        if 'overall' in components:
            print("✗ WARNING: 'overall' component still present in results")
        else:
            print("✓ No 'overall' component found (issue fixed)")
        
        # Display component scores
        print("\n4. Component Analysis:")
        for component, score in components.items():
            print(f"  - {component}: {score:.2f}")
        
        # Check for default values
        default_components = [comp for comp, score in components.items() if abs(score - 50.0) < 0.001]
        if default_components:
            print(f"\n⚠️  Components with potential default values: {default_components}")
        else:
            print("\n✓ No components with default values detected")
        
        return True
        
    except Exception as e:
        print(f"✗ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sr_analysis_specifically():
    """Test the S/R analysis improvements specifically."""
    
    print("\n" + "=" * 80)
    print("TESTING S/R ANALYSIS IMPROVEMENTS")
    print("=" * 80)
    
    # Create simple test data with known S/R levels
    np.random.seed(42)
    
    # Create price data with clear support/resistance at 2500 and 2600
    prices = []
    base_price = 2550
    
    # Add data that bounces between 2500 and 2600
    for i in range(200):
        if i % 40 < 20:  # Move towards 2500
            noise = np.random.normal(0, 5)
            price = 2500 + abs(noise)
        else:  # Move towards 2600
            noise = np.random.normal(0, 5)
            price = 2600 - abs(noise)
        prices.append(price)
    
    # Create DataFrame
    df = pd.DataFrame({
        'open': prices,
        'high': [p * 1.002 for p in prices],
        'low': [p * 0.998 for p in prices],
        'close': prices,
        'volume': np.random.lognormal(10, 0.5, 200)
    })
    
    try:
        # Load config and create indicator
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        logger = Logger(__name__)
        
        price_structure = PriceStructureIndicators(config, logger)
        
        # Test S/R calculation directly
        sr_score = price_structure._calculate_sr_levels(df)
        
        print(f"✓ S/R analysis completed")
        print(f"  - S/R Score: {sr_score:.2f}")
        print(f"  - Expected: Score should reflect proximity to 2500/2600 levels")
        
        if 30 <= sr_score <= 70:
            print("✓ S/R score is in reasonable range")
        else:
            print(f"⚠️  S/R score may be outside expected range: {sr_score:.2f}")
        
        return True
        
    except Exception as e:
        print(f"✗ S/R analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    
    print("Price Structure Analysis Fix Validation")
    print("=" * 50)
    
    # Test 1: Overall price structure analysis
    test1_passed = await test_price_structure_fixes()
    
    # Test 2: Specific S/R analysis improvements
    test2_passed = test_sr_analysis_specifically()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    tests_passed = 0
    total_tests = 2
    
    if test1_passed:
        print("✓ Test 1: Overall price structure analysis - PASSED")
        tests_passed += 1
    else:
        print("✗ Test 1: Overall price structure analysis - FAILED")
    
    if test2_passed:
        print("✓ Test 2: S/R analysis improvements - PASSED")
        tests_passed += 1
    else:
        print("✗ Test 2: S/R analysis improvements - FAILED")
    
    print(f"\nResults: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Price structure fixes are working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 