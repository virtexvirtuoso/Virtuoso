#!/usr/bin/env python3

import yaml
import logging
import pandas as pd
import numpy as np
from src.indicators.orderflow_indicators import OrderflowIndicators
from src.core.logger import Logger

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger('test_orderflow_components')

def main():
    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create logger
    logger = Logger('test_orderflow_components')
    
    # Create OrderflowIndicators instance
    indicator = OrderflowIndicators(config, logger)
    
    # Print component weights
    print("\nComponent Weights:")
    for component, weight in indicator.component_weights.items():
        print(f"  {component}: {weight:.2f}")
    
    # Check if component mapping exists
    if hasattr(indicator, 'component_mapping'):
        print("\nComponent Mapping:")
        for config_name, internal_name in indicator.component_mapping.items():
            print(f"  {config_name} -> {internal_name}")
    else:
        print("\nNo component mapping found in OrderflowIndicators class")
    
    # Create sample data
    print("\nCreating sample data...")
    market_data = create_sample_data()
    
    # Calculate indicator scores
    print("\nCalculating indicator scores...")
    result = indicator.calculate(market_data)
    
    # Print results
    print("\nFinal Score:", result['score'])
    print("\nComponent Scores:")
    for component, score in result['components'].items():
        print(f"  {component}: {score:.2f}")
    
    # Verify that weights are being properly applied
    print("\nVerifying weight application...")
    
    # Extract component scores
    component_scores = {}
    for key, value in result['components'].items():
        if key in ['cvd', 'imbalance_score', 'trade_flow_score', 'open_interest_score', 'pressure_score']:
            component_scores[key] = value
    
    # Calculate expected weighted score
    expected_score = 0
    total_weight = 0
    
    # Map component names if needed
    component_mapping = {
        'imbalance_score': 'imbalance',
        'trade_flow_score': 'trade_flow',
        'open_interest_score': 'open_interest',
        'pressure_score': 'pressure'
    }
    
    for component, score in component_scores.items():
        # Map component name if needed
        config_component = component_mapping.get(component, component)
        weight = indicator.component_weights.get(config_component, 0)
        
        if weight > 0:
            print(f"  {component} -> {config_component}: {score:.2f} × {weight:.2f} = {score * weight:.2f}")
            expected_score += score * weight
            total_weight += weight
    
    if total_weight > 0:
        expected_score /= total_weight
    
    # Compare with actual score
    print(f"\n  Expected weighted score: {expected_score:.2f}")
    print(f"  Actual score: {result['score']:.2f}")
    print(f"  Difference: {abs(expected_score - result['score']):.4f}")
    
    if abs(expected_score - result['score']) < 5.0:
        print("  ✅ Weights are being applied (within reasonable margin)")
    else:
        print("  ❌ Weights are not being properly applied")
        print("  This suggests there might be inconsistencies in component naming or weight application")
    
    # Print pressure score details
    print("\nPressure Score Details:")
    if 'pressure_score' in result['components']:
        pressure_score = result['components']['pressure_score']
        print(f"  Pressure Score: {pressure_score:.2f}")
        
        if pressure_score > 60:
            print("  Interpretation: Strong buying pressure")
        elif pressure_score > 55:
            print("  Interpretation: Moderate buying pressure")
        elif pressure_score < 40:
            print("  Interpretation: Strong selling pressure")
        elif pressure_score < 45:
            print("  Interpretation: Moderate selling pressure")
        else:
            print("  Interpretation: Neutral pressure")
    else:
        print("  Pressure score not found in components")
    
    # Print open interest score details
    print("\nOpen Interest Score Details:")
    if 'open_interest_score' in result['components']:
        oi_score = result['components']['open_interest_score']
        print(f"  Open Interest Score: {oi_score:.2f}")
        
        if oi_score > 60:
            print("  Interpretation: Bullish (increasing open interest)")
        elif oi_score < 40:
            print("  Interpretation: Bearish (decreasing open interest)")
        else:
            print("  Interpretation: Neutral (stable open interest)")
    else:
        print("  Open interest score not found in components")
    
    # Test the new divergence functionality
    test_divergence_calculations(indicator, market_data)

