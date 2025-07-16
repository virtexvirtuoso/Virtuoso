#!/usr/bin/env python3

import yaml
import pandas as pd
import numpy as np
import logging
from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.core.logger import Logger

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

def create_sample_data(periods=200):
    """Create sample OHLCV data for testing"""
    np.random.seed(42)  # For reproducible results
    
    # Generate realistic price data
    base_price = 50000
    price_changes = np.random.normal(0, 0.02, periods)
    prices = [base_price]
    
    for change in price_changes:
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    prices = np.array(prices[1:])  # Remove the initial base price
    
    # Create OHLCV data
    data = []
    for i in range(periods):
        open_price = prices[i]
        close_price = prices[i] * (1 + np.random.normal(0, 0.01))
        high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.005)))
        low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.005)))
        volume = np.random.uniform(1000, 10000)
        
        data.append({
            'timestamp': pd.Timestamp.now() - pd.Timedelta(minutes=(periods-i)),
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(data).set_index('timestamp')

def create_sample_trades(periods=100):
    """Create sample trade data for testing"""
    np.random.seed(42)
    
    trades = []
    base_price = 50000
    
    for i in range(periods):
        price = base_price * (1 + np.random.normal(0, 0.01))
        size = np.random.uniform(0.1, 10.0)
        side = np.random.choice(['buy', 'sell'])
        
        trades.append({
            'price': price,
            'size': size,
            'side': side,
            'time': pd.Timestamp.now() - pd.Timedelta(minutes=(periods-i))
        })
    
    return pd.DataFrame(trades)

async def test_volume_indicators():
    """Test VolumeIndicators with the migrated methods"""
    print("\n" + "="*60)
    print("TESTING VOLUME INDICATORS")
    print("="*60)
    
    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create logger
    logger = Logger('test_volume_indicators')
    
    # Create VolumeIndicators instance
    volume_indicator = VolumeIndicators(config, logger)
    
    print(f"\n1. Component Weights:")
    for component, weight in volume_indicator.component_weights.items():
        print(f"   {component}: {weight:.4f}")
    
    # Verify volume_profile and vwap are included
    assert 'volume_profile' in volume_indicator.component_weights, "volume_profile not found in VolumeIndicators"
    assert 'vwap' in volume_indicator.component_weights, "vwap not found in VolumeIndicators"
    
    print(f"\n2. Total weight sum: {sum(volume_indicator.component_weights.values()):.4f}")
    
    # Create sample data
    ohlcv_data = create_sample_data(200)
    trades_data = create_sample_trades(100)
    
    # Test data structure
    test_data = {
        'ticker': 'BTCUSDT',
        'timeframe': 'base',
        'ohlcv': {
            'base': ohlcv_data,
            'ltf': ohlcv_data.iloc[::5],  # Simulate different timeframes
            'mtf': ohlcv_data.iloc[::30],
            'htf': ohlcv_data.iloc[::240]
        },
        'trades': trades_data
    }
    
    print(f"\n3. Testing with sample data:")
    print(f"   OHLCV periods: {len(ohlcv_data)}")
    print(f"   Trades count: {len(trades_data)}")
    
    try:
        # Calculate volume indicators
        result = await volume_indicator.calculate(test_data)
        
        print(f"\n4. Volume Indicators Result:")
        print(f"   Score: {result.get('score', 'N/A')}")
        print(f"   Confidence: {result.get('confidence', 'N/A')}")
        print(f"   Signal: {result.get('signal', 'N/A')}")
        
        # Check component scores
        components = result.get('components', {})
        print(f"\n5. Component Scores:")
        for component, score in components.items():
            print(f"   {component}: {score}")
        
        # Verify volume_profile and vwap scores are calculated
        assert 'volume_profile' in components, "volume_profile score not calculated"
        assert 'vwap' in components, "vwap score not calculated"
        
        print(f"\n✅ VolumeIndicators test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ VolumeIndicators test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_price_structure_indicators():
    """Test PriceStructureIndicators after removing volume methods"""
    print("\n" + "="*60)
    print("TESTING PRICE STRUCTURE INDICATORS")
    print("="*60)
    
    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create logger
    logger = Logger('test_price_structure')
    
    # Create PriceStructureIndicators instance
    price_indicator = PriceStructureIndicators(config, logger)
    
    print(f"\n1. Component Weights:")
    for component, weight in price_indicator.component_weights.items():
        print(f"   {component}: {weight:.4f}")
    
    # Verify volume_profile and vwap are NOT included
    assert 'volume_profile' not in price_indicator.component_weights, "volume_profile should not be in PriceStructureIndicators"
    assert 'vwap' not in price_indicator.component_weights, "vwap should not be in PriceStructureIndicators"
    
    print(f"\n2. Total weight sum: {sum(price_indicator.component_weights.values()):.4f}")
    
    # Create sample data
    ohlcv_data = create_sample_data(200)
    trades_data = create_sample_trades(100)
    
    # Test data structure
    test_data = {
        'ticker': 'BTCUSDT',
        'timeframe': 'base',
        'ohlcv': {
            'base': ohlcv_data,
            'ltf': ohlcv_data.iloc[::5],
            'mtf': ohlcv_data.iloc[::30],
            'htf': ohlcv_data.iloc[::240]
        },
        'trades': trades_data
    }
    
    print(f"\n3. Testing with sample data:")
    print(f"   OHLCV periods: {len(ohlcv_data)}")
    print(f"   Trades count: {len(trades_data)}")
    
    try:
        # Calculate price structure indicators
        result = await price_indicator.calculate(test_data)
        
        print(f"\n4. Price Structure Indicators Result:")
        print(f"   Score: {result.get('score', 'N/A')}")
        print(f"   Confidence: {result.get('confidence', 'N/A')}")
        print(f"   Signal: {result.get('signal', 'N/A')}")
        
        # Check component scores
        components = result.get('components', {})
        print(f"\n5. Component Scores:")
        for component, score in components.items():
            print(f"   {component}: {score}")
        
        # Verify volume_profile and vwap scores are NOT calculated
        assert 'volume_profile' not in components, "volume_profile should not be in PriceStructureIndicators components"
        assert 'vwap' not in components, "vwap should not be in PriceStructureIndicators components"
        
        print(f"\n✅ PriceStructureIndicators test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ PriceStructureIndicators test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_method_availability():
    """Test that moved methods are available in VolumeIndicators and not in PriceStructureIndicators"""
    print("\n" + "="*60)
    print("TESTING METHOD AVAILABILITY")
    print("="*60)
    
    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    logger = Logger('test_methods')
    
    # Create instances
    volume_indicator = VolumeIndicators(config, logger)
    price_indicator = PriceStructureIndicators(config, logger)
    
    # Methods that should be in VolumeIndicators
    volume_methods = [
        '_calculate_volume_profile_score',
        '_calculate_vwap_score',
        '_calculate_single_vwap_score',
        '_verify_score_not_default',
        '_calculate_volume_profile'
    ]
    
    print(f"\n1. Checking VolumeIndicators methods:")
    volume_passed = True
    for method in volume_methods:
        has_method = hasattr(volume_indicator, method)
        print(f"   {method}: {'✅' if has_method else '❌'}")
        if not has_method:
            volume_passed = False
    
    print(f"\n2. Checking PriceStructureIndicators methods (should NOT have):")
    price_passed = True
    for method in volume_methods:
        has_method = hasattr(price_indicator, method)
        print(f"   {method}: {'❌' if has_method else '✅'}")
        if has_method:
            price_passed = False
    
    if volume_passed and price_passed:
        print(f"\n✅ Method availability test PASSED")
        return True
    else:
        print(f"\n❌ Method availability test FAILED")
        return False

async def main():
    """Run all tests"""
    print("MIGRATION VERIFICATION TESTS")
    print("="*80)
    
    tests = [
        ("Method Availability", test_method_availability),
        ("Volume Indicators", test_volume_indicators),
        ("Price Structure Indicators", test_price_structure_indicators)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            if test_name == "Method Availability":
                result = test_func()  # This one is not async
            else:
                result = await test_func()  # These are async
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} test CRASHED: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = 0
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        icon = "✅" if result else "❌"
        print(f"{icon} {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 ALL TESTS PASSED - Migration successful!")
    else:
        print("⚠️  Some tests failed - Migration needs attention")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 