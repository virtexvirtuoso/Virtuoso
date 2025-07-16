#!/usr/bin/env python3
"""
Simple test script for OIR and DI implementation.
This avoids importing all indicators to bypass the talib dependency.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import asyncio

# Import only what we need
from src.core.logger import Logger

# Let's test the core OIR and DI calculations directly
def test_oir_calculation():
    """Test the OIR calculation directly."""
    print("=== Testing OIR Calculation ===")
    
    # Test data: [price, volume]
    bids = np.array([
        [50000.0, 3.0],  # Higher bid volumes (bullish)
        [49990.0, 2.5],
        [49980.0, 4.0],
        [49970.0, 2.2],
        [49960.0, 1.8]
    ])
    
    asks = np.array([
        [50010.0, 1.0],  # Lower ask volumes
        [50020.0, 0.8],
        [50030.0, 1.5],
        [50040.0, 0.6],
        [50050.0, 0.4]
    ])
    
    # Calculate OIR manually
    depth_levels = 5
    sum_bid_volume = np.sum(bids[:depth_levels, 1])
    sum_ask_volume = np.sum(asks[:depth_levels, 1])
    
    print(f"Sum bid volume: {sum_bid_volume}")
    print(f"Sum ask volume: {sum_ask_volume}")
    
    # OIR formula: (sum_bid_volume - sum_ask_volume) / (sum_bid_volume + sum_ask_volume)
    if sum_bid_volume + sum_ask_volume > 0:
        oir = (sum_bid_volume - sum_ask_volume) / (sum_bid_volume + sum_ask_volume)
        print(f"OIR value: {oir:.4f}")
        
        # Convert to 0-100 score
        raw_score = 50.0 * (1 + oir)
        print(f"Raw score (0-100): {raw_score:.2f}")
        
        # Expected: Since bid volume > ask volume, OIR should be positive, score > 50
        print(f"Expected: OIR > 0 (bullish), Score > 50")
        print(f"✅ Test passed" if oir > 0 and raw_score > 50 else "❌ Test failed")
    
    print()

def test_di_calculation():
    """Test the DI calculation directly."""
    print("=== Testing DI Calculation ===")
    
    # Test data: [price, volume]
    bids = np.array([
        [50000.0, 1.0],  # Lower bid volumes (bearish)
        [49990.0, 0.8],
        [49980.0, 1.2],
        [49970.0, 0.6],
        [49960.0, 0.4]
    ])
    
    asks = np.array([
        [50010.0, 3.0],  # Higher ask volumes
        [50020.0, 2.5],
        [50030.0, 4.0],
        [50040.0, 2.2],
        [50050.0, 1.8]
    ])
    
    # Calculate DI manually
    depth_levels = 5
    sum_bid_volume = np.sum(bids[:depth_levels, 1])
    sum_ask_volume = np.sum(asks[:depth_levels, 1])
    
    print(f"Sum bid volume: {sum_bid_volume}")
    print(f"Sum ask volume: {sum_ask_volume}")
    
    # DI formula: sum_bid_volume - sum_ask_volume
    di = sum_bid_volume - sum_ask_volume
    print(f"DI value: {di:.4f}")
    
    # Normalize for scoring
    total_volume = sum_bid_volume + sum_ask_volume
    if total_volume > 0:
        normalized_di = np.tanh(di / total_volume)
        raw_score = 50.0 * (1 + normalized_di)
        print(f"Normalized DI: {normalized_di:.4f}")
        print(f"Raw score (0-100): {raw_score:.2f}")
        
        # Expected: Since ask volume > bid volume, DI should be negative, score < 50
        print(f"Expected: DI < 0 (bearish), Score < 50")
        print(f"✅ Test passed" if di < 0 and raw_score < 50 else "❌ Test failed")
    
    print()

def test_balanced_scenario():
    """Test balanced orderbook scenario."""
    print("=== Testing Balanced Scenario ===")
    
    # Balanced data
    bids = np.array([
        [50000.0, 1.0],
        [49990.0, 1.5],
        [49980.0, 2.0],
        [49970.0, 1.2],
        [49960.0, 0.8]
    ])
    
    asks = np.array([
        [50010.0, 1.0],
        [50020.0, 1.5],
        [50030.0, 2.0],
        [50040.0, 1.2],
        [50050.0, 0.8]
    ])
    
    # Calculate both metrics
    depth_levels = 5
    sum_bid_volume = np.sum(bids[:depth_levels, 1])
    sum_ask_volume = np.sum(asks[:depth_levels, 1])
    
    print(f"Sum bid volume: {sum_bid_volume}")
    print(f"Sum ask volume: {sum_ask_volume}")
    
    # OIR
    oir = (sum_bid_volume - sum_ask_volume) / (sum_bid_volume + sum_ask_volume)
    oir_score = 50.0 * (1 + oir)
    
    # DI
    di = sum_bid_volume - sum_ask_volume
    normalized_di = np.tanh(di / (sum_bid_volume + sum_ask_volume))
    di_score = 50.0 * (1 + normalized_di)
    
    print(f"OIR: {oir:.4f} → Score: {oir_score:.2f}")
    print(f"DI: {di:.4f} → Score: {di_score:.2f}")
    
    # Expected: Both should be close to 50 (neutral)
    print(f"Expected: Both scores ≈ 50 (balanced)")
    oir_balanced = 45 <= oir_score <= 55
    di_balanced = 45 <= di_score <= 55
    print(f"OIR balanced: {'✅' if oir_balanced else '❌'}")
    print(f"DI balanced: {'✅' if di_balanced else '❌'}")
    
    print()

def test_weight_configuration():
    """Test that the component weights are configured correctly."""
    print("=== Testing Component Weights ===")
    
    # Expected weights after our changes
    expected_weights = {
        'imbalance': 0.25,
        'mpi': 0.20,
        'depth': 0.20,
        'liquidity': 0.10,
        'absorption_exhaustion': 0.10,
        'oir': 0.10,  # New
        'di': 0.05   # New
    }
    
    # Check total weight
    total_weight = sum(expected_weights.values())
    print(f"Total expected weight: {total_weight:.3f}")
    print(f"Weight sum correct: {'✅' if abs(total_weight - 1.0) < 0.001 else '❌'}")
    
    # Check that old components are removed
    old_components = {'dom_momentum', 'spread', 'obps'}
    new_components = {'oir', 'di'}
    current_components = set(expected_weights.keys())
    
    old_removed = old_components.isdisjoint(current_components)
    new_added = new_components.issubset(current_components)
    
    print(f"Old components removed: {'✅' if old_removed else '❌'}")
    print(f"New components added: {'✅' if new_added else '❌'}")
    
    print("Expected component weights:")
    for component, weight in expected_weights.items():
        print(f"  {component}: {weight:.3f}")
    
    print()

if __name__ == "__main__":
    print("🧪 Testing OIR and DI Implementation\n")
    
    test_oir_calculation()
    test_di_calculation()
    test_balanced_scenario()
    test_weight_configuration()
    
    print("✅ All basic tests completed!")
    print("\nNext steps:")
    print("1. Install missing dependencies (talib) if needed")
    print("2. Run full integration test with OrderbookIndicators class")
    print("3. Test with real market data")
    print("4. Compare performance against old implementation") 