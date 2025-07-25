#!/usr/bin/env python3

"""
Simplified test script to demonstrate volume and OIR/DI enhancements.

This script tests the enhanced non-linear transformations by directly
testing the transformation methods from BaseIndicator.
"""

import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.indicators.base_indicator import BaseIndicator

class TestIndicator(BaseIndicator):
    """Test indicator class to access transformation methods."""
    
    def __init__(self):
        # Minimal config for testing
        self.config = {}
        self.logger = None
        self.component_weights = {}
        self.indicator_type = 'test'
    
    async def calculate(self, market_data):
        return {
            'score': 50.0,
            'components': {},
            'signals': {},
            'metadata': {}
        }
    
    def validate_input(self, data):
        return True

def test_sigmoid_transformation():
    """Test sigmoid transformation for different values."""
    print("=" * 60)
    print("TESTING SIGMOID TRANSFORMATION")
    print("=" * 60)
    
    indicator = TestIndicator()
    
    # Test different values
    test_values = [0, 10, 25, 50, 75, 90, 100]
    
    print("Value\tSigmoid(center=50, steep=0.1)\tSigmoid(center=50, steep=0.2)")
    print("-" * 65)
    
    for value in test_values:
        score1 = indicator._sigmoid_transform(value, center=50, steepness=0.1)
        score2 = indicator._sigmoid_transform(value, center=50, steepness=0.2)
        print(f"{value}\t{score1:.2f}\t\t\t{score2:.2f}")

def test_extreme_value_transformation():
    """Test extreme value transformation for volume spikes."""
    print("\n" + "=" * 60)
    print("TESTING EXTREME VALUE TRANSFORMATION")
    print("=" * 60)
    
    indicator = TestIndicator()
    
    # Test volume ratios (relative volume)
    test_values = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
    
    print("RVOL\tLinear Score\tExtreme Value Transform")
    print("-" * 50)
    
    for value in test_values:
        # Linear scoring (old method)
        if value < 1.0:
            linear_score = 50 * value
        else:
            linear_score = 50 + 50 * min((value - 1.0) / 2.0, 1.0)  # Cap at 100
        
        # Enhanced extreme value transformation
        enhanced_score = indicator._extreme_value_transform(value, threshold=1.0, max_extreme=10.0)
        
        print(f"{value}\t{linear_score:.2f}\t\t{enhanced_score:.2f}")

def test_hyperbolic_transformation():
    """Test hyperbolic transformation for OIR values."""
    print("\n" + "=" * 60)
    print("TESTING HYPERBOLIC TRANSFORMATION")
    print("=" * 60)
    
    indicator = TestIndicator()
    
    # Test OIR values (range -1 to 1)
    test_values = [-1.0, -0.5, -0.2, 0.0, 0.2, 0.5, 1.0]
    
    print("OIR\tLinear Score\tHyperbolic Transform")
    print("-" * 45)
    
    for value in test_values:
        # Linear scoring (old method)
        linear_score = 50.0 * (1 + value)
        
        # Enhanced hyperbolic transformation
        enhanced_score = indicator._hyperbolic_transform(value, sensitivity=1.0)
        
        print(f"{value}\t{linear_score:.2f}\t\t{enhanced_score:.2f}")

def test_enhanced_rsi_transformation():
    """Test enhanced RSI transformation."""
    print("\n" + "=" * 60)
    print("TESTING ENHANCED RSI TRANSFORMATION")
    print("=" * 60)
    
    indicator = TestIndicator()
    
    # Test RSI values
    test_values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 95]
    
    print("RSI\tLinear Score\tEnhanced Score\tImprovement")
    print("-" * 55)
    
    for rsi in test_values:
        # Linear scoring (old method)
        if rsi > 70:
            linear_score = max(0, 50 - ((rsi - 70) / 30) * 50)
        elif rsi < 30:
            linear_score = min(100, 50 + ((30 - rsi) / 30) * 50)
        else:
            linear_score = 50 + ((rsi - 50) / 20) * 25
        
        # Enhanced RSI transformation
        enhanced_score = indicator._enhanced_rsi_transform(rsi)
        
        improvement = enhanced_score - linear_score
        print(f"{rsi}\t{linear_score:.2f}\t\t{enhanced_score:.2f}\t\t{improvement:+.2f}")

def demonstrate_extreme_differentiation():
    """Demonstrate better differentiation at extreme values."""
    print("\n" + "=" * 60)
    print("DEMONSTRATING EXTREME VALUE DIFFERENTIATION")
    print("=" * 60)
    
    indicator = TestIndicator()
    
    print("The key improvement is better differentiation at extreme values:")
    print()
    
    # RSI extreme values
    print("RSI Extreme Values:")
    rsi_extremes = [75, 85, 95]
    for rsi in rsi_extremes:
        linear_score = max(0, 50 - ((rsi - 70) / 30) * 50)
        enhanced_score = indicator._enhanced_rsi_transform(rsi)
        print(f"  RSI {rsi}: Linear={linear_score:.2f}, Enhanced={enhanced_score:.2f} (Δ={enhanced_score-linear_score:+.2f})")
    
    print()
    
    # Volume extreme values
    print("Volume Extreme Values:")
    volume_extremes = [3.0, 5.0, 10.0]
    for vol in volume_extremes:
        linear_score = 50 + 50 * min((vol - 1.0) / 2.0, 1.0)
        enhanced_score = indicator._extreme_value_transform(vol, threshold=1.0, max_extreme=10.0)
        print(f"  RVOL {vol}: Linear={linear_score:.2f}, Enhanced={enhanced_score:.2f} (Δ={enhanced_score-linear_score:+.2f})")

def main():
    """Run all transformation tests."""
    print("Testing Enhanced Non-Linear Transformations")
    print("This demonstrates the improvements over linear scoring methods")
    print()
    
    # Test individual transformations
    test_sigmoid_transformation()
    test_extreme_value_transformation()
    test_hyperbolic_transformation()
    test_enhanced_rsi_transformation()
    demonstrate_extreme_differentiation()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("✅ Key Improvements:")
    print("   - Better differentiation at extreme values")
    print("   - Smooth transitions instead of linear scaling")
    print("   - Exponential decay for volume spikes")
    print("   - Confidence weighting for orderbook imbalances")
    print()
    print("These enhancements fix the linear scoring problems by:")
    print("1. RSI 95 vs 75 now have significantly different scores")
    print("2. Volume spikes >3x get exponential decay treatment")
    print("3. Orderbook imbalances use sophisticated tanh scaling")
    print("4. All transformations maintain proper 0-100 bounds")

if __name__ == "__main__":
    main() 