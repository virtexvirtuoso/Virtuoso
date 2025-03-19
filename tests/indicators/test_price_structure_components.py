#!/usr/bin/env python3

import yaml
import logging
import pandas as pd
import numpy as np
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.core.logger import Logger

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

async def main():
    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create logger
    logger = Logger('test_price_structure_components')
    
    # Create PriceStructureIndicators instance
    indicator = PriceStructureIndicators(config, logger)
    
    # Print component weights
    print("\nComponent Weights:")
    for component, weight in indicator.component_weights.items():
        print(f"  {component}: {weight:.2f}")
    
    # Print component mapping
    print("\nComponent Mapping:")
    for config_name, internal_name in indicator.component_mapping.items():
        print(f"  {config_name} -> {internal_name}")
    
    # Create sample OHLCV data
    print("\nCreating sample OHLCV data...")
    df = create_sample_data()
    
    # Create market data structure
    market_data = {
        'ohlcv': {
            'base': df,
            'ltf': df,
            'mtf': df,
            'htf': df
        },
        'symbol': 'BTCUSDT'
    }
    
    # Calculate indicator scores
    print("\nCalculating indicator scores...")
    result = await indicator.calculate(market_data)
    
    # Print results
    print("\nFinal Score:", result['score'])
    print("\nComponent Scores:")
    for component, score in result['components'].items():
        print(f"  {component}: {score:.2f}")
    
    # Verify that both market_structure and composite_value have their own scores
    print("\nVerifying component scores...")
    if 'market_structure' in result['components'] and 'composite_value' in result['components']:
        print("  ✅ Both market_structure and composite_value have their own scores")
        print(f"  market_structure: {result['components']['market_structure']:.2f}")
        print(f"  composite_value: {result['components']['composite_value']:.2f}")
    else:
        print("  ❌ Missing one or both components:")
        print(f"  market_structure in components: {'market_structure' in result['components']}")
        print(f"  composite_value in components: {'composite_value' in result['components']}")
    
    # Verify that the weights are being properly applied
    print("\nVerifying weight application...")
    
    # Calculate expected weighted score
    expected_score = 0
    total_weight = 0
    for component, score in result['components'].items():
        weight = indicator.component_weights.get(component, 0)
        expected_score += score * weight
        total_weight += weight
    
    if total_weight > 0:
        expected_score /= total_weight
    
    print(f"  Expected weighted score: {expected_score:.2f}")
    print(f"  Actual score: {result['score']:.2f}")
    print(f"  Difference: {abs(expected_score - result['score']):.4f}")
    
    if abs(expected_score - result['score']) < 0.01:
        print("  ✅ Weights are being properly applied")
    else:
        print("  ❌ Weights are not being properly applied")

def create_sample_data():
    """Create sample OHLCV data for testing."""
    # Create a dataframe with 100 rows of sample data
    np.random.seed(42)  # For reproducibility
    
    # Start with a base price
    base_price = 50000
    
    # Create price series with some trend and volatility
    prices = []
    current_price = base_price
    
    for i in range(100):
        # Add some random walk
        change = np.random.normal(0, 100)
        # Add slight uptrend
        trend = 10
        current_price += change + trend
        prices.append(current_price)
    
    # Convert to OHLCV
    df = pd.DataFrame({
        'timestamp': pd.date_range(start='2023-01-01', periods=100, freq='1H'),
        'open': prices,
        'high': [p + abs(np.random.normal(0, 50)) for p in prices],
        'low': [p - abs(np.random.normal(0, 50)) for p in prices],
        'close': prices,
        'volume': [abs(np.random.normal(100, 30)) for _ in range(100)]
    })
    
    return df

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 