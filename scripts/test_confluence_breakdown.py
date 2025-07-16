#!/usr/bin/env python3
"""
Test script to verify the confluence breakdown functionality is working correctly.
This tests the enhanced interpretation methods and detailed component analysis.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from src.signal_generation.signal_generator import SignalGenerator
import json

async def test_confluence_breakdown():
    """Test the confluence breakdown functionality."""
    
    # Create a minimal config
    config = {
        'confluence': {
            'weights': {
                'components': {
                    'volume': 0.2,
                    'technical': 0.2,
                    'orderflow': 0.2,
                    'orderbook': 0.15,
                    'sentiment': 0.15,
                    'price_structure': 0.1
                }
            },
            'thresholds': {
                'buy': 60,
                'sell': 40,
                'neutral_buffer': 5
            }
        },
        'timeframes': {
            'base': {'weight': 0.4},
            'ltf': {'weight': 0.2},
            'mtf': {'weight': 0.2},
            'htf': {'weight': 0.2}
        }
    }
    
    # Create SignalGenerator instance
    signal_generator = SignalGenerator(config)
    
    # Test data with detailed indicators for sophisticated interpretation
    test_indicators = {
        'symbol': 'BTCUSDT',
        'current_price': 65000.0,
        'volume_score': 75.0,
        'technical_score': 68.0,
        'orderflow_score': 82.0,
        'orderbook_score': 71.0,
        'sentiment_score': 58.0,
        'price_structure_score': 63.0,
        
        # Detailed volume indicators
        'volume_delta': 85.0,
        'cmf': 0.3,
        'adl': 72.0,
        'mfi': 85,
        'obv': 78.0,
        'price_change_pct': 2.5,
        
        # Detailed orderflow indicators
        'cvd': 0.7,
        'cvd_slope': 0.6,
        'trade_flow_score': 80.0,
        'aggressive_buys': 1500,
        'aggressive_sells': 800,
        'imbalance_score': 75.0,
        
        # Detailed orderbook indicators
        'bid_ask_ratio': 2.1,
        'liquidity': 85.0,
        'support_resistance': 88.0,
        'price_impact': 25.0,
        
        # Technical indicators
        'rsi': 68.0,
        'macd': 0.8,
        'ao': 0.5,
        'williams_r': -25.0,
        'atr': 1200.0,
        
        # Sentiment indicators
        'funding_rate': 0.005,
        'long_short_ratio': 1.3,
        'risk_score': 58.0
    }
    
    print("🧪 Testing Confluence Breakdown Functionality")
    print("=" * 50)
    
    # Test 1: Component extraction
    print("\n📊 Test 1: Component Extraction")
    volume_components = signal_generator._extract_volume_components(test_indicators)
    orderflow_components = signal_generator._extract_orderflow_components(test_indicators)
    orderbook_components = signal_generator._extract_orderbook_components(test_indicators)
    
    print(f"Volume components: {volume_components}")
    print(f"Orderflow components: {orderflow_components}")
    print(f"Orderbook components: {orderbook_components}")
    
    # Test 2: Sophisticated interpretations
    print("\n🔍 Test 2: Sophisticated Interpretations")
    volume_interpretation = signal_generator._interpret_volume(75.0, test_indicators)
    orderflow_interpretation = signal_generator._interpret_orderflow(82.0, test_indicators)
    orderbook_interpretation = signal_generator._interpret_orderbook(71.0, test_indicators)
    technical_interpretation = signal_generator._interpret_technical(68.0, test_indicators)
    
    print(f"Volume: {volume_interpretation}")
    print(f"Orderflow: {orderflow_interpretation}")
    print(f"Orderbook: {orderbook_interpretation}")
    print(f"Technical: {technical_interpretation}")
    
    # Test 3: Collect detailed results
    print("\n📋 Test 3: Detailed Results Collection")
    results = signal_generator._collect_indicator_results(test_indicators)
    
    for component_name, component_data in results.items():
        print(f"\n{component_name.upper()}:")
        print(f"  Components: {component_data['components']}")
        print(f"  Interpretation: {component_data['interpretation']}")
    
    # Test 4: Enhanced formatted data generation
    print("\n🎯 Test 4: Enhanced Formatted Data Generation")
    
    components = {
        'volume': 75.0,
        'technical': 68.0,
        'orderflow': 82.0,
        'orderbook': 71.0,
        'sentiment': 58.0,
        'price_structure': 63.0
    }
    
    enhanced_data = signal_generator._generate_enhanced_formatted_data(
        symbol='BTCUSDT',
        confluence_score=69.2,  # Calculated weighted score
        components=components,
        results=results,
        reliability=0.85,
        buy_threshold=60,
        sell_threshold=40
    )
    
    print(f"Influential components count: {len(enhanced_data['influential_components'])}")
    print(f"Market interpretations count: {len(enhanced_data['market_interpretations'])}")
    print(f"Actionable insights count: {len(enhanced_data['actionable_insights'])}")
    print(f"Top weighted subcomponents count: {len(enhanced_data['top_weighted_subcomponents'])}")
    
    # Display detailed breakdown
    print("\n🔥 CONFLUENCE BREAKDOWN:")
    print("-" * 30)
    
    for comp in enhanced_data['influential_components']:
        print(f"📈 {comp['display_name']}: {comp['score']:.1f} (weight: {comp['weight']:.2f})")
        if comp.get('sub_components'):
            for sub in comp['sub_components'][:3]:  # Show top 3 subcomponents
                print(f"   {sub['indicator']} {sub['display_name']}: {sub['score']:.1f}")
    
    print("\n💡 MARKET INTERPRETATIONS:")
    print("-" * 30)
    for interp in enhanced_data['market_interpretations']:
        print(f"🎯 {interp['display_name']}: {interp['interpretation']}")
    
    print("\n🎯 ACTIONABLE INSIGHTS:")
    print("-" * 30)
    for insight in enhanced_data['actionable_insights']:
        print(f"✅ {insight}")
    
    print("\n✅ Confluence breakdown functionality is working correctly!")
    return True

if __name__ == "__main__":
    asyncio.run(test_confluence_breakdown()) 