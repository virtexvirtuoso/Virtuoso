#!/usr/bin/env python3

import asyncio
import pandas as pd
import numpy as np
import logging
import sys
import os
from datetime import datetime, timedelta
import yaml

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.core.logger import Logger

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

def generate_comprehensive_market_data(num_candles=500):
    """Generate comprehensive market data for testing both indicators"""
    print(f"📊 Generating {num_candles} candles of comprehensive market data...")
    
    # Start with realistic BTC price
    base_price = 45000.0
    current_price = base_price
    
    # Generate realistic OHLCV data
    ohlcv_data = []
    trades_data = []
    
    for i in range(num_candles):
        # Create realistic price movement
        volatility = np.random.normal(0, 0.02)  # 2% volatility
        price_change = current_price * volatility
        
        # OHLC with realistic patterns
        open_price = current_price
        high_price = open_price + abs(price_change) + np.random.uniform(0, open_price * 0.005)
        low_price = open_price - abs(price_change) - np.random.uniform(0, open_price * 0.005)
        close_price = open_price + price_change
        
        # Ensure OHLC logic
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
        # Volume with realistic patterns
        base_volume = np.random.uniform(50, 200)
        if abs(price_change) > current_price * 0.01:  # High volatility = high volume
            volume = base_volume * np.random.uniform(1.5, 3.0)
        else:
            volume = base_volume * np.random.uniform(0.5, 1.5)
        
        timestamp = datetime.now() - timedelta(minutes=num_candles-i)
        
        ohlcv_data.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
        
        # Generate trades for this candle
        num_trades = np.random.randint(5, 20)
        for j in range(num_trades):
            trade_price = np.random.uniform(low_price, high_price)
            trade_size = np.random.uniform(0.001, 0.1)
            trade_side = 'buy' if np.random.random() > 0.5 else 'sell'
            
            trades_data.append({
                'price': trade_price,
                'size': trade_size,
                'side': trade_side,
                'time': timestamp + timedelta(seconds=j*3)
            })
        
        current_price = close_price
    
    # Convert to DataFrames
    ohlcv_df = pd.DataFrame(ohlcv_data)
    trades_df = pd.DataFrame(trades_data)
    
    print(f"✅ Generated OHLCV: {len(ohlcv_df)} candles")
    print(f"✅ Generated Trades: {len(trades_df)} trades")
    print(f"   Price range: ${ohlcv_df['low'].min():.2f} - ${ohlcv_df['high'].max():.2f}")
    print(f"   Volume range: {ohlcv_df['volume'].min():.2f} - {ohlcv_df['volume'].max():.2f}")
    
    return ohlcv_df, trades_df

def create_market_data_structure(ohlcv_df, trades_df):
    """Create the market data structure expected by both indicators"""
    
    # Get current price for ticker
    current_price = ohlcv_df['close'].iloc[-1]
    
    # Create timeframe data (using same data for all timeframes for simplicity)
    market_data = {
        'symbol': 'BTC/USDT',
        'ohlcv': {
            'base': ohlcv_df.copy(),
            'ltf': ohlcv_df.iloc[::5].copy(),  # Every 5th candle for LTF
            'mtf': ohlcv_df.iloc[::30].copy(), # Every 30th candle for MTF  
            'htf': ohlcv_df.iloc[::120].copy() # Every 120th candle for HTF
        },
        'trades': trades_df.copy(),
        'processed_trades': trades_df.copy(),
        'orderbook': {
            'asks': [[current_price + 100, 1.0], [current_price + 200, 2.0]],
            'bids': [[current_price - 100, 1.5], [current_price - 200, 2.5]],
            'timestamp': datetime.now().timestamp()
        },
        'ticker': {
            'last': current_price,
            'volume': ohlcv_df['volume'].sum(),
            'high': ohlcv_df['high'].max(),
            'low': ohlcv_df['low'].min(),
            'change': ((current_price - ohlcv_df['open'].iloc[0]) / ohlcv_df['open'].iloc[0]) * 100
        },
        'sentiment': {
            'funding_rate': 0.0001,  # 0.01% funding rate
            'long_short_ratio': 1.2,  # Slightly more longs
            'liquidations': [
                {'side': 'long', 'amount': 1000000, 'price': current_price - 500},
                {'side': 'short', 'amount': 800000, 'price': current_price + 300}
            ]
        },
        'timeframe': 'base'  # Current timeframe being analyzed
    }
    
    return market_data

