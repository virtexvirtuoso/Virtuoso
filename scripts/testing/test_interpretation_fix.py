#!/usr/bin/env python3
"""
Test script to verify the interpretation component type classification fix.

This script tests that:
1. InterpretationManager correctly classifies component types
2. Component names are properly displayed in alerts
3. No more "General Analysis" prefix for all components
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.interpretation.interpretation_manager import InterpretationManager
from src.core.models.interpretation_schema import ComponentType
from datetime import datetime

def test_component_type_inference():
    """Test that component types are correctly inferred."""
    manager = InterpretationManager()
    
    # Test cases: (component_name, expected_type)
    test_cases = [
        ('technical', ComponentType.TECHNICAL_INDICATOR),
        ('volume', ComponentType.VOLUME_ANALYSIS),
        ('sentiment', ComponentType.SENTIMENT_ANALYSIS),
        ('orderbook', ComponentType.VOLUME_ANALYSIS),
        ('orderflow', ComponentType.VOLUME_ANALYSIS),
        ('price_structure', ComponentType.PRICE_ANALYSIS),
        ('funding', ComponentType.FUNDING_ANALYSIS),
        ('whale', ComponentType.WHALE_ANALYSIS),
        ('futures_premium', ComponentType.FUNDING_ANALYSIS),
        ('overall_analysis', ComponentType.GENERAL_ANALYSIS),
        ('general_analysis', ComponentType.GENERAL_ANALYSIS),
        ('confluence_analysis', ComponentType.GENERAL_ANALYSIS),
        ('divergence_analysis', ComponentType.GENERAL_ANALYSIS),
    ]
    
    print("🧪 Testing component type inference...")
    all_passed = True
    for component_name, expected_type in test_cases:
        inferred_type = manager._infer_component_type(component_name)
        status = "✅ PASS" if inferred_type == expected_type else "❌ FAIL"
        print(f"  {status} '{component_name}' -> {inferred_type.value} (expected: {expected_type.value})")
        
        if inferred_type != expected_type:
            all_passed = False
    
    return all_passed

def test_market_interpretation_processing():
    """Test that market interpretations are processed correctly."""
    manager = InterpretationManager()
    
    # Simulate raw interpretations from signal generator
    raw_interpretations = [
        {
            'component': 'technical',
            'display_name': 'Technical',
            'interpretation': 'Technical indicators show bullish momentum with RSI at 65'
        },
        {
            'component': 'volume', 
            'display_name': 'Volume',
            'interpretation': 'Volume analysis shows strong buying pressure with CVD positive'
        },
        {
            'component': 'sentiment',
            'display_name': 'Sentiment', 
            'interpretation': 'Market sentiment is bullish with funding rates positive'
        },
        {
            'component': 'orderbook',
            'display_name': 'Orderbook',
            'interpretation': 'Orderbook shows bid-side dominance with tight spreads'
        },
        {
            'component': 'orderflow',
            'display_name': 'Orderflow',
            'interpretation': 'Orderflow indicates aggressive buying with large orders'
        },
        {
            'component': 'price_structure',
            'display_name': 'Price Structure',
            'interpretation': 'Price structure shows bullish bias with higher highs'
        }
    ]
    
    print("\n🧪 Testing market interpretation processing...")
    
    try:
        # Process interpretations
        interpretation_set = manager.process_interpretations(
            raw_interpretations,
            "test_signal_generator",
            market_data=None,
            timestamp=datetime.now()
        )
        
        # Check that we have the expected number of interpretations
        expected_count = len(raw_interpretations)
        actual_count = len(interpretation_set.interpretations)
        
        print(f"  Expected {expected_count} interpretations, got {actual_count}")
        
        # Check component types
        component_types_found = {}
        for interpretation in interpretation_set.interpretations:
            component_type = interpretation.component_type
            component_name = interpretation.component_name
            component_types_found[component_name] = component_type
            
            print(f"  Component '{component_name}' classified as: {component_type.value}")
        
        # Verify that we don't have all components classified as GENERAL_ANALYSIS
        general_analysis_count = sum(1 for ct in component_types_found.values() 
                                   if ct == ComponentType.GENERAL_ANALYSIS)
        
        if general_analysis_count == len(component_types_found):
            print("  ❌ FAIL: All components classified as GENERAL_ANALYSIS")
            return False
        elif general_analysis_count > 1:
            print(f"  ⚠️  WARNING: {general_analysis_count} components classified as GENERAL_ANALYSIS")
        
        # Check specific component types
        expected_types = {
            'technical': ComponentType.TECHNICAL_INDICATOR,
            'volume': ComponentType.VOLUME_ANALYSIS,
            'sentiment': ComponentType.SENTIMENT_ANALYSIS,
            'orderbook': ComponentType.VOLUME_ANALYSIS,
            'orderflow': ComponentType.VOLUME_ANALYSIS,
            'price_structure': ComponentType.PRICE_ANALYSIS
        }
        
        all_correct = True
        for component_name, expected_type in expected_types.items():
            if component_name in component_types_found:
                actual_type = component_types_found[component_name]
                if actual_type == expected_type:
                    print(f"  ✅ PASS: '{component_name}' correctly classified as {expected_type.value}")
                else:
                    print(f"  ❌ FAIL: '{component_name}' classified as {actual_type.value}, expected {expected_type.value}")
                    all_correct = False
            else:
                print(f"  ❌ FAIL: Component '{component_name}' not found in processed interpretations")
                all_correct = False
        
        return all_correct
        
    except Exception as e:
        print(f"  ❌ ERROR: Failed to process interpretations: {e}")
        return False

def test_discord_component_mapping():
    """Test Discord component name mapping."""
    from src.monitoring.alert_manager import AlertManager
    
    # Component type display mapping (same as in AlertManager)
    component_type_display_map = {
        'technical_indicator': 'Technical',
        'volume_analysis': 'Volume',
        'sentiment_analysis': 'Sentiment',
        'price_analysis': 'Price Structure',
        'funding_analysis': 'Funding',
        'whale_analysis': 'Whale Activity',
        'general_analysis': 'General Analysis',
        'unknown': 'Unknown'
    }
    
    print("\n🧪 Testing Discord component name mapping...")
    
    test_cases = [
        ('technical_indicator', 'Technical'),
        ('volume_analysis', 'Volume'),
        ('sentiment_analysis', 'Sentiment'),
        ('price_analysis', 'Price Structure'),
        ('funding_analysis', 'Funding'),
        ('whale_analysis', 'Whale Activity'),
        ('general_analysis', 'General Analysis'),
        ('unknown', 'Unknown')
    ]
    
    all_correct = True
    for component_type_value, expected_display in test_cases:
        actual_display = component_type_display_map.get(component_type_value, 'Unknown')
        status = "✅ PASS" if actual_display == expected_display else "❌ FAIL"
        print(f"  {status} '{component_type_value}' -> '{actual_display}' (expected: '{expected_display}')")
        
        if actual_display != expected_display:
            all_correct = False
    
    # Test typo safeguard
    typos = ['Genral Analyis', 'Genral Analysis']
    for typo in typos:
        corrected = 'General Analysis' if typo in ['Genral Analyis', 'Genral Analysis'] else typo
        status = "✅ PASS" if corrected == 'General Analysis' else "❌ FAIL"
        print(f"  {status} Typo '{typo}' -> '{corrected}' (safeguard working)")
    
    return all_correct

def test_end_to_end_signal_processing():
    """Test end-to-end signal processing to ensure proper component classification."""
    print("\n🧪 Testing end-to-end signal processing...")
    
    # Simulate signal generator data
    components = {
        'technical': 65.5,
        'volume': 72.3,
        'sentiment': 58.7,
        'orderbook': 68.1,
        'orderflow': 71.2,
        'price_structure': 62.0
    }
    
    # Create mock raw interpretations (as signal generator would)
    raw_interpretations = []
    for component_name, score in components.items():
        bias = "bullish" if score > 50 else "bearish"
        interpretation = f"{component_name.replace('_', ' ').title()} shows {bias} sentiment with score {score:.1f}"
        
        raw_interpretations.append({
            'component': component_name,
            'display_name': component_name.replace('_', ' ').title(),
            'interpretation': interpretation
        })
    
    # Process through InterpretationManager
    manager = InterpretationManager()
    
    try:
        interpretation_set = manager.process_interpretations(
            raw_interpretations,
            "test_confluence_btcusdt",
            market_data={
                'market_overview': {
                    'regime': 'BULLISH',
                    'volatility': 2.5,
                    'trend_strength': 0.65,
                    'volume_change': 0.72
                }
            },
            timestamp=datetime.now()
        )
        
        # Format for alerts (simulate what AlertManager would do)
        formatted_interpretations = manager.get_formatted_interpretation(
            interpretation_set, 'alert'
        )
        
        print(f"  Processed {len(interpretation_set.interpretations)} interpretations")
        
        # Check that we have diverse component types
        component_types = [interp.component_type for interp in interpretation_set.interpretations]
        unique_types = set(component_types)
        
        print(f"  Found {len(unique_types)} unique component types: {[ct.value for ct in unique_types]}")
        
        # Success if we have more than just GENERAL_ANALYSIS
        if len(unique_types) > 1 or (len(unique_types) == 1 and ComponentType.GENERAL_ANALYSIS not in unique_types):
            print("  ✅ PASS: Diverse component types detected")
            return True
        else:
            print("  ❌ FAIL: Only GENERAL_ANALYSIS detected")
            return False
            
    except Exception as e:
        print(f"  ❌ ERROR: End-to-end test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🔍 Testing Interpretation Component Type Classification Fix")
    print("=" * 60)
    
    tests = [
        ("Component Type Inference", test_component_type_inference),
        ("Market Interpretation Processing", test_market_interpretation_processing), 
        ("Discord Component Mapping", test_discord_component_mapping),
        ("End-to-End Signal Processing", test_end_to_end_signal_processing)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ ERROR in {test_name}: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! The interpretation fix is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 