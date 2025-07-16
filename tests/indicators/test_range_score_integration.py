#!/usr/bin/env python3
"""
Test script for Range Score Integration - Professional Range Analysis Implementation

This script tests the comprehensive range score integration that was added to the
PriceStructureIndicators class following the implementation plan.

Tests cover:
1. Range detection functionality
2. Range scoring logic
3. System integration
4. Component weight handling
5. Multi-timeframe analysis
6. Volume confirmation
7. EQ interactions
8. Range deviations

Author: AI Assistant
Date: 2024
"""

import sys
import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from indicators.price_structure_indicators import PriceStructureIndicators

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_mock_range_data(start_price: float = 100.0, range_size: float = 5.0, num_bars: int = 200) -> pd.DataFrame:
    """
    Create mock OHLCV data that forms a clear range pattern.
    
    Args:
        start_price: Starting price level
        range_size: Size of the range (high - low)
        num_bars: Number of bars to generate
        
    Returns:
        pd.DataFrame: Mock OHLCV data with range pattern
    """
    np.random.seed(42)  # For reproducible results
    
    range_high = start_price + (range_size / 2)
    range_low = start_price - (range_size / 2)
    eq_level = start_price
    
    data = []
    current_price = start_price
    
    for i in range(num_bars):
        # Create range-bound price action
        if i < 50:  # Initial range formation
            if i % 20 < 10:  # Move towards high
                target = range_high
            else:  # Move towards low
                target = range_low
        else:  # Range maintenance with occasional touches
            if i % 30 < 5:  # Touch high
                target = range_high - 0.1
            elif i % 30 < 10:  # Touch low
                target = range_low + 0.1
            else:  # Stay around EQ
                target = eq_level + np.random.uniform(-0.5, 0.5)
        
        # Add some noise and gradual movement
        price_change = (target - current_price) * 0.1 + np.random.uniform(-0.2, 0.2)
        current_price = np.clip(current_price + price_change, range_low - 0.5, range_high + 0.5)
        
        # Create OHLC from current price
        volatility = 0.3
        high = current_price + np.random.uniform(0, volatility)
        low = current_price - np.random.uniform(0, volatility)
        open_price = current_price + np.random.uniform(-volatility/2, volatility/2)
        close = current_price + np.random.uniform(-volatility/2, volatility/2)
        
        # Ensure OHLC relationships
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        # Volume - higher at range boundaries
        base_volume = 1000
        if abs(high - range_high) < 0.2 or abs(low - range_low) < 0.2:
            volume = base_volume * np.random.uniform(1.5, 3.0)  # Higher volume at boundaries
        else:
            volume = base_volume * np.random.uniform(0.8, 1.2)
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'timestamp': datetime.now() - timedelta(minutes=num_bars-i)
        })
    
    df = pd.DataFrame(data)
    return df

def create_mock_trending_data(start_price: float = 100.0, trend_direction: str = 'up', num_bars: int = 200) -> pd.DataFrame:
    """
    Create mock OHLCV data that shows trending behavior (should score low on range analysis).
    
    Args:
        start_price: Starting price level
        trend_direction: 'up' or 'down'
        num_bars: Number of bars to generate
        
    Returns:
        pd.DataFrame: Mock OHLCV data with trending pattern
    """
    np.random.seed(123)  # Different seed for different pattern
    
    data = []
    current_price = start_price
    trend_multiplier = 1 if trend_direction == 'up' else -1
    
    for i in range(num_bars):
        # Create trending price action
        trend_move = 0.1 * trend_multiplier + np.random.uniform(-0.05, 0.05)
        current_price += trend_move
        
        # Create OHLC from current price
        volatility = 0.4
        high = current_price + np.random.uniform(0, volatility)
        low = current_price - np.random.uniform(0, volatility)
        open_price = current_price + np.random.uniform(-volatility/2, volatility/2)
        close = current_price + np.random.uniform(-volatility/2, volatility/2)
        
        # Ensure OHLC relationships
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        # Volume - consistent
        volume = 1000 * np.random.uniform(0.8, 1.2)
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'timestamp': datetime.now() - timedelta(minutes=num_bars-i)
        })
    
    df = pd.DataFrame(data)
    return df