async def test_volume_indicators(market_data):
    """Test volume indicators with market data"""
    print("\n🔵 TESTING VOLUME INDICATORS")
    print("=" * 50)
    
    # Create logger
    logger = Logger('test_volume_indicators')
    
    # Load volume indicators config
    config = {
        'volume_indicators': {
            'enabled': True,
            'weights': {
                'volume_delta': 0.20,
                'adl': 0.15,
                'cmf': 0.15,
                'relative_volume': 0.15,
                'obv': 0.15,
                'volume_profile': 0.10,
                'vwap': 0.10
            },
            'volume_profile': {
                'bins': 100,
                'value_area_percentage': 70.0
            },
            'vwap': {
                'std_bands': True,
                'debug_logging': False,
                'timeframe_weights': {
                    'daily': 0.6,
                    'weekly': 0.4
                }
            }
        },
        'timeframes': {
            'base': {
                'weight': 0.4, 
                'interval': 1,
                'validation': {'min_candles': 50}
            },
            'ltf': {
                'weight': 0.3, 
                'interval': 5,
                'validation': {'min_candles': 20}
            },
            'mtf': {
                'weight': 0.2, 
                'interval': 30,
                'validation': {'min_candles': 10}
            },
            'htf': {
                'weight': 0.1, 
                'interval': 240,
                'validation': {'min_candles': 5}
            }
        },
        'validation_requirements': {
            'trades': {
                'min_trades': 10,
                'max_age': 3600
            },
            'orderbook': {
                'min_levels': 5
            }
        }
    }
    
    try:
        # Create volume indicators
        volume_indicators = VolumeIndicators(config, logger)
        
        # Calculate indicators
        result = await volume_indicators.calculate(market_data)
        
        print(f"✅ Volume Indicators Calculation: SUCCESS")
        print(f"   Final Score: {result['score']:.2f}")
        print(f"   Components calculated: {len(result['components'])}")
        
        # Display component breakdown
        print("\n📊 Volume Component Breakdown:")
        for component, score in result['components'].items():
            status = "🟢" if score > 60 else "🟡" if score > 40 else "🔴"
            print(f"   {status} {component:15}: {score:6.2f}")
        
        # Verify no default scores
        default_scores = [comp for comp, score in result['components'].items() if abs(score - 50.0) < 0.01]
        if default_scores:
            print(f"⚠️  Components with potential default scores: {default_scores}")
        else:
            print("✅ No default scores detected - all components calculated properly")
        
        return True, result
        
    except Exception as e:
        print(f"❌ Volume Indicators Calculation: FAILED")
        print(f"   Error: {str(e)}")
        return False, None

async def test_price_structure_indicators(market_data):
    """Test price structure indicators with market data"""
    print("\n🟠 TESTING PRICE STRUCTURE INDICATORS")
    print("=" * 50)
    
    # Create logger
    logger = Logger('test_price_structure_indicators')
    
    # Load price structure indicators config
    config = {
        'price_structure_indicators': {
            'enabled': True,
            'weights': {
                'support_resistance': 0.1667,
                'order_blocks': 0.1667,
                'trend_position': 0.1667,
                'volume_profile': 0.1667,
                'market_structure': 0.1667,
                'range_analysis': 0.1667
            }
        },
        'timeframes': {
            'base': {
                'weight': 0.4, 
                'interval': 1,
                'validation': {'min_candles': 50}
            },
            'ltf': {
                'weight': 0.3, 
                'interval': 5,
                'validation': {'min_candles': 20}
            },
            'mtf': {
                'weight': 0.2, 
                'interval': 30,
                'validation': {'min_candles': 10}
            },
            'htf': {
                'weight': 0.1, 
                'interval': 240,
                'validation': {'min_candles': 5}
            }
        },
        'validation_requirements': {
            'trades': {
                'min_trades': 10,
                'max_age': 3600
            },
            'orderbook': {
                'min_levels': 5
            }
        }
    }
    
    try:
        # Create price structure indicators
        price_indicators = PriceStructureIndicators(config, logger)
        
        # Calculate indicators
        result = await price_indicators.calculate(market_data)
        
        print(f"✅ Price Structure Indicators Calculation: SUCCESS")
        print(f"   Final Score: {result['score']:.2f}")
        print(f"   Components calculated: {len(result['components'])}")
        
        # Display component breakdown
        print("\n📊 Price Structure Component Breakdown:")
        for component, score in result['components'].items():
            status = "🟢" if score > 60 else "🟡" if score > 40 else "🔴"
            print(f"   {status} {component:15}: {score:6.2f}")
        
        # Verify no default scores
        default_scores = [comp for comp, score in result['components'].items() if abs(score - 50.0) < 0.01]
        if default_scores:
            print(f"⚠️  Components with potential default scores: {default_scores}")
        else:
            print("✅ No default scores detected - all components calculated properly")
        
        return True, result
        
    except Exception as e:
        print(f"❌ Price Structure Indicators Calculation: FAILED")
        print(f"   Error: {str(e)}")
        return False, None

