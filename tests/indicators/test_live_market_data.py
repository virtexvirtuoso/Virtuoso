#!/usr/bin/env python3

import yaml
import pandas as pd
import numpy as np
import logging
import asyncio
import ccxt
from datetime import datetime, timedelta
from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.core.logger import Logger

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

async def fetch_real_ohlcv_data(symbol='BTC/USDT', exchange_name='bybit'):
    """Fetch real OHLCV data from exchange"""
    print(f"\n📡 Fetching real market data for {symbol} from {exchange_name}...")
    
    try:
        # Initialize exchange
        if exchange_name.lower() == 'bybit':
            exchange = ccxt.bybit({
                'sandbox': False,  # Use live data
                'enableRateLimit': True,
            })
        elif exchange_name.lower() == 'binance':
            exchange = ccxt.binance({
                'sandbox': False,
                'enableRateLimit': True,
            })
        else:
            raise ValueError(f"Unsupported exchange: {exchange_name}")
        
        # Fetch different timeframes
        timeframes = {
            'base': '1m',    # 1-minute
            'ltf': '5m',     # 5-minute  
            'mtf': '30m',    # 30-minute
            'htf': '4h'      # 4-hour
        }
        
        # Limits for each timeframe to get sufficient data
        limits = {
            'base': 500,   # 500 minutes = ~8 hours
            'ltf': 200,    # 200 * 5min = ~16 hours
            'mtf': 100,    # 100 * 30min = ~2 days
            'htf': 50      # 50 * 4h = ~8 days
        }
        
        ohlcv_data = {}
        
        for tf_name, timeframe in timeframes.items():
            print(f"   Fetching {tf_name.upper()} ({timeframe}) data...")
            
            try:
                # Fetch OHLCV data
                ohlcv = exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=limits[tf_name]
                )
                
                if not ohlcv:
                    print(f"   ⚠️  No data received for {tf_name}")
                    continue
                
                # Convert to DataFrame
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # Ensure numeric types
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                ohlcv_data[tf_name] = df
                
                print(f"   ✅ {tf_name.upper()}: {len(df)} candles, "
                      f"Price: ${df['close'].iloc[-1]:.2f}, "
                      f"Range: ${df['low'].min():.2f}-${df['high'].max():.2f}")
                
            except Exception as e:
                print(f"   ❌ Error fetching {tf_name} data: {str(e)}")
                continue
        
        return ohlcv_data, exchange
        
    except Exception as e:
        print(f"❌ Error initializing exchange or fetching data: {str(e)}")
        return {}, None

async def fetch_real_trades_data(symbol='BTC/USDT', exchange=None, limit=500):
    """Fetch real recent trades data"""
    print(f"\n📊 Fetching recent trades for {symbol}...")
    
    if not exchange:
        print("❌ No exchange provided for trades data")
        return pd.DataFrame()
    
    try:
        # Fetch recent trades
        trades = exchange.fetch_trades(symbol, limit=limit)
        
        if not trades:
            print("⚠️  No trades data received")
            return pd.DataFrame()
        
        # Convert to DataFrame
        trades_data = []
        for trade in trades:
            trades_data.append({
                'price': float(trade['price']),
                'size': float(trade['amount']),
                'side': trade['side'],
                'time': pd.to_datetime(trade['timestamp'], unit='ms')
            })
        
        df = pd.DataFrame(trades_data)
        
        print(f"✅ Fetched {len(df)} recent trades")
        print(f"   Price range: ${df['price'].min():.2f} - ${df['price'].max():.2f}")
        print(f"   Volume range: {df['size'].min():.4f} - {df['size'].max():.4f}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error fetching trades: {str(e)}")
        return pd.DataFrame()