def create_mock_config() -> dict:
    """Create a mock configuration for testing."""
    return {
        'analysis': {
            'indicators': {
                'price_structure': {
                    'enabled': True
                }
            }
        },
        'confluence': {
            'weights': {
                'sub_components': {
                    'price_structure': {
                        'support_resistance': 0.1667,
                        'order_blocks': 0.1667,
                        'trend_position': 0.1667,
                        'volume_profile': 0.1667,
                        'market_structure': 0.1667,
                        'range_analysis': 0.1667
                    }
                }
            }
        }
    }

async def test_range_detection():
    """Test the range detection functionality."""
    logger.info("Testing range detection functionality...")
    
    # Create test data
    config = create_mock_config()
    indicator = PriceStructureIndicators(config, logger)
    
    # Test with range-bound data
    range_data = create_mock_range_data(start_price=100.0, range_size=5.0, num_bars=100)
    range_info = indicator._detect_range_structure(range_data)
    
    logger.info(f"Range detection results:")
    logger.info(f"  Has range: {range_info['has_range']}")
    if range_info['has_range']:
        logger.info(f"  Range high: {range_info['range_high']:.4f}")
        logger.info(f"  Range low: {range_info['range_low']:.4f}")
        logger.info(f"  EQ level: {range_info['eq_level']:.4f}")
        logger.info(f"  Range age: {range_info['range_age']}")
        logger.info(f"  Range strength: {range_info['range_strength']:.2f}")
        logger.info(f"  Touches high: {range_info['touches_high']}")
        logger.info(f"  Touches low: {range_info['touches_low']}")
        logger.info(f"  Recent deviations: {len(range_info['recent_deviations'])}")
    
    # Test with trending data
    trending_data = create_mock_trending_data(start_price=100.0, trend_direction='up', num_bars=100)
    trending_range_info = indicator._detect_range_structure(trending_data)
    
    logger.info(f"\nTrending data range detection:")
    logger.info(f"  Has range: {trending_range_info['has_range']}")
    
    return range_info['has_range'] and not trending_range_info['has_range']

async def test_range_scoring():
    """Test the range scoring logic."""
    logger.info("\nTesting range scoring logic...")
    
    config = create_mock_config()
    indicator = PriceStructureIndicators(config, logger)
    
    # Test with range-bound data
    range_data = create_mock_range_data(start_price=100.0, range_size=5.0, num_bars=100)
    range_info = indicator._detect_range_structure(range_data)
    range_score = indicator._score_range_conditions(range_data, range_info)
    
    logger.info(f"Range-bound data score: {range_score:.2f}")
    
    # Test with trending data
    trending_data = create_mock_trending_data(start_price=100.0, trend_direction='up', num_bars=100)
    trending_range_info = indicator._detect_range_structure(trending_data)
    trending_score = indicator._score_range_conditions(trending_data, trending_range_info)
    
    logger.info(f"Trending data score: {trending_score:.2f}")
    
    return range_score > trending_score

async def test_system_integration():
    """Test the full system integration."""
    logger.info("\nTesting system integration...")
    
    config = create_mock_config()
    indicator = PriceStructureIndicators(config, logger)
    
    # Create multi-timeframe data
    range_data = create_mock_range_data(start_price=100.0, range_size=5.0, num_bars=200)
    
    market_data = {
        'symbol': 'TESTUSDT',
        'ohlcv': {
            'base': range_data,
            'ltf': range_data.iloc[::2].reset_index(drop=True),  # Simulate 2x timeframe
            'mtf': range_data.iloc[::5].reset_index(drop=True),  # Simulate 5x timeframe
            'htf': range_data.iloc[::10].reset_index(drop=True)  # Simulate 10x timeframe
        }
    }
    
    # Test the full calculation
    results = await indicator.calculate(market_data)
    
    logger.info(f"System integration results:")
    logger.info(f"  Final score: {results['score']:.2f}")
    logger.info(f"  Range score component: {results['components'].get('range_score', 'N/A')}")
    logger.info(f"  Interpretation: {results['interpretation']}")
    
    # Test signals
    signals = await indicator.get_signals(market_data)
    range_signal = signals.get('range_analysis', {})
    
    logger.info(f"  Range signal: {range_signal.get('signal', 'N/A')}")
    logger.info(f"  Range bias: {range_signal.get('bias', 'N/A')}")
    logger.info(f"  Range strength: {range_signal.get('strength', 'N/A')}")
    
    return 'range_score' in results['components'] and 'range_analysis' in signals