def verify_migration_success(volume_result, price_result):
    """Verify that the migration was successful"""
    print("\n🔍 MIGRATION VERIFICATION")
    print("=" * 50)
    
    success = True
    
    # Check volume indicators have the moved components
    volume_components = set(volume_result['components'].keys())
    expected_volume = {'volume_delta', 'adl', 'cmf', 'relative_volume', 'obv', 'volume_profile', 'vwap'}
    
    if expected_volume.issubset(volume_components):
        print("✅ Volume indicators contain all expected components including moved ones")
    else:
        missing = expected_volume - volume_components
        print(f"❌ Volume indicators missing components: {missing}")
        success = False
    
    # Check price structure indicators don't have the moved components
    price_components = set(price_result['components'].keys())
    moved_components = {'volume_profile', 'vwap'}
    
    if moved_components.isdisjoint(price_components):
        print("✅ Price structure indicators correctly exclude moved components")
    else:
        unexpected = moved_components.intersection(price_components)
        print(f"❌ Price structure indicators still contain moved components: {unexpected}")
        success = False
    
    # Check that both indicators produce non-default scores
    volume_non_default = sum(1 for score in volume_result['components'].values() if abs(score - 50.0) > 0.1)
    price_non_default = sum(1 for score in price_result['components'].values() if abs(score - 50.0) > 0.1)
    
    print(f"📊 Volume indicators: {volume_non_default}/{len(volume_result['components'])} non-default scores")
    print(f"📊 Price structure indicators: {price_non_default}/{len(price_result['components'])} non-default scores")
    
    if volume_non_default >= 5 and price_non_default >= 5:
        print("✅ Both indicators producing real calculated scores")
    else:
        print("⚠️  Some indicators may be returning default scores")
    
    return success

async def main():
    """Main test function"""
    print("🧪 COMPREHENSIVE INTEGRATION TEST")
    print("Testing both Volume and Price Structure Indicators with same market data")
    print("=" * 80)
    
    try:
        # Generate comprehensive market data
        ohlcv_df, trades_df = generate_comprehensive_market_data(500)
        
        # Create market data structure
        market_data = create_market_data_structure(ohlcv_df, trades_df)
        
        print(f"\n📋 Market Data Summary:")
        print(f"   Symbol: {market_data['symbol']}")
        print(f"   Timeframes: {list(market_data['ohlcv'].keys())}")
        print(f"   Base candles: {len(market_data['ohlcv']['base'])}")
        print(f"   Trades: {len(market_data['trades'])}")
        
        # Test volume indicators
        volume_success, volume_result = await test_volume_indicators(market_data)
        
        # Test price structure indicators  
        price_success, price_result = await test_price_structure_indicators(market_data)
        
        # Verify migration success
        if volume_success and price_success:
            migration_success = verify_migration_success(volume_result, price_result)
        else:
            migration_success = False
        
        # Final summary
        print("\n" + "=" * 80)
        print("🎯 FINAL TEST RESULTS")
        print("=" * 80)
        
        print(f"Volume Indicators:        {'✅ PASS' if volume_success else '❌ FAIL'}")
        print(f"Price Structure Indicators: {'✅ PASS' if price_success else '❌ FAIL'}")
        print(f"Migration Verification:   {'✅ PASS' if migration_success else '❌ FAIL'}")
        
        overall_success = volume_success and price_success and migration_success
        print(f"\nOVERALL TEST:            {'✅ SUCCESS' if overall_success else '❌ FAILURE'}")
        
        if overall_success:
            print("\n🎉 All tests passed! Both indicators work correctly with the same market data.")
            print("   The migration of volume_profile and vwap was successful!")
        else:
            print("\n⚠️  Some tests failed. Please review the output above.")
        
        return overall_success
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1) 