#!/usr/bin/env python3
"""
Test script for OIR and DI implementation in OrderbookIndicators.

This script tests the new Order Imbalance Ratio (OIR) and Depth Imbalance (DI) 
metrics that were added based on the academic paper by Josef Smutný.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import asyncio
from src.indicators.orderbook_indicators import OrderbookIndicators
from src.core.logger import Logger

def create_test_config():
    """Create a test configuration for the OrderbookIndicators."""
    return {
        'timeframes': {
            'base': {'interval': '1', 'weight': 0.4, 'validation': {'min_candles': 50}},
            'ltf': {'interval': '5', 'weight': 0.3, 'validation': {'min_candles': 50}},
            'mtf': {'interval': '30', 'weight': 0.2, 'validation': {'min_candles': 50}},
            'htf': {'interval': '240', 'weight': 0.1, 'validation': {'min_candles': 50}}
        },
        'orderbook': {
            'depth_levels': 10,
            'imbalance_threshold': 1.5,
            'liquidity_threshold': 1.5,
            'spread_factor': 2.0,
            'max_spread_bps': 50,
            'min_price_impact': 0.05,
            'parameters': {
                'sigmoid_transformation': {
                    'default_sensitivity': 0.12,
                    'imbalance_sensitivity': 0.15,
                    'pressure_sensitivity': 0.18
                }
            }
        }
    }

def create_test_orderbook_data():
    """Create test orderbook data with different scenarios."""
    
    # Scenario 1: Balanced orderbook (should give ~50 scores)
    balanced_data = {
        'symbol': 'BTCUSDT',
        'orderbook': {
            'bids': [
                [50000.0, 1.0],
                [49990.0, 1.5],
                [49980.0, 2.0],
                [49970.0, 1.2],
                [49960.0, 0.8],
                [49950.0, 1.1],
                [49940.0, 1.3],
                [49930.0, 0.9],
                [49920.0, 1.4],
                [49910.0, 1.0]
            ],
            'asks': [
                [50010.0, 1.0],
                [50020.0, 1.5],
                [50030.0, 2.0],
                [50040.0, 1.2],
                [50050.0, 0.8],
                [50060.0, 1.1],
                [50070.0, 1.3],
                [50080.0, 0.9],
                [50090.0, 1.4],
                [50100.0, 1.0]
            ]
        }
    }
    
    # Scenario 2: Bullish orderbook (more bid volume - should give >50 scores)
    bullish_data = {
        'symbol': 'BTCUSDT',
        'orderbook': {
            'bids': [
                [50000.0, 3.0],  # Much higher bid volumes
                [49990.0, 2.5],
                [49980.0, 4.0],
                [49970.0, 2.2],
                [49960.0, 1.8],
                [49950.0, 2.1],
                [49940.0, 2.3],
                [49930.0, 1.9],
                [49920.0, 2.4],
                [49910.0, 2.0]
            ],
            'asks': [
                [50010.0, 0.5],  # Much lower ask volumes
                [50020.0, 0.8],
                [50030.0, 1.0],
                [50040.0, 0.6],
                [50050.0, 0.4],
                [50060.0, 0.7],
                [50070.0, 0.9],
                [50080.0, 0.3],
                [50090.0, 0.8],
                [50100.0, 0.5]
            ]
        }
    }
    
    # Scenario 3: Bearish orderbook (more ask volume - should give <50 scores)
    bearish_data = {
        'symbol': 'BTCUSDT',
        'orderbook': {
            'bids': [
                [50000.0, 0.5],  # Much lower bid volumes
                [49990.0, 0.8],
                [49980.0, 1.0],
                [49970.0, 0.6],
                [49960.0, 0.4],
                [49950.0, 0.7],
                [49940.0, 0.9],
                [49930.0, 0.3],
                [49920.0, 0.8],
                [49910.0, 0.5]
            ],
            'asks': [
                [50010.0, 3.0],  # Much higher ask volumes
                [50020.0, 2.5],
                [50030.0, 4.0],
                [50040.0, 2.2],
                [50050.0, 1.8],
                [50060.0, 2.1],
                [50070.0, 2.3],
                [50080.0, 1.9],
                [50090.0, 2.4],
                [50100.0, 2.0]
            ]
        }
    }
    
    return {
        'balanced': balanced_data,
        'bullish': bullish_data,
        'bearish': bearish_data
    }

async def test_oir_di_implementation():
    """Test the OIR and DI implementation."""
    
    print("=== Testing OIR and DI Implementation ===\n")
    
    # Create test configuration
    config = create_test_config()
    
    # Initialize OrderbookIndicators
    logger = Logger(__name__)
    indicator = OrderbookIndicators(config, logger.logger)
    
    # Create test data
    test_data = create_test_orderbook_data()
    
    # Test each scenario
    for scenario_name, market_data in test_data.items():
        print(f"--- Testing {scenario_name.upper()} Scenario ---")
        
        try:
            # Calculate orderbook indicators
            result = await indicator.calculate(market_data)
            
            # Extract key metrics
            overall_score = result['score']
            components = result['components']
            
            print(f"Overall Score: {overall_score:.2f}")
            print("Component Scores:")
            for component, score in components.items():
                weight = indicator.component_weights.get(component, 0)
                print(f"  {component}: {score:.2f} (weight: {weight:.2f})")
            
            # Focus on our new metrics
            if 'oir' in components and 'di' in components:
                print(f"\n🎯 NEW ACADEMIC METRICS:")
                print(f"  OIR (Order Imbalance Ratio): {components['oir']:.2f}")
                print(f"  DI (Depth Imbalance): {components['di']:.2f}")
                
                # Verify expected behavior
                if scenario_name == 'balanced':
                    expected_range = (45, 55)
                elif scenario_name == 'bullish':
                    expected_range = (55, 100)
                elif scenario_name == 'bearish':
                    expected_range = (0, 45)
                
                oir_in_range = expected_range[0] <= components['oir'] <= expected_range[1]
                di_in_range = expected_range[0] <= components['di'] <= expected_range[1]
                
                print(f"  OIR in expected range {expected_range}: {'✅' if oir_in_range else '❌'}")
                print(f"  DI in expected range {expected_range}: {'✅' if di_in_range else '❌'}")
            
            print(f"  Interpretation: {result.get('interpretation', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Error in {scenario_name} scenario: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("-" * 50)
    
    print("\n=== Component Weight Verification ===")
    print("Current component weights:")
    total_weight = 0
    for component, weight in indicator.component_weights.items():
        print(f"  {component}: {weight:.3f}")
        total_weight += weight
    print(f"Total weight: {total_weight:.3f} (should be 1.000)")
    
    # Verify we removed old components and added new ones
    old_components = {'dom_momentum', 'spread', 'obps'}
    new_components = {'oir', 'di'}
    
    current_components = set(indicator.component_weights.keys())
    
    print(f"\nOld components removed: {old_components.isdisjoint(current_components)}")
    print(f"New components added: {new_components.issubset(current_components)}")
    
    if old_components.isdisjoint(current_components) and new_components.issubset(current_components):
        print("✅ Component replacement successful!")
    else:
        print("❌ Component replacement incomplete!")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_oir_di_implementation()) 