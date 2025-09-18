#!/usr/bin/env python3
"""
Local test script for Phase 1 Enhanced Liquidation Analysis
Tests the implementation with realistic market scenarios
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

# Add project path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from src.core.analysis.enhanced_liquidation_analyzer import (
        EnhancedLiquidationAnalyzer,
        create_enhanced_liquidation_analyzer,
        enhance_liquidation_score
    )
    from src.indicators.sentiment_indicators import SentimentIndicators
    print("✅ Successfully imported Phase 1 modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def create_market_data_scenario(scenario_type='uptrend'):
    """Create realistic market data for different scenarios"""
    
    num_periods = 100
    base_price = 50000
    
    if scenario_type == 'uptrend':
        # Uptrend scenario - price increasing with pullbacks
        trend = np.linspace(0, 5000, num_periods)
        noise = np.random.normal(0, 200, num_periods)
        prices = base_price + trend + noise
        
        # Add some healthy corrections
        for i in range(20, 80, 20):
            prices[i:i+5] *= 0.98  # 2% pullbacks
            
    elif scenario_type == 'downtrend':
        # Downtrend scenario - price decreasing with bounces
        trend = np.linspace(0, -5000, num_periods)
        noise = np.random.normal(0, 200, num_periods)
        prices = base_price + trend + noise
        
        # Add some relief rallies
        for i in range(20, 80, 20):
            prices[i:i+5] *= 1.02  # 2% bounces
            
    elif scenario_type == 'sideways':
        # Sideways/ranging market
        prices = base_price + np.random.normal(0, 500, num_periods)
        prices = pd.Series(prices).rolling(window=5).mean().fillna(base_price).values
        
    else:  # volatile
        # High volatility scenario
        prices = base_price + np.random.normal(0, 1000, num_periods)
        # Add some sharp moves
        prices[30:35] *= 0.95  # 5% drop
        prices[60:65] *= 1.05  # 5% spike
    
    # Create OHLCV DataFrame
    df = pd.DataFrame()
    dates = pd.date_range(start='2024-01-01', periods=num_periods, freq='1h')
    df.index = dates
    
    df['close'] = prices
    df['open'] = np.roll(prices, 1)
    df['open'][0] = prices[0]
    
    # High and low with realistic wicks
    df['high'] = df[['open', 'close']].max(axis=1) * np.random.uniform(1.001, 1.005, num_periods)
    df['low'] = df[['open', 'close']].min(axis=1) * np.random.uniform(0.995, 0.999, num_periods)
    
    # Volume (higher on big moves)
    price_change = np.abs(df['close'].pct_change().fillna(0))
    df['volume'] = 1000000 * (1 + price_change * 10) * np.random.uniform(0.8, 1.2, num_periods)
    
    return df

def test_scenario(scenario_name, liquidation_score, market_scenario):
    """Test a specific market scenario"""
    
    print(f"\n{'='*60}")
    print(f"Testing: {scenario_name}")
    print(f"Base Liquidation Score: {liquidation_score}")
    print(f"Market Scenario: {market_scenario}")
    print('='*60)
    
    # Create market data
    ohlcv_df = create_market_data_scenario(market_scenario)
    
    # Initialize analyzer
    analyzer = EnhancedLiquidationAnalyzer(
        adx_period=14,
        ema_short_period=9,
        ema_long_period=21,
        sr_lookback_periods=50,
        sr_distance_threshold=0.02
    )
    
    # Prepare market data dict
    market_data = {
        'ohlcv': ohlcv_df,
        'symbol': 'BTCUSDT',
        'exchange': 'test'
    }
    
    # Analyze with enhancements
    result = analyzer.analyze_enhanced_liquidation(
        base_liquidation_score=liquidation_score,
        market_data=market_data,
        price_data=ohlcv_df
    )
    
    # Display results
    print(f"\n📊 Analysis Results:")
    print(f"  Base Score: {result.base_score:.2f}")
    print(f"  Regime Adjusted: {result.regime_adjusted_score:.2f}")
    print(f"  Final Score: {result.final_score:.2f}")
    print(f"  Confidence: {result.confidence:.2%}")
    
    if result.market_regime:
        print(f"\n📈 Market Regime:")
        print(f"  Direction: {result.market_regime.trend_direction}")
        print(f"  Strength (ADX): {result.market_regime.trend_strength:.2f}")
        print(f"  Regime Factor: {result.market_regime.regime_factor:.3f}x")
        
    if result.sr_context:
        current_price = ohlcv_df['close'].iloc[-1]
        print(f"\n📍 S/R Context (Current Price: ${current_price:,.2f}):")
        print(f"  Nearest Support: ${result.sr_context.nearest_support:,.2f} ({result.sr_context.distance_to_support_pct:+.1f}%)")
        print(f"  Nearest Resistance: ${result.sr_context.nearest_resistance:,.2f} ({result.sr_context.distance_to_resistance_pct:+.1f}%)")
        print(f"  S/R Adjustment: {result.sr_context.adjustment_factor:.3f}x")
        
    print(f"\n💡 Reasoning:")
    for reason in result.reasoning[:5]:  # Show first 5 reasons
        print(f"  • {reason}")
    
    # Determine signal interpretation
    signal = "NEUTRAL"
    if result.final_score >= 70:
        signal = "STRONG BUY"
    elif result.final_score >= 60:
        signal = "BUY"
    elif result.final_score <= 30:
        signal = "STRONG SELL"
    elif result.final_score <= 40:
        signal = "SELL"
    
    print(f"\n🎯 Trading Signal: {signal}")
    
    # Show adjustment impact
    adjustment = result.final_score - result.base_score
    if abs(adjustment) > 0.1:
        direction = "increased" if adjustment > 0 else "decreased"
        print(f"\n✨ Enhancement Impact: Score {direction} by {abs(adjustment):.1f} points")
    
    return result

def test_integration_with_sentiment():
    """Test integration with existing sentiment indicators"""
    
    print(f"\n{'='*60}")
    print("Testing Integration with Sentiment Indicators")
    print('='*60)
    
    # Create sample market data
    ohlcv_df = create_market_data_scenario('uptrend')
    
    # Prepare config
    config = {
        'sentiment': {
            'enhanced_liquidation': {
                'enable': True,
                'adx_period': 14,
                'ema_short_period': 9,
                'ema_long_period': 21,
                'sr_lookback_periods': 50,
                'sr_distance_threshold': 0.02,
                'fallback_enabled': True
            }
        }
    }
    
    try:
        # Initialize sentiment indicators
        sentiment = SentimentIndicators(config=config)
        
        # Check if enhanced analyzer was initialized
        if hasattr(sentiment, 'enhanced_liquidation_analyzer'):
            print("✅ Enhanced liquidation analyzer integrated with SentimentIndicators")
            print(f"   Feature enabled: {sentiment.enable_enhanced_liquidation}")
            print(f"   Fallback enabled: {sentiment.enhanced_liquidation_fallback}")
        else:
            print("❌ Enhanced liquidation analyzer not found in SentimentIndicators")
            
    except Exception as e:
        print(f"⚠️ Integration test encountered an issue: {e}")
    
def main():
    """Run comprehensive local tests"""
    
    print("\n" + "="*60)
    print("🚀 Phase 1 Enhanced Liquidation Analysis - Local Testing")
    print("="*60)
    
    # Test scenarios
    test_cases = [
        # (scenario_name, liquidation_score, market_scenario)
        ("Bearish signal in uptrend (should be dampened)", 25, 'uptrend'),
        ("Bullish signal in uptrend (should be amplified)", 75, 'uptrend'),
        ("Bearish signal in downtrend (should be amplified)", 25, 'downtrend'),
        ("Bullish signal in downtrend (should be dampened)", 75, 'downtrend'),
        ("Neutral signal in sideways market", 50, 'sideways'),
        ("Extreme bearish in volatile market", 15, 'volatile'),
        ("Extreme bullish in volatile market", 85, 'volatile'),
    ]
    
    results = []
    for scenario_name, liq_score, market_scenario in test_cases:
        try:
            result = test_scenario(scenario_name, liq_score, market_scenario)
            results.append({
                'scenario': scenario_name,
                'base': result.base_score,
                'final': result.final_score,
                'adjustment': result.final_score - result.base_score,
                'confidence': result.confidence
            })
        except Exception as e:
            print(f"❌ Error in scenario '{scenario_name}': {e}")
            
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    if results:
        df_results = pd.DataFrame(results)
        print(f"\nAverage adjustment: {df_results['adjustment'].mean():+.2f} points")
        print(f"Average confidence: {df_results['confidence'].mean():.2%}")
        print(f"Max positive adjustment: {df_results['adjustment'].max():+.2f} points")
        print(f"Max negative adjustment: {df_results['adjustment'].min():+.2f} points")
        
        print("\nDetailed Results:")
        for _, row in df_results.iterrows():
            adj_str = f"{row['adjustment']:+.1f}" if abs(row['adjustment']) > 0.1 else "no change"
            print(f"  • {row['scenario'][:40]:40s} : {row['base']:.0f} → {row['final']:.0f} ({adj_str})")
    
    # Test integration
    test_integration_with_sentiment()
    
    print("\n✅ Local testing complete!")
    print("\n💡 Next steps:")
    print("  1. Review the adjustment patterns above")
    print("  2. Verify regime detection is working correctly")
    print("  3. Check S/R adjustments near key levels")
    print("  4. If satisfied, deploy to VPS for production testing")

if __name__ == "__main__":
    main()