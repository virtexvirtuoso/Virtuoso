#!/usr/bin/env python3
"""Test enhanced order block improvements."""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.core.logger import Logger

def create_test_data():
    """Create test OHLCV data."""
    np.random.seed(42)
    periods = 200
    base_price = 50000.0
    
    data = []
    current_price = base_price
    
    for i in range(periods):
        # Create consolidation then expansion pattern
        if i % 20 < 10:  # Consolidation
            change = np.random.normal(0, 0.001) * current_price
            volume = 1000
        else:  # Expansion
            change = np.random.normal(0.01, 0.005) * current_price
            volume = 3000
        
        open_price = current_price
        close_price = current_price + change
        high = max(open_price, close_price) + abs(change) * 0.2
        low = min(open_price, close_price) - abs(change) * 0.2
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
        
        current_price = close_price
    
    timestamps = [datetime.now() - timedelta(minutes=periods-i) for i in range(periods)]
    return pd.DataFrame(data, index=timestamps)

def test_order_blocks():
    """Test enhanced order block functionality."""
    print("Testing Enhanced Order Block Implementation")
    print("=" * 50)
    
    try:
        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        logger = Logger(__name__)
        indicator = PriceStructureIndicators(config, logger)
        
        # Create test data
        df = create_test_data()
        print(f"✓ Created {len(df)} periods of test data")
        
        # Test order block detection
        order_blocks = indicator._calculate_order_blocks(df)
        print(f"✓ Bullish blocks: {len(order_blocks['bullish'])}")
        print(f"✓ Bearish blocks: {len(order_blocks['bearish'])}")
        
        # Test scoring
        score = indicator._calculate_order_blocks_score(df)
        print(f"✓ Order block score: {score:.2f}")
        
        # Show sample block details
        if order_blocks['bullish']:
            block = order_blocks['bullish'][0]
            print(f"✓ Sample block strength: {block.get('strength', 'N/A')}")
            print(f"✓ Mitigation status: {block.get('mitigation_status', {}).get('is_mitigated', 'N/A')}")
        
        print("\n🎉 Enhanced order block test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_order_blocks() 