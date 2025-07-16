#!/usr/bin/env python3

import sys
import os
import yaml

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.price_structure_indicators import PriceStructureIndicators

def test_config_weights():
    """Test that configuration weights are properly loaded after migration."""
    
    print("🧪 CONFIGURATION WEIGHTS VERIFICATION TEST")
    print("=" * 80)
    
    # Load config
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print("📋 Expected weights from config.yaml:")
    
    # Expected volume weights from config
    expected_volume_weights = config['confluence']['weights']['sub_components']['volume']
    print("\n🔵 Volume Components:")
    for component, weight in expected_volume_weights.items():
        print(f"   {component}: {weight}")
    
    # Expected price structure weights from config
    expected_price_weights = config['confluence']['weights']['sub_components']['price_structure']
    print("\n🟠 Price Structure Components:")
    for component, weight in expected_price_weights.items():
        print(f"   {component}: {weight}")
    
    print("\n" + "=" * 80)
    print("🔍 TESTING ACTUAL INDICATOR WEIGHTS")
    print("=" * 80)
    
    # Test Volume Indicators
    print("\n🔵 Testing Volume Indicators...")
    volume_indicator = VolumeIndicators(config)
    
    print("   Actual weights loaded:")
    volume_total = 0
    for component, weight in volume_indicator.component_weights.items():
        expected = expected_volume_weights.get(component, 0)
        status = "✅" if abs(weight - expected) < 0.001 else "❌"
        print(f"   {status} {component}: {weight:.3f} (expected: {expected:.3f})")
        volume_total += weight
    
    print(f"   📊 Total weight: {volume_total:.3f} (should be 1.000)")
    volume_pass = abs(volume_total - 1.0) < 0.001
    print(f"   🎯 Volume weights normalized: {'✅ PASS' if volume_pass else '❌ FAIL'}")
    
    # Test Price Structure Indicators
    print("\n🟠 Testing Price Structure Indicators...")
    price_indicator = PriceStructureIndicators(config)
    
    print("   Actual weights loaded:")
    price_total = 0
    for component, weight in price_indicator.component_weights.items():
        expected = expected_price_weights.get(component, 0)
        status = "✅" if abs(weight - expected) < 0.001 else "❌"
        print(f"   {status} {component}: {weight:.3f} (expected: {expected:.3f})")
        price_total += weight
    
    print(f"   📊 Total weight: {price_total:.3f} (should be 1.000)")
    price_pass = abs(price_total - 1.0) < 0.001
    print(f"   🎯 Price weights normalized: {'✅ PASS' if price_pass else '❌ FAIL'}")
    
    # Verify migration
    print("\n" + "=" * 80)
    print("🔍 MIGRATION VERIFICATION")
    print("=" * 80)
    
    # Check that volume_profile and vwap are in volume indicators
    volume_has_vp = 'volume_profile' in volume_indicator.component_weights
    volume_has_vwap = 'vwap' in volume_indicator.component_weights
    
    # Check that volume_profile and vwap are NOT in price structure indicators
    price_missing_vp = 'volume_profile' not in price_indicator.component_weights
    price_missing_vwap = 'vwap' not in price_indicator.component_weights
    
    print(f"   {'✅' if volume_has_vp else '❌'} volume_profile in Volume Indicators: {volume_has_vp}")
    print(f"   {'✅' if volume_has_vwap else '❌'} vwap in Volume Indicators: {volume_has_vwap}")
    print(f"   {'✅' if price_missing_vp else '❌'} volume_profile NOT in Price Structure: {price_missing_vp}")
    print(f"   {'✅' if price_missing_vwap else '❌'} vwap NOT in Price Structure: {price_missing_vwap}")
    
    migration_success = volume_has_vp and volume_has_vwap and price_missing_vp and price_missing_vwap
    
    print("\n" + "=" * 80)
    print("🎯 FINAL RESULTS")
    print("=" * 80)
    
    overall_pass = volume_pass and price_pass and migration_success
    
    print(f"   Volume Indicators:     {'✅ PASS' if volume_pass else '❌ FAIL'}")
    print(f"   Price Structure:       {'✅ PASS' if price_pass else '❌ FAIL'}")
    print(f"   Migration Verification: {'✅ PASS' if migration_success else '❌ FAIL'}")
    print(f"   OVERALL:               {'✅ SUCCESS' if overall_pass else '❌ FAILURE'}")
    
    if overall_pass:
        print("\n🎉 All configuration weights are properly loaded and migration is successful!")
    else:
        print("\n❌ Configuration issues detected!")
    
    return overall_pass

if __name__ == "__main__":
    test_config_weights() 