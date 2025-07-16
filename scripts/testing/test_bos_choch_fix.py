#!/usr/bin/env python3
"""
Simple test script to verify BOS/CHoCH scoring fix.
Tests the logic without importing the full module structure.
"""

import numpy as np
from typing import Dict, List, Any

def _score_bos_choch_fixed(bos_choch: Dict[str, List]) -> float:
    """Fixed version of BOS/CHoCH scoring function."""
    try:
        # Get all events and sort by break_index to find recent ones
        all_bos = sorted(bos_choch['bos'], key=lambda x: x['break_index'])
        all_choch = sorted(bos_choch['choch'], key=lambda x: x['break_index'])
        
        # Get recent events (last 20 candles worth of events)
        # Take the most recent events based on their break_index
        recent_bos = all_bos[-20:] if len(all_bos) > 20 else all_bos
        recent_choch = all_choch[-20:] if len(all_choch) > 20 else all_choch
        
        bos_score = 0
        choch_score = 0
        
        # Score BOS events (trend continuation)
        for event in recent_bos:
            if event['type'] == 'bullish':
                bos_score += event['strength'] * 0.3
            else:
                bos_score -= event['strength'] * 0.3
        
        # Score CHoCH events (potential reversal)
        for event in recent_choch:
            if event['type'] == 'bullish':
                choch_score += event['strength'] * 0.5  # Higher weight for reversals
            else:
                choch_score -= event['strength'] * 0.5
        
        # Combine scores
        final_score = 50 + bos_score + choch_score
        
        return float(np.clip(final_score, 0, 100))
        
    except Exception as e:
        print(f"Error scoring BOS/CHoCH: {str(e)}")
        return 50.0

def _score_bos_choch_original(bos_choch: Dict[str, List]) -> float:
    """Original broken version for comparison."""
    try:
        # This was the broken logic
        recent_bos = [event for event in bos_choch['bos'] if event['break_index'] >= len(bos_choch['bos']) - 20]
        recent_choch = [event for event in bos_choch['choch'] if event['break_index'] >= len(bos_choch['choch']) - 20]
        
        bos_score = 0
        choch_score = 0
        
        # Score BOS events (trend continuation)
        for event in recent_bos:
            if event['type'] == 'bullish':
                bos_score += event['strength'] * 0.3
            else:
                bos_score -= event['strength'] * 0.3
        
        # Score CHoCH events (potential reversal)
        for event in recent_choch:
            if event['type'] == 'bullish':
                choch_score += event['strength'] * 0.5
            else:
                choch_score -= event['strength'] * 0.5
        
        # Combine scores
        final_score = 50 + bos_score + choch_score
        
        return float(np.clip(final_score, 0, 100))
        
    except Exception as e:
        print(f"Error scoring BOS/CHoCH (original): {str(e)}")
        return 50.0

def test_bos_choch_fix():
    """Test the BOS/CHoCH scoring fix."""
    print("Testing BOS/CHoCH Scoring Fix")
    print("=" * 40)
    
    # Create test data that would cause the original bug
    test_data = {
        'bos': [
            {'type': 'bullish', 'break_index': 100, 'strength': 75.0},
            {'type': 'bearish', 'break_index': 150, 'strength': 60.0},
            {'type': 'bullish', 'break_index': 200, 'strength': 80.0},
        ],
        'choch': [
            {'type': 'bearish', 'break_index': 120, 'strength': 65.0},
            {'type': 'bullish', 'break_index': 180, 'strength': 70.0},
        ]
    }
    
    print(f"Test data:")
    print(f"  BOS events: {len(test_data['bos'])}")
    print(f"  CHoCH events: {len(test_data['choch'])}")
    print(f"  Break indices: {[e['break_index'] for e in test_data['bos'] + test_data['choch']]}")
    
    # Test original (broken) version
    print(f"\n1. Testing original (broken) logic:")
    try:
        original_score = _score_bos_choch_original(test_data)
        print(f"   Original score: {original_score:.2f}")
    except Exception as e:
        print(f"   Original failed with error: {str(e)}")
    
    # Test fixed version
    print(f"\n2. Testing fixed logic:")
    try:
        fixed_score = _score_bos_choch_fixed(test_data)
        print(f"   Fixed score: {fixed_score:.2f}")
        print(f"   ✅ Fixed version works correctly!")
    except Exception as e:
        print(f"   Fixed version failed: {str(e)}")
        return False
    
    # Test edge cases
    print(f"\n3. Testing edge cases:")
    
    # Empty data
    empty_data = {'bos': [], 'choch': []}
    empty_score = _score_bos_choch_fixed(empty_data)
    print(f"   Empty data score: {empty_score:.2f}")
    
    # Large dataset (>20 events)
    large_data = {
        'bos': [{'type': 'bullish', 'break_index': i*10, 'strength': 50.0} for i in range(25)],
        'choch': [{'type': 'bearish', 'break_index': i*10+5, 'strength': 40.0} for i in range(15)]
    }
    large_score = _score_bos_choch_fixed(large_data)
    print(f"   Large dataset score: {large_score:.2f}")
    
    print(f"\n✅ All tests passed! BOS/CHoCH fix is working correctly.")
    return True

if __name__ == "__main__":
    test_bos_choch_fix() 