#!/usr/bin/env python3
"""
Test script to verify the fix for price structure warning about default values.

This script tests the improved warning logic that should only warn when there are
systemic issues, not when individual components legitimately return neutral scores.
"""

import sys
import os
import logging
from typing import Dict, Any

# Add the src directory to the path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.core.logger import Logger

def setup_logging():
    """Setup logging to capture warnings."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def create_test_config():
    """Create a test configuration for price structure indicators."""
    return {
        'timeframes': {
            'base': {
                'interval': 1,
                'weight': 0.4,
                'validation': {'min_candles': 50}
            },
            'ltf': {
                'interval': 5,
                'weight': 0.3,
                'validation': {'min_candles': 50}
            },
            'mtf': {
                'interval': 30,
                'weight': 0.2,
                'validation': {'min_candles': 50}
            },
            'htf': {
                'interval': 240,
                'weight': 0.1,
                'validation': {'min_candles': 50}
            }
        },
        'analysis': {
            'indicators': {
                'price_structure': {
                    'parameters': {}
                }
            }
        }
    }

def test_warning_scenarios():
    """Test different scenarios for the warning logic."""
    print("=== Testing Price Structure Warning Logic ===\n")
    
    config = create_test_config()
    indicator = PriceStructureIndicators(config)
    
    # Test Case 1: Normal case with mixed scores (should not warn)
    print("Test Case 1: Mixed scores (should only debug log)")
    scores_mixed = {
        'support_resistance': 75.5,
        'order_block': 50.0,  # Neutral
        'trend_position': 82.3,
        'swing_structure': 50.0,  # Neutral
        'composite_value': 45.2,
        'fair_value_gaps': 68.9,
        'bos_choch': 50.0,  # Neutral
        'range_score': 55.1
    }
    
    result1 = indicator._compute_weighted_score(scores_mixed)
    print(f"Result: {result1:.2f}")
    print()
    
    # Test Case 2: Mostly neutral scores (should warn about systemic issue)
    print("Test Case 2: 6/8 components neutral (should warn about systemic issue)")
    scores_mostly_neutral = {
        'support_resistance': 50.0,
        'order_block': 50.0,
        'trend_position': 50.0,
        'swing_structure': 50.0,
        'composite_value': 50.0,
        'fair_value_gaps': 50.0,
        'bos_choch': 65.2,  # Non-neutral
        'range_score': 72.8   # Non-neutral
    }
    
    result2 = indicator._compute_weighted_score(scores_mostly_neutral)
    print(f"Result: {result2:.2f}")
    print()
    
    # Test Case 3: All neutral scores (should warn about calculation failure)
    print("Test Case 3: All components neutral (should warn about calculation failure)")
    scores_all_neutral = {
        'support_resistance': 50.0,
        'order_block': 50.0,
        'trend_position': 50.0,
        'swing_structure': 50.0,
        'composite_value': 50.0,
        'fair_value_gaps': 50.0,
        'bos_choch': 50.0,
        'range_score': 50.0
    }
    
    result3 = indicator._compute_weighted_score(scores_all_neutral)
    print(f"Result: {result3:.2f}")
    print()
    
    # Test Case 4: Few neutral scores (should not warn)
    print("Test Case 4: Only 2/8 components neutral (should not warn)")
    scores_few_neutral = {
        'support_resistance': 78.5,
        'order_block': 50.0,  # Neutral
        'trend_position': 85.3,
        'swing_structure': 62.7,
        'composite_value': 58.2,
        'fair_value_gaps': 71.9,
        'bos_choch': 50.0,  # Neutral
        'range_score': 66.1
    }
    
    result4 = indicator._compute_weighted_score(scores_few_neutral)
    print(f"Result: {result4:.2f}")
    print()
    
    print("=== Test Summary ===")
    print("✓ Test Case 1: Mixed scores - Should only show debug log")
    print("⚠ Test Case 2: 75%+ neutral - Should warn about systemic issue")
    print("⚠ Test Case 3: All neutral - Should warn about calculation failure")
    print("✓ Test Case 4: Few neutral - Should not warn")
    print("\nThe fix should significantly reduce warning noise while still catching genuine issues.")

if __name__ == "__main__":
    setup_logging()
    test_warning_scenarios() 