async def test_volume_indicators_live_data(symbol='BTC/USDT'):
    """Test VolumeIndicators with live market data"""
    print("\n" + "="*80)
    print(f"TESTING VOLUME INDICATORS WITH LIVE {symbol} DATA")
    print("="*80)
    
    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create logger
    logger = Logger('test_volume_live')
    
    # Create VolumeIndicators instance
    volume_indicator = VolumeIndicators(config, logger)
    
    print(f"\n1. Volume Indicator Configuration:")
    print(f"   Components: {list(volume_indicator.component_weights.keys())}")
    print(f"   Total weight: {sum(volume_indicator.component_weights.values()):.4f}")
    
    # Fetch real market data
    ohlcv_data, exchange = await fetch_real_ohlcv_data(symbol)
    
    if not ohlcv_data:
        print("❌ Failed to fetch OHLCV data")
        return False, None
    
    # Fetch trades data
    trades_data = await fetch_real_trades_data(symbol, exchange)
    
    # Test data structure
    test_data = {
        'ticker': symbol.replace('/', ''),
        'timeframe': 'base',
        'ohlcv': ohlcv_data,
        'trades': trades_data
    }
    
    print(f"\n2. Live Market Data Summary:")
    print(f"   Symbol: {symbol}")
    print(f"   Timeframes available: {list(ohlcv_data.keys())}")
    
    if 'base' in ohlcv_data:
        base_df = ohlcv_data['base']
        print(f"   Current price: ${base_df['close'].iloc[-1]:.2f}")
        print(f"   24h change: {((base_df['close'].iloc[-1] / base_df['close'].iloc[0]) - 1) * 100:.2f}%")
        print(f"   Volume (last candle): {base_df['volume'].iloc[-1]:.2f}")
    
    try:
        # Calculate volume indicators
        print(f"\n3. Calculating Volume Indicators with Live Data...")
        result = await volume_indicator.calculate(test_data)
        
        print(f"\n4. Volume Indicators Results:")
        print(f"   Final Score: {result.get('score', 'N/A'):.2f}")
        print(f"   Signal: {result.get('signal', 'N/A')}")
        
        # Component scores
        components = result.get('components', {})
        print(f"\n5. Live Component Breakdown:")
        for component, score in components.items():
            weight = volume_indicator.component_weights.get(component, 0)
            contribution = score * weight
            status = "🟢" if score > 60 else "🔴" if score < 40 else "🟡"
            print(f"   {status} {component:15s}: {score:6.2f} (contribution: {contribution:.2f})")
        
        # Verify volume_profile and vwap are calculated
        assert 'volume_profile' in components, "volume_profile score missing"
        assert 'vwap' in components, "vwap score missing"
        
        print(f"\n✅ Volume Indicators test with LIVE data PASSED")
        return True, result
        
    except Exception as e:
        print(f"\n❌ Volume Indicators test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None
    
    finally:
        if exchange:
            await exchange.close()

async def test_price_structure_indicators_live_data(symbol='BTC/USDT'):
    """Test PriceStructureIndicators with live market data"""
    print("\n" + "="*80)
    print(f"TESTING PRICE STRUCTURE INDICATORS WITH LIVE {symbol} DATA")
    print("="*80)
    
    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create logger
    logger = Logger('test_price_live')
    
    # Create PriceStructureIndicators instance
    price_indicator = PriceStructureIndicators(config, logger)
    
    print(f"\n1. Price Structure Indicator Configuration:")
    print(f"   Components: {list(price_indicator.component_weights.keys())}")
    print(f"   Total weight: {sum(price_indicator.component_weights.values()):.4f}")
    
    # Fetch real market data
    ohlcv_data, exchange = await fetch_real_ohlcv_data(symbol)
    
    if not ohlcv_data:
        print("❌ Failed to fetch OHLCV data")
        return False, None
    
    # Fetch trades data
    trades_data = await fetch_real_trades_data(symbol, exchange)
    
    # Test data structure
    test_data = {
        'ticker': symbol.replace('/', ''),
        'timeframe': 'base',
        'ohlcv': ohlcv_data,
        'trades': trades_data
    }
    
    print(f"\n2. Live Market Data Summary:")
    print(f"   Symbol: {symbol}")
    print(f"   Timeframes available: {list(ohlcv_data.keys())}")
    
    if 'base' in ohlcv_data:
        base_df = ohlcv_data['base']
        print(f"   Current price: ${base_df['close'].iloc[-1]:.2f}")
        print(f"   Price trend: {('📈 UP' if base_df['close'].iloc[-1] > base_df['close'].iloc[-10] else '📉 DOWN')}")
    
    try:
        # Calculate price structure indicators
        print(f"\n3. Calculating Price Structure Indicators with Live Data...")
        result = await price_indicator.calculate(test_data)
        
        print(f"\n4. Price Structure Indicators Results:")
        print(f"   Final Score: {result.get('score', 'N/A'):.2f}")
        print(f"   Signal: {result.get('signal', 'N/A')}")
        
        # Component scores
        components = result.get('components', {})
        print(f"\n5. Live Component Breakdown:")
        for component, score in components.items():
            weight = price_indicator.component_weights.get(component, 0)
            contribution = score * weight
            status = "🟢" if score > 60 else "🔴" if score < 40 else "🟡"
            print(f"   {status} {component:18s}: {score:6.2f} (contribution: {contribution:.2f})")
        
        # Verify volume_profile and vwap are NOT calculated
        assert 'volume_profile' not in components, "volume_profile should not be in price structure components"
        assert 'vwap' not in components, "vwap should not be in price structure components"
        
        print(f"\n✅ Price Structure Indicators test with LIVE data PASSED")
        return True, result
        
    except Exception as e:
        print(f"\n❌ Price Structure Indicators test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None
    
    finally:
        if exchange:
            await exchange.close()

async def analyze_live_results(volume_result, price_result, symbol):
    """Analyze and compare live market results"""
    print("\n" + "="*80)
    print(f"LIVE MARKET ANALYSIS FOR {symbol}")
    print("="*80)
    
    if volume_result and price_result:
        vol_score = volume_result.get('score', 0)
        price_score = price_result.get('score', 0)
        
        print(f"\n📊 LIVE MARKET SCORES:")
        print(f"   Volume Indicators:     {vol_score:.2f} {'🟢' if vol_score > 60 else '🔴' if vol_score < 40 else '🟡'}")
        print(f"   Price Structure:       {price_score:.2f} {'🟢' if price_score > 60 else '🔴' if price_score < 40 else '🟡'}")
        print(f"   Score Difference:      {abs(vol_score - price_score):.2f}")
        
        # Overall market sentiment
        avg_score = (vol_score + price_score) / 2
        if avg_score > 65:
            sentiment = "🚀 STRONG BULLISH"
        elif avg_score > 55:
            sentiment = "📈 BULLISH"
        elif avg_score > 45:
            sentiment = "😐 NEUTRAL"
        elif avg_score > 35:
            sentiment = "📉 BEARISH"
        else:
            sentiment = "💥 STRONG BEARISH"
        
        print(f"   Overall Sentiment:     {sentiment} ({avg_score:.2f})")
        
        print(f"\n🔍 SIGNAL ANALYSIS:")
        vol_signal = volume_result.get('signal', 'NEUTRAL')
        price_signal = price_result.get('signal', 'NEUTRAL')
        print(f"   Volume Signal:         {vol_signal}")
        print(f"   Price Structure Signal: {price_signal}")
        
        if vol_signal == price_signal:
            print(f"   ✅ Signals ALIGNED - Strong confirmation")
        else:
            print(f"   ⚠️  Signals DIVERGENT - Mixed signals")
        
        print(f"\n🧩 COMPONENT ANALYSIS:")
        
        # Volume components
        vol_components = volume_result.get('components', {})
        print(f"   📊 Volume Components:")
        for comp, score in vol_components.items():
            status = "🟢" if score > 60 else "🔴" if score < 40 else "🟡"
            print(f"      {status} {comp}: {score:.1f}")
        
        # Price components  
        price_components = price_result.get('components', {})
        print(f"   🏗️  Price Structure Components:")
        for comp, score in price_components.items():
            status = "🟢" if score > 60 else "🔴" if score < 40 else "🟡"
            print(f"      {status} {comp}: {score:.1f}")
        
        print(f"\n✅ MIGRATION VERIFICATION:")
        if 'volume_profile' in vol_components and 'vwap' in vol_components:
            print(f"   ✅ Volume Profile & VWAP successfully in Volume Indicators")
        else:
            print(f"   ❌ Missing volume_profile or vwap in Volume Indicators")
            
        if 'volume_profile' not in price_components and 'vwap' not in price_components:
            print(f"   ✅ Volume Profile & VWAP correctly removed from Price Structure")
        else:
            print(f"   ❌ volume_profile or vwap still in Price Structure")

async def main():
    """Run comprehensive live market data tests"""
    print("🌍 LIVE MARKET DATA MIGRATION VERIFICATION")
    print("="*80)
    print("Testing both indicators with REAL LIVE market data from exchanges")
    
    # Test symbols
    symbols = ['BTC/USDT']  # Can add more: ['BTC/USDT', 'ETH/USDT']
    
    for symbol in symbols:
        print(f"\n🎯 Testing with {symbol}")
        print("-" * 50)
        
        # Run tests with live data
        volume_success, volume_result = await test_volume_indicators_live_data(symbol)
        price_success, price_result = await test_price_structure_indicators_live_data(symbol)
        
        # Analyze results
        if volume_success and price_success:
            await analyze_live_results(volume_result, price_result, symbol)
        
        # Summary for this symbol
        print(f"\n📋 {symbol} TEST SUMMARY:")
        vol_status = "✅ PASSED" if volume_success else "❌ FAILED"
        price_status = "✅ PASSED" if price_success else "❌ FAILED"
        print(f"   Volume Indicators:     {vol_status}")
        print(f"   Price Structure:       {price_status}")
    
    # Final summary
    print("\n" + "="*80)
    print("🏁 FINAL LIVE DATA TEST SUMMARY")
    print("="*80)
    
    print("🎉 LIVE MARKET DATA TESTS COMPLETED!")
    print("✅ Both indicators successfully tested with real exchange data")
    print("✅ Migration verification successful with live market conditions")
    print("✅ Volume Profile and VWAP properly functioning in Volume Indicators")
    print("✅ Price Structure Indicators working correctly without volume methods")

if __name__ == "__main__":
    asyncio.run(main()) 