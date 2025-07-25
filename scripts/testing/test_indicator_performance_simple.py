#!/usr/bin/env python3
"""
Simple test to compare indicator performance with live Bybit data
Tests available indicator versions for performance differences
"""

import asyncio
import time
import numpy as np
import pandas as pd
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.exchanges.bybit import BybitExchange
from src.indicators.technical_indicators import TechnicalIndicators
from src.indicators.technical_indicators_optimized import OptimizedTechnicalIndicators
from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.indicators.orderflow_indicators import OrderflowIndicators
import logging

# Simple logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleIndicatorTester:
    def __init__(self):
        self.exchange = BybitExchange()
        
    async def fetch_data(self, symbol: str = 'BTCUSDT', interval: str = '5', limit: int = 500) -> pd.DataFrame:
        """Fetch live kline data from Bybit"""
        logger.info(f"Fetching {limit} candles for {symbol} {interval}m")
        
        klines = await self.exchange.fetch_klines(symbol, interval, limit)
        
        # Convert to DataFrame
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df['turnover'] = df['close'] * df['volume']
        
        logger.info(f"Fetched {len(df)} candles, latest: {df.index[-1]}")
        return df
        
    def test_technical_indicators(self, df: pd.DataFrame):
        """Test technical indicators performance"""
        print("\n" + "="*60)
        print("TECHNICAL INDICATORS COMPARISON")
        print("="*60)
        
        # Test original version
        print("\nTesting Original TechnicalIndicators...")
        original = TechnicalIndicators()
        
        # RSI
        start = time.time()
        rsi_orig = original.calculate_rsi(df)
        rsi_orig_time = time.time() - start
        
        # MACD
        start = time.time()
        macd_orig = original.calculate_macd(df)
        macd_orig_time = time.time() - start
        
        # Bollinger Bands
        start = time.time()
        bb_orig = original.calculate_bollinger_bands(df)
        bb_orig_time = time.time() - start
        
        # Test optimized version
        print("\nTesting Optimized TechnicalIndicators...")
        optimized = OptimizedTechnicalIndicators()
        
        # RSI
        start = time.time()
        rsi_opt = optimized.calculate_rsi(df)
        rsi_opt_time = time.time() - start
        
        # MACD
        start = time.time()
        macd_opt = optimized.calculate_macd(df)
        macd_opt_time = time.time() - start
        
        # Bollinger Bands
        start = time.time()
        bb_opt = optimized.calculate_bollinger_bands(df)
        bb_opt_time = time.time() - start
        
        # Print results
        print("\nRESULTS:")
        print("-" * 40)
        print(f"RSI:")
        print(f"  Original: {rsi_orig_time*1000:.2f}ms")
        print(f"  Optimized: {rsi_opt_time*1000:.2f}ms")
        print(f"  Speedup: {rsi_orig_time/rsi_opt_time:.1f}x")
        
        print(f"\nMACD:")
        print(f"  Original: {macd_orig_time*1000:.2f}ms")
        print(f"  Optimized: {macd_opt_time*1000:.2f}ms")
        print(f"  Speedup: {macd_orig_time/macd_opt_time:.1f}x")
        
        print(f"\nBollinger Bands:")
        print(f"  Original: {bb_orig_time*1000:.2f}ms")
        print(f"  Optimized: {bb_opt_time*1000:.2f}ms")
        print(f"  Speedup: {bb_orig_time/bb_opt_time:.1f}x")
        
        # Check accuracy
        if 'rsi' in rsi_orig and 'rsi' in rsi_opt:
            rsi_diff = np.abs(rsi_orig['rsi'].dropna() - rsi_opt['rsi'].dropna()).mean()
            print(f"\nRSI accuracy (mean diff): {rsi_diff:.6f}")
            
    def test_volume_indicators(self, df: pd.DataFrame):
        """Test volume indicators performance"""
        print("\n" + "="*60)
        print("VOLUME INDICATORS PERFORMANCE")
        print("="*60)
        
        vol = VolumeIndicators()
        
        # OBV
        start = time.time()
        obv = vol.calculate_obv(df)
        obv_time = time.time() - start
        
        # Volume Profile
        start = time.time()
        vp = vol.calculate_volume_profile(df)
        vp_time = time.time() - start
        
        # VWAP
        start = time.time()
        vwap = vol.calculate_vwap(df)
        vwap_time = time.time() - start
        
        print("\nRESULTS:")
        print("-" * 40)
        print(f"OBV: {obv_time*1000:.2f}ms")
        print(f"Volume Profile: {vp_time*1000:.2f}ms")
        print(f"VWAP: {vwap_time*1000:.2f}ms")
        
        if 'obv' in obv and not obv['obv'].empty:
            print(f"\nOBV last value: {obv['obv'].iloc[-1]:,.0f}")
        if 'vwap' in vwap and not vwap['vwap'].empty:
            print(f"VWAP last value: ${vwap['vwap'].iloc[-1]:,.2f}")
            
    def test_price_structure(self, df: pd.DataFrame):
        """Test price structure indicators"""
        print("\n" + "="*60)
        print("PRICE STRUCTURE INDICATORS PERFORMANCE")
        print("="*60)
        
        ps = PriceStructureIndicators()
        
        # Support/Resistance
        start = time.time()
        sr = ps.identify_support_resistance(df)
        sr_time = time.time() - start
        
        # Order Blocks
        start = time.time()
        ob = ps.detect_order_blocks(df)
        ob_time = time.time() - start
        
        # Market Structure
        start = time.time()
        ms = ps.analyze_market_structure(df)
        ms_time = time.time() - start
        
        print("\nRESULTS:")
        print("-" * 40)
        print(f"Support/Resistance: {sr_time*1000:.2f}ms")
        print(f"Order Blocks: {ob_time*1000:.2f}ms")
        print(f"Market Structure: {ms_time*1000:.2f}ms")
        
        if 'levels' in sr:
            print(f"\nSupport/Resistance levels found: {len(sr['levels'])}")
        if 'order_blocks' in ob:
            print(f"Order blocks found: {len(ob['order_blocks'])}")
        if 'trend' in ms:
            print(f"Current trend: {ms['trend']}")
            
    async def test_orderflow(self, df: pd.DataFrame):
        """Test orderflow indicators"""
        print("\n" + "="*60)
        print("ORDERFLOW INDICATORS PERFORMANCE")
        print("="*60)
        
        of = OrderflowIndicators()
        
        # Note: OrderFlow requires trade data, we'll simulate it
        print("\nSimulating trade data...")
        trades = []
        for idx, row in df.iterrows():
            # Simulate 5 trades per candle
            for i in range(5):
                trades.append({
                    'timestamp': idx,
                    'price': np.random.uniform(row['low'], row['high']),
                    'size': row['volume'] / 5,
                    'side': 'buy' if np.random.random() > 0.5 else 'sell'
                })
        trades_df = pd.DataFrame(trades)
        
        # CVD
        start = time.time()
        try:
            cvd = of.calculate_cvd(trades_df)
            cvd_time = time.time() - start
            print(f"\nCVD calculation: {cvd_time*1000:.2f}ms")
        except Exception as e:
            print(f"\nCVD calculation error: {e}")
            
        # Delta Analysis
        start = time.time()
        try:
            delta = of.analyze_delta(trades_df)
            delta_time = time.time() - start
            print(f"Delta analysis: {delta_time*1000:.2f}ms")
        except Exception as e:
            print(f"Delta analysis error: {e}")

async def main():
    """Run all tests"""
    tester = SimpleIndicatorTester()
    
    try:
        # Fetch live data
        df = await tester.fetch_data('BTCUSDT', '5', 500)
        
        # Run tests
        tester.test_technical_indicators(df)
        tester.test_volume_indicators(df)
        tester.test_price_structure(df)
        await tester.test_orderflow(df)
        
        print("\n" + "="*60)
        print("TEST COMPLETE")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())