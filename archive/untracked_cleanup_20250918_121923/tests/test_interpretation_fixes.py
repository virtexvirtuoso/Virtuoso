#!/usr/bin/env python3
"""
Test the interpretation fixes for orderflow and price_structure components.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from typing import Dict, Any

# Add the source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.analysis.confluence import ConfluenceAnalyzer
from core.analysis.interpretation_generator import InterpretationGenerator

# Configure logging to see debug messages
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_test_market_data() -> Dict[str, Any]:
    """Create realistic test market data."""
    # Generate realistic price movement (trending upward)
    base_price = 50000
    periods = 100
    
    # Create realistic OHLCV data with upward trend
    prices = []
    volumes = []
    
    for i in range(periods):
        # Add trend and some volatility
        trend_factor = 1 + (i * 0.001)  # 0.1% upward trend per period
        volatility = np.random.normal(0, 0.005)  # 0.5% volatility
        price = base_price * trend_factor * (1 + volatility)
        
        # Generate OHLC around the price
        high = price * (1 + abs(np.random.normal(0, 0.002)))
        low = price * (1 - abs(np.random.normal(0, 0.002)))
        open_price = price * (1 + np.random.normal(0, 0.001))
        close_price = price
        
        prices.append([open_price, high, low, close_price])
        volumes.append(np.random.uniform(1000, 5000))
    
    df_data = {
        'open': [p[0] for p in prices],
        'high': [p[1] for p in prices],
        'low': [p[2] for p in prices],
        'close': [p[3] for p in prices],
        'volume': volumes
    }
    
    return {
        'ohlcv': {
            '1m': pd.DataFrame(df_data),
            '5m': pd.DataFrame(df_data[::5] if len(df_data['open']) > 5 else df_data),
            '30m': pd.DataFrame({k: v[::30] if len(v) > 30 else v[:2] for k, v in df_data.items()})
        },
        'symbol': 'BTCUSDT',
        'timestamp': datetime.now(timezone.utc)
    }

async def test_interpretation_fixes():
    """Test the interpretation fixes."""
    print("=" * 60)
    print("TESTING INTERPRETATION FIXES")
    print("=" * 60)
    
    # Create test configuration
    config = {
        'confluence': {
            'weights': {
                'components': {
                    'technical': 0.20,
                    'volume': 0.10,
                    'orderflow': 0.25,
                    'sentiment': 0.15,
                    'orderbook': 0.20,
                    'price_structure': 0.10
                },
                'sub_components': {}
            }
        }
    }
    
    # Initialize confluence analyzer
    print("\n1. Initializing ConfluenceAnalyzer...")
    try:
        analyzer = ConfluenceAnalyzer(config)
        print("✅ ConfluenceAnalyzer initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize ConfluenceAnalyzer: {e}")
        return
    
    # Create test market data
    print("\n2. Creating test market data...")
    market_data = create_test_market_data()
    print(f"✅ Created market data with {len(market_data['ohlcv']['1m'])} 1m candles")
    
    # Run confluence analysis
    print("\n3. Running confluence analysis...")
    try:
        result = await analyzer.analyze(market_data)
        print("✅ Confluence analysis completed")
        
        # Check if we have results
        if 'results' in result:
            results = result['results']
            print(f"📊 Analysis results keys: {list(results.keys())}")
            
            # Check for market_interpretations
            if 'market_interpretations' in results:
                interpretations = results['market_interpretations']
                print(f"\n4. Found {len(interpretations)} market interpretations:")
                print("-" * 50)
                
                for i, interp in enumerate(interpretations, 1):
                    component = interp.get('component', 'unknown')
                    display_name = interp.get('display_name', 'Unknown')
                    interpretation_text = interp.get('interpretation', 'No interpretation')
                    
                    print(f"{i}. {display_name} ({component}):")
                    print(f"   {interpretation_text}")
                    
                    # Check for problematic patterns
                    if 'score=' in interpretation_text and 'interpretation=' in interpretation_text:
                        print("   ⚠️  RAW OBJECT REPRESENTATION DETECTED!")
                    elif interpretation_text.startswith('{') or 'value=' in interpretation_text:
                        print("   ⚠️  DICT-LIKE STRING REPRESENTATION DETECTED!")
                    else:
                        print("   ✅ Clean interpretation text")
                    
                    print()
                
                # Summary
                print("\n" + "=" * 60)
                print("SUMMARY")
                print("=" * 60)
                
                problematic_count = 0
                for interp in interpretations:
                    interpretation_text = interp.get('interpretation', '')
                    if ('score=' in interpretation_text and 'interpretation=' in interpretation_text) or \
                       interpretation_text.startswith('{') or 'value=' in interpretation_text:
                        problematic_count += 1
                
                if problematic_count == 0:
                    print(f"✅ ALL {len(interpretations)} INTERPRETATIONS ARE CLEAN!")
                    print("🎉 FIXES ARE WORKING CORRECTLY!")
                else:
                    print(f"❌ {problematic_count}/{len(interpretations)} interpretations still have issues")
                    print("🔧 Additional fixes may be needed")
                    
            else:
                print("❌ No market_interpretations found in results")
                print(f"Available result keys: {list(results.keys())}")
        else:
            print("❌ No results found in analysis output")
            print(f"Available keys: {list(result.keys())}")
            
    except Exception as e:
        print(f"❌ Error during confluence analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_interpretation_fixes())