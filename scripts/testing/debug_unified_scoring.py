#!/usr/bin/env python3
"""
Debug script to test UnifiedScoringFramework directly.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.scoring import ScoringConfig, UnifiedScoringFramework, ScoringMode
from src.core.logger import Logger

# Set up logging
logger = Logger(__name__)

def test_volume_enhanced():
    """Test volume_enhanced transformation directly."""
    print("Testing UnifiedScoringFramework - Volume Enhanced")
    print("="*50)
    
    # Create configuration with caching disabled
    config = ScoringConfig(
        mode=ScoringMode.ENHANCED_LINEAR,  # Use the correct enum value
        sigmoid_steepness=0.1,
        tanh_sensitivity=1.0,
        market_regime_aware=True,
        confluence_enhanced=True,
        debug_mode=True,
        enable_caching=False,  # Disable caching
        log_transformations=True  # Enable transformation logging
    )
    
    # Create framework
    framework = UnifiedScoringFramework(config)
    
    # Test volume_enhanced method directly
    print("\nTesting volume_enhanced method directly:")
    test_values = [2.0]  # Just test one value for clarity
    
    for value in test_values:
        try:
            # Call the method directly
            direct_score = framework.enhanced_methods['volume_enhanced'](
                value,
                spike_threshold=3.0,
                normal_threshold=1.0,
                extreme_threshold=10.0
            )
            print(f"  Volume {value}: Direct call = {direct_score:.2f}")
        except Exception as e:
            print(f"  Volume {value}: Direct call ERROR - {e}")
    
    # Test _apply_enhanced_method directly
    print("\nTesting _apply_enhanced_method directly:")
    for value in test_values:
        try:
            score = framework._apply_enhanced_method(
                value, 
                'volume_enhanced',
                normal_threshold=1.0,
                spike_threshold=3.0,
                extreme_threshold=10.0
            )
            print(f"  Volume {value}: _apply_enhanced_method = {score:.2f}")
        except Exception as e:
            print(f"  Volume {value}: _apply_enhanced_method ERROR - {e}")
    
    # Test through transform_score with enhanced_linear mode (no cache)
    print("\nTesting through transform_score (ENHANCED_LINEAR mode, no cache):")
    for value in test_values:
        try:
            print(f"  About to call transform_score with value={value}, method='volume_enhanced'")
            print(f"  Config mode: {framework.config.mode}")
            print(f"  Config mode value: {framework.config.mode.value}")
            print(f"  Is sophisticated: {framework._is_sophisticated_method('volume_enhanced')}")
            
            score = framework.transform_score(
                value, 
                'volume_enhanced',
                normal_threshold=1.0,
                spike_threshold=3.0,
                extreme_threshold=10.0
            )
            print(f"  Volume {value}: transform_score = {score:.2f}")
        except Exception as e:
            print(f"  Volume {value}: transform_score ERROR - {e}")
            import traceback
            traceback.print_exc()
    
    # Test method detection
    print(f"\nMethod detection:")
    print(f"  volume_enhanced is sophisticated: {framework._is_sophisticated_method('volume_enhanced')}")
    print(f"  Config mode: {framework.config.mode}")
    print(f"  Config mode value: {framework.config.mode.value}")
    print(f"  Cache enabled: {framework.config.enable_caching}")
    print(f"  Available enhanced methods: {list(framework.enhanced_methods.keys())}")

if __name__ == "__main__":
    test_volume_enhanced() 