def test_divergence_calculations(indicator, market_data):
    """Test the price-CVD and price-OI divergence calculations."""
    print("\n=== Testing Divergence Calculations ===")
    
    # Test price-CVD divergence
    print("\nTesting Price-CVD Divergence:")
    try:
        price_cvd_divergence = indicator._calculate_price_cvd_divergence(market_data)
        print(f"  Type: {price_cvd_divergence['type']}")
        print(f"  Strength: {price_cvd_divergence['strength']:.2f}")
        
        if price_cvd_divergence['type'] != 'neutral' and price_cvd_divergence['strength'] > 0:
            print(f"  ✅ Detected {price_cvd_divergence['type']} price-CVD divergence")
        else:
            print("  ℹ️ No significant price-CVD divergence detected")
    except Exception as e:
        print(f"  ❌ Error testing price-CVD divergence: {str(e)}")
    
    # Test price-OI divergence
    print("\nTesting Price-OI Divergence:")
    try:
        price_oi_divergence = indicator._calculate_price_oi_divergence(market_data)
        print(f"  Type: {price_oi_divergence['type']}")
        print(f"  Strength: {price_oi_divergence['strength']:.2f}")
        
        if price_oi_divergence['type'] != 'neutral' and price_oi_divergence['strength'] > 0:
            print(f"  ✅ Detected {price_oi_divergence['type']} price-OI divergence")
        else:
            print("  ℹ️ No significant price-OI divergence detected")
    except Exception as e:
        print(f"  ❌ Error testing price-OI divergence: {str(e)}")
    
    # Check if divergences are included in the result
    print("\nChecking Divergences in Result:")
    result = indicator.calculate(market_data)
    
    if 'divergences' in result and result['divergences']:
        print("  ✅ Divergences included in result")
        for key, divergence in result['divergences'].items():
            print(f"  - {key}: {divergence['type']} (strength: {divergence['strength']:.2f})")
            if 'description' in divergence:
                print(f"    Description: {divergence['description']}")
    else:
        print("  ℹ️ No divergences included in result")
    
    # Create test data with forced divergences
    print("\nTesting with Forced Divergences:")
    
    # Create bullish price-CVD divergence (price down, CVD up)
    bullish_market_data = create_sample_data_with_divergence('bullish')
    bullish_result = indicator.calculate(bullish_market_data)
    
    print("\nBullish Divergence Test:")
    if 'divergences' in bullish_result and 'price_cvd' in bullish_result['divergences']:
        div = bullish_result['divergences']['price_cvd']
        print(f"  ✅ Detected {div['type']} price-CVD divergence (strength: {div['strength']:.2f})")
        if div['type'] == 'bullish':
            print("  ✅ Correctly identified as bullish divergence")
        else:
            print(f"  ❌ Incorrectly identified as {div['type']} divergence (expected: bullish)")
    else:
        print("  ❌ Failed to detect bullish price-CVD divergence")
    
    # Create bearish price-CVD divergence (price up, CVD down)
    bearish_market_data = create_sample_data_with_divergence('bearish')
    bearish_result = indicator.calculate(bearish_market_data)
    
    print("\nBearish Divergence Test:")
    if 'divergences' in bearish_result and 'price_cvd' in bearish_result['divergences']:
        div = bearish_result['divergences']['price_cvd']
        print(f"  ✅ Detected {div['type']} price-CVD divergence (strength: {div['strength']:.2f})")
        if div['type'] == 'bearish':
            print("  ✅ Correctly identified as bearish divergence")
        else:
            print(f"  ❌ Incorrectly identified as {div['type']} divergence (expected: bearish)")
    else:
        print("  ❌ Failed to detect bearish price-CVD divergence")

def create_sample_data():
    """Create sample market data for testing OrderflowIndicators."""
    # Create sample OHLCV data
    df = pd.DataFrame({
        'timestamp': pd.date_range(start='2023-01-01', periods=100, freq='1H'),
        'open': np.random.normal(50000, 100, 100),
        'high': np.random.normal(50100, 100, 100),
        'low': np.random.normal(49900, 100, 100),
        'close': np.random.normal(50000, 100, 100),
        'volume': np.random.normal(10, 2, 100)
    })
    
    # Ensure high is always highest and low is always lowest
    for i in range(len(df)):
        values = [df.loc[i, 'open'], df.loc[i, 'close']]
        df.loc[i, 'high'] = max(values) + abs(np.random.normal(50, 10))
        df.loc[i, 'low'] = min(values) - abs(np.random.normal(50, 10))
    
    # Create sample trades data
    trades = []
    for i in range(1000):  # Create 1000 trades
        price = np.random.normal(50000, 100)
        side = 'buy' if np.random.random() > 0.5 else 'sell'
        trades.append({
            'id': i,
            'price': price,
            'size': np.random.normal(1, 0.2),
            'side': side,
            'time': pd.Timestamp('2023-01-01') + pd.Timedelta(seconds=i*10)
        })
    
    # Create sample orderbook data
    bids = [[49900 - i*10, np.random.normal(10, 2)] for i in range(10)]
    asks = [[50100 + i*10, np.random.normal(10, 2)] for i in range(10)]
    
    # Create sample sentiment data with open interest history
    oi_history = []
    base_oi = 10000.0
    
    # Create OI history aligned with OHLCV timestamps
    for i, timestamp in enumerate(df['timestamp']):
        # Add some random variation to open interest
        oi_value = base_oi + np.random.normal(0, 100)
        if i > 0:
            # Add a slight trend
            oi_value += (i % 20) - 10  # Oscillating trend
        
        oi_history.append({
            'timestamp': timestamp,
            'value': float(oi_value)
        })
    
    # Assemble market data
    market_data = {
        'ohlcv': {
            'base': df,
            'ltf': df,
            'mtf': df,
            'htf': df
        },
        'trades': trades,
        'orderbook': {
            'bids': bids,
            'asks': asks
        },
        'sentiment': {
            'open_interest': {
                'current': float(oi_history[-1]['value']),
                'previous': float(oi_history[-2]['value']),
                'history': oi_history
            }
        },
        'symbol': 'BTCUSDT'
    }
    
    return market_data

