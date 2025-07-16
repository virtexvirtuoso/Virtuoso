#!/usr/bin/env python3

import yaml
import pandas as pd
import numpy as np
import logging
import asyncio
from datetime import datetime, timedelta
from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.core.logger import Logger

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

def create_realistic_ohlcv_data(periods=500, symbol="BTCUSDT"):
    """Create realistic OHLCV data that mimics real market data"""
    np.random.seed(42)  # For reproducible results
    
    # Start with a realistic BTC price
    base_price = 45000.0
    
    # Generate realistic price movements with trend and volatility
    returns = []
    for i in range(periods):
        # Add some trend component
        trend = 0.0001 * np.sin(i / 100)  # Slow trend cycle
        
        # Add volatility clustering
        volatility = 0.015 + 0.01 * abs(np.sin(i / 50))
        
        # Generate return with trend and volatility
        daily_return = trend + np.random.normal(0, volatility)
        returns.append(daily_return)
    
    # Calculate prices
    prices = [base_price]
    for ret in returns:
        new_price = prices[-1] * (1 + ret)
        prices.append(new_price)
    
    prices = np.array(prices[1:])  # Remove initial price
    
    # Create OHLCV data with realistic intraday movements
    data = []
    for i in range(periods):
        close_price = prices[i]
        
        # Create realistic OHLC from close price
        daily_range = close_price * np.random.uniform(0.005, 0.03)  # 0.5% to 3% daily range
        
        # Open price (previous close with small gap)
        if i == 0:
            open_price = close_price * (1 + np.random.normal(0, 0.002))
        else:
            open_price = prices[i-1] * (1 + np.random.normal(0, 0.002))
        
        # High and low based on open and close
        high_price = max(open_price, close_price) + daily_range * np.random.uniform(0.3, 0.7)
        low_price = min(open_price, close_price) - daily_range * np.random.uniform(0.3, 0.7)
        
        # Realistic volume (higher volume on bigger moves)
        price_change = abs(close_price - open_price) / open_price
        base_volume = np.random.uniform(1000, 5000)
        volume_multiplier = 1 + (price_change * 10)  # Higher volume on bigger moves
        volume = base_volume * volume_multiplier
        
        # Create timestamp (1-minute intervals going back from now)
        timestamp = datetime.now() - timedelta(minutes=(periods - i))
        
        data.append({
            'timestamp': timestamp,
            'open': float(open_price),
            'high': float(high_price),
            'low': float(low_price),
            'close': float(close_price),
            'volume': float(volume)
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df

def create_realistic_trades_data(periods=200, base_price=45000):
    """Create realistic trade data"""
    np.random.seed(42)
    
    trades = []
    current_price = base_price
    
    for i in range(periods):
        # Price movement
        price_change = np.random.normal(0, 0.001)  # Small price movements
        current_price *= (1 + price_change)
        
        # Trade size (realistic distribution)
        if np.random.random() < 0.1:  # 10% large trades
            size = np.random.uniform(5.0, 50.0)
        else:  # 90% smaller trades
            size = np.random.uniform(0.01, 2.0)
        
        # Side (slightly biased based on price trend)
        if price_change > 0:
            side = np.random.choice(['buy', 'sell'], p=[0.6, 0.4])
        else:
            side = np.random.choice(['buy', 'sell'], p=[0.4, 0.6])
        
        # Timestamp
        timestamp = datetime.now() - timedelta(minutes=(periods - i))
        
        trades.append({
            'price': float(current_price),
            'size': float(size),
            'side': side,
            'time': timestamp
        })
    
    return pd.DataFrame(trades)

def create_multi_timeframe_data(base_df):
    """Create multiple timeframe data from base 1-minute data"""
    timeframes = {
        'base': base_df,  # 1-minute data
        'ltf': base_df.iloc[::5].copy(),   # 5-minute data (every 5th candle)
        'mtf': base_df.iloc[::30].copy(),  # 30-minute data (every 30th candle)
        'htf': base_df.iloc[::240].copy()  # 4-hour data (every 240th candle)
    }
    
    # Ensure we have enough data for each timeframe
    for tf_name, tf_data in timeframes.items():
        print(f"{tf_name.upper()} timeframe: {len(tf_data)} candles")
    
    return timeframes

async def test_volume_indicators_real_data():
    """Test VolumeIndicators with realistic market data"""
    print("\n" + "="*70)
    print("TESTING VOLUME INDICATORS WITH REALISTIC DATA")
    print("="*70)
    
    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create logger
    logger = Logger('test_volume_real')
    
    # Create VolumeIndicators instance
    volume_indicator = VolumeIndicators(config, logger)
    
    print(f"\n1. Volume Indicator Configuration:")
    print(f"   Components: {list(volume_indicator.component_weights.keys())}")
    print(f"   Total weight: {sum(volume_indicator.component_weights.values()):.4f}")
    
    # Create realistic market data
    base_ohlcv = create_realistic_ohlcv_data(periods=500, symbol="BTCUSDT")
    trades_data = create_realistic_trades_data(periods=300, base_price=base_ohlcv['close'].iloc[0])
    
    # Create multi-timeframe data
    ohlcv_data = create_multi_timeframe_data(base_ohlcv)
    
    # Test data structure
    test_data = {
        'ticker': 'BTCUSDT',
        'timeframe': 'base',
        'ohlcv': ohlcv_data,
        'trades': trades_data
    }
    
    print(f"\n2. Market Data Summary:")
    print(f"   Symbol: BTCUSDT")
    print(f"   Base timeframe: {len(ohlcv_data['base'])} candles")
    print(f"   Price range: ${ohlcv_data['base']['low'].min():.2f} - ${ohlcv_data['base']['high'].max():.2f}")
    print(f"   Current price: ${ohlcv_data['base']['close'].iloc[-1]:.2f}")
    print(f"   Total trades: {len(trades_data)}")
    print(f"   Volume range: {ohlcv_data['base']['volume'].min():.0f} - {ohlcv_data['base']['volume'].max():.0f}")
    
    try:
        # Calculate volume indicators
        print(f"\n3. Calculating Volume Indicators...")
        result = await volume_indicator.calculate(test_data)
        
        print(f"\n4. Volume Indicators Results:")
        print(f"   Final Score: {result.get('score', 'N/A'):.2f}")
        print(f"   Signal: {result.get('signal', 'N/A')}")
        
        # Component scores
        components = result.get('components', {})
        print(f"\n5. Component Breakdown:")
        for component, score in components.items():
            weight = volume_indicator.component_weights.get(component, 0)
            contribution = score * weight
            print(f"   {component:15s}: {score:6.2f} (weight: {weight:.3f}, contribution: {contribution:.2f})")
        
        # Verify volume_profile and vwap are calculated
        assert 'volume_profile' in components, "volume_profile score missing"
        assert 'vwap' in components, "vwap score missing"
        
        print(f"\n✅ Volume Indicators test with real data PASSED")
        return True, result
        
    except Exception as e:
        print(f"\n❌ Volume Indicators test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

async def test_price_structure_indicators_real_data():
    """Test PriceStructureIndicators with realistic market data"""
    print("\n" + "="*70)
    print("TESTING PRICE STRUCTURE INDICATORS WITH REALISTIC DATA")
    print("="*70)
    
    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create logger
    logger = Logger('test_price_real')
    
    # Create PriceStructureIndicators instance
    price_indicator = PriceStructureIndicators(config, logger)
    
    print(f"\n1. Price Structure Indicator Configuration:")
    print(f"   Components: {list(price_indicator.component_weights.keys())}")
    print(f"   Total weight: {sum(price_indicator.component_weights.values()):.4f}")
    
    # Create realistic market data
    base_ohlcv = create_realistic_ohlcv_data(periods=500, symbol="BTCUSDT")
    trades_data = create_realistic_trades_data(periods=300, base_price=base_ohlcv['close'].iloc[0])
    
    # Create multi-timeframe data
    ohlcv_data = create_multi_timeframe_data(base_ohlcv)
    
    # Test data structure
    test_data = {
        'ticker': 'BTCUSDT',
        'timeframe': 'base',
        'ohlcv': ohlcv_data,
        'trades': trades_data
    }
    
    print(f"\n2. Market Data Summary:")
    print(f"   Symbol: BTCUSDT")
    print(f"   Base timeframe: {len(ohlcv_data['base'])} candles")
    print(f"   Price range: ${ohlcv_data['base']['low'].min():.2f} - ${ohlcv_data['base']['high'].max():.2f}")
    print(f"   Current price: ${ohlcv_data['base']['close'].iloc[-1]:.2f}")
    
    try:
        # Calculate price structure indicators
        print(f"\n3. Calculating Price Structure Indicators...")
        result = await price_indicator.calculate(test_data)
        
        print(f"\n4. Price Structure Indicators Results:")
        print(f"   Final Score: {result.get('score', 'N/A'):.2f}")
        print(f"   Signal: {result.get('signal', 'N/A')}")
        
        # Component scores
        components = result.get('components', {})
        print(f"\n5. Component Breakdown:")
        for component, score in components.items():
            weight = price_indicator.component_weights.get(component, 0)
            contribution = score * weight
            print(f"   {component:18s}: {score:6.2f} (weight: {weight:.3f}, contribution: {contribution:.2f})")
        
        # Verify volume_profile and vwap are NOT calculated
        assert 'volume_profile' not in components, "volume_profile should not be in price structure components"
        assert 'vwap' not in components, "vwap should not be in price structure components"
        
        print(f"\n✅ Price Structure Indicators test with real data PASSED")
        return True, result
        
    except Exception as e:
        print(f"\n❌ Price Structure Indicators test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

async def compare_results(volume_result, price_result):
    """Compare and analyze the results from both indicators"""
    print("\n" + "="*70)
    print("COMPARATIVE ANALYSIS")
    print("="*70)
    
    if volume_result and price_result:
        vol_score = volume_result.get('score', 0)
        price_score = price_result.get('score', 0)
        
        print(f"\n1. Score Comparison:")
        print(f"   Volume Indicators Score:        {vol_score:.2f}")
        print(f"   Price Structure Score:          {price_score:.2f}")
        print(f"   Difference:                     {abs(vol_score - price_score):.2f}")
        
        print(f"\n2. Signal Analysis:")
        vol_signal = volume_result.get('signal', 'NEUTRAL')
        price_signal = price_result.get('signal', 'NEUTRAL')
        print(f"   Volume Signal:                  {vol_signal}")
        print(f"   Price Structure Signal:         {price_signal}")
        
        if vol_signal == price_signal:
            print(f"   ✅ Signals are ALIGNED")
        else:
            print(f"   ⚠️  Signals are DIVERGENT")
        
        print(f"\n3. Component Count Verification:")
        vol_components = len(volume_result.get('components', {}))
        price_components = len(price_result.get('components', {}))
        print(f"   Volume components calculated:   {vol_components}")
        print(f"   Price components calculated:    {price_components}")
        
        # Check for migrated components
        vol_comps = set(volume_result.get('components', {}).keys())
        price_comps = set(price_result.get('components', {}).keys())
        
        print(f"\n4. Migration Verification:")
        if 'volume_profile' in vol_comps:
            print(f"   ✅ volume_profile found in Volume Indicators")
        else:
            print(f"   ❌ volume_profile missing from Volume Indicators")
            
        if 'vwap' in vol_comps:
            print(f"   ✅ vwap found in Volume Indicators")
        else:
            print(f"   ❌ vwap missing from Volume Indicators")
            
        if 'volume_profile' not in price_comps:
            print(f"   ✅ volume_profile correctly removed from Price Structure")
        else:
            print(f"   ❌ volume_profile still in Price Structure")
            
        if 'vwap' not in price_comps:
            print(f"   ✅ vwap correctly removed from Price Structure")
        else:
            print(f"   ❌ vwap still in Price Structure")

async def main():
    """Run comprehensive real data tests"""
    print("REAL DATA MIGRATION VERIFICATION TESTS")
    print("="*80)
    print("Testing both indicators with realistic market data to verify migration success")
    
    # Run tests
    volume_success, volume_result = await test_volume_indicators_real_data()
    price_success, price_result = await test_price_structure_indicators_real_data()
    
    # Compare results
    if volume_success and price_success:
        await compare_results(volume_result, price_result)
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL TEST SUMMARY")
    print("="*80)
    
    tests = [
        ("Volume Indicators (Real Data)", volume_success),
        ("Price Structure Indicators (Real Data)", price_success)
    ]
    
    passed = sum(1 for _, success in tests if success)
    
    for test_name, success in tests:
        status = "PASSED" if success else "FAILED"
        icon = "✅" if success else "❌"
        print(f"{icon} {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 ALL REAL DATA TESTS PASSED - Migration working perfectly with realistic data!")
    else:
        print("⚠️  Some tests failed - Migration needs attention")

if __name__ == "__main__":
    asyncio.run(main()) 