async def test_component_weights():
    """Test that component weights are properly handled."""
    logger.info("\nTesting component weights...")
    
    config = create_mock_config()
    indicator = PriceStructureIndicators(config, logger)
    
    # Check weights
    logger.info(f"Component weights:")
    for component, weight in indicator.component_weights.items():
        logger.info(f"  {component}: {weight:.4f}")
    
    # Verify weights sum to 1.0
    total_weight = sum(indicator.component_weights.values())
    logger.info(f"Total weight: {total_weight:.4f}")
    
    # Check that range_score is included
    has_range_score = 'range_score' in indicator.component_weights
    logger.info(f"Range score included: {has_range_score}")
    
    return abs(total_weight - 1.0) < 0.001 and has_range_score

async def test_volume_enhancement():
    """Test volume enhancement functionality."""
    logger.info("\nTesting volume enhancement...")
    
    config = create_mock_config()
    indicator = PriceStructureIndicators(config, logger)
    
    # Create range data with volume spikes at boundaries
    range_data = create_mock_range_data(start_price=100.0, range_size=5.0, num_bars=100)
    range_info = indicator._detect_range_structure(range_data)
    
    if range_info['has_range']:
        volume_multiplier = indicator._enhance_range_score_with_volume(range_data, range_info)
        logger.info(f"Volume enhancement multiplier: {volume_multiplier:.3f}")
        
        return 0.8 <= volume_multiplier <= 1.2
    else:
        logger.warning("No range detected for volume enhancement test")
        return False

async def test_eq_interactions():
    """Test equilibrium interaction detection."""
    logger.info("\nTesting EQ interactions...")
    
    config = create_mock_config()
    indicator = PriceStructureIndicators(config, logger)
    
    # Create range data
    range_data = create_mock_range_data(start_price=100.0, range_size=5.0, num_bars=100)
    range_info = indicator._detect_range_structure(range_data)
    
    if range_info['has_range']:
        eq_level = range_info['eq_level']
        eq_interactions = indicator._detect_eq_interactions(range_data, eq_level)
        
        logger.info(f"EQ interactions:")
        logger.info(f"  Total interactions: {eq_interactions['total_interactions']}")
        logger.info(f"  Bullish reactions: {eq_interactions['bullish_reactions']}")
        logger.info(f"  Bearish reactions: {eq_interactions['bearish_reactions']}")
        
        return eq_interactions['total_interactions'] > 0
    else:
        logger.warning("No range detected for EQ interaction test")
        return False

async def run_all_tests():
    """Run all tests and report results."""
    logger.info("=" * 60)
    logger.info("RANGE SCORE INTEGRATION TEST SUITE")
    logger.info("=" * 60)
    
    tests = [
        ("Range Detection", test_range_detection),
        ("Range Scoring", test_range_scoring),
        ("System Integration", test_system_integration),
        ("Component Weights", test_component_weights),
        ("Volume Enhancement", test_volume_enhancement),
        ("EQ Interactions", test_eq_interactions),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
            status = "PASS" if result else "FAIL"
            logger.info(f"{test_name}: {status}")
        except Exception as e:
            results[test_name] = False
            logger.error(f"{test_name}: ERROR - {str(e)}")
    
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! Range score integration is working correctly.")
    else:
        logger.warning(f"⚠️  {total - passed} tests failed. Review implementation.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(run_all_tests()) 