def create_sample_data_with_divergence(divergence_type='bullish'):
    """Create sample market data with a specific divergence pattern.
    
    Args:
        divergence_type: Type of divergence to create ('bullish' or 'bearish')
        
    Returns:
        Dict: Market data with the specified divergence pattern
    """
    # Start with base sample data
    market_data = create_sample_data()
    
    # Get the base OHLCV data
    df = market_data['ohlcv']['base'].copy()
    
    # Modify the last 10 candles to create the divergence pattern
    if divergence_type == 'bullish':
        # Bullish divergence: Price down, CVD up
        # Make price trend down
        for i in range(1, 11):
            idx = len(df) - i
            df.loc[idx, 'close'] = df.loc[idx-1, 'close'] * 0.995  # Decrease by 0.5%
            df.loc[idx, 'open'] = df.loc[idx, 'close'] * 1.001
            df.loc[idx, 'high'] = max(df.loc[idx, 'open'], df.loc[idx, 'close']) * 1.002
            df.loc[idx, 'low'] = min(df.loc[idx, 'open'], df.loc[idx, 'close']) * 0.998
        
        # Create trades with more buys than sells for positive CVD
        trades = []
        for i in range(2000):
            price = df.iloc[-1]['close'] * (1 + np.random.normal(0, 0.001))
            # 70% buys for positive CVD
            side = 'buy' if np.random.random() < 0.7 else 'sell'
            trades.append({
                'id': i,
                'price': price,
                'size': np.random.normal(1, 0.2),
                'side': side,
                'time': df.iloc[-10:]['timestamp'].iloc[i % 10]  # Distribute across last 10 candles
            })
    
    elif divergence_type == 'bearish':
        # Bearish divergence: Price up, CVD down
        # Make price trend up
        for i in range(1, 11):
            idx = len(df) - i
            df.loc[idx, 'close'] = df.loc[idx-1, 'close'] * 1.005  # Increase by 0.5%
            df.loc[idx, 'open'] = df.loc[idx, 'close'] * 0.999
            df.loc[idx, 'high'] = max(df.loc[idx, 'open'], df.loc[idx, 'close']) * 1.002
            df.loc[idx, 'low'] = min(df.loc[idx, 'open'], df.loc[idx, 'close']) * 0.998
        
        # Create trades with more sells than buys for negative CVD
        trades = []
        for i in range(2000):
            price = df.iloc[-1]['close'] * (1 + np.random.normal(0, 0.001))
            # 70% sells for negative CVD
            side = 'sell' if np.random.random() < 0.7 else 'buy'
            trades.append({
                'id': i,
                'price': price,
                'size': np.random.normal(1, 0.2),
                'side': side,
                'time': df.iloc[-10:]['timestamp'].iloc[i % 10]  # Distribute across last 10 candles
            })
    
    # Update market data with modified OHLCV and trades
    market_data['ohlcv']['base'] = df
    market_data['trades'] = trades
    
    # Also update OI history to align with the new price pattern
    oi_history = []
    base_oi = 10000.0
    
    for i, timestamp in enumerate(df['timestamp']):
        if i >= len(df) - 10:
            # For the last 10 candles, create OI pattern based on divergence type
            if divergence_type == 'bullish':
                # Bullish divergence: OI should increase while price decreases
                trend_factor = 50 * (i - (len(df) - 11)) / 10  # Increasing trend
            else:
                # Bearish divergence: OI should decrease while price increases
                trend_factor = -50 * (i - (len(df) - 11)) / 10  # Decreasing trend
        else:
            trend_factor = 0
        
        oi_value = base_oi + trend_factor + np.random.normal(0, 20)
        
        oi_history.append({
            'timestamp': timestamp,
            'value': float(oi_value)
        })
    
    # Update sentiment data
    market_data['sentiment']['open_interest']['history'] = oi_history
    market_data['sentiment']['open_interest']['current'] = float(oi_history[-1]['value'])
    market_data['sentiment']['open_interest']['previous'] = float(oi_history[-2]['value'])
    
    return market_data

if __name__ == "__main__":
    main() 