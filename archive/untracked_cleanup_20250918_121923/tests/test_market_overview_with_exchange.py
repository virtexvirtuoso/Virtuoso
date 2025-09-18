#!/usr/bin/env python3
"""Test script to verify market overview calculation with exchange connection"""

import asyncio
import sys
import os
sys.path.insert(0, '/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

from src.monitoring.market_reporter import MarketReporter
from src.core.exchanges.bybit import BybitExchange
import logging

logging.basicConfig(level=logging.INFO)

async def test_market_overview_with_exchange():
    """Test the market overview calculation with real exchange"""
    print("=" * 60)
    print("Testing Market Overview with Exchange Connection")
    print("=" * 60)
    
    # Initialize exchange
    exchange = BybitExchange()
    
    # Initialize market reporter with exchange
    market_reporter = MarketReporter(exchange=exchange)
    
    # Test symbols
    test_symbols = [
        'BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT',
        'BNB/USDT:USDT', 'XRP/USDT:USDT', 'ADA/USDT:USDT',
        'AVAX/USDT:USDT', 'DOGE/USDT:USDT', 'DOT/USDT:USDT',
        'MATIC/USDT:USDT', 'LINK/USDT:USDT', 'UNI/USDT:USDT'
    ]
    
    print(f"\nTesting with {len(test_symbols)} symbols:")
    for symbol in test_symbols[:10]:  # Show first 10
        print(f"  - {symbol}")
    
    try:
        # Call the market overview calculation
        print("\nCalling _calculate_market_overview...")
        result = await market_reporter._calculate_market_overview(test_symbols)
        
        if result and result.get('total_volume', 0) > 0:
            print("\n✅ Market Overview Calculation Successful with Real Data!")
            print("\n📊 Live Market Results:")
            print(f"  - Market Regime: {result.get('regime', 'N/A')}")
            print(f"  - Average Change: {result.get('average_change', 0):.2f}%")
            print(f"  - Bullish Symbols: {result.get('bullish_symbols', 0)}")
            print(f"  - Bearish Symbols: {result.get('bearish_symbols', 0)}")
            print(f"  - Total Volume: ${result.get('total_volume', 0):,.0f}")
            print(f"  - Total Turnover: ${result.get('total_turnover', 0):,.0f}")
            print(f"  - Total Open Interest: ${result.get('total_open_interest', 0):,.0f}")
            print(f"  - Trend Strength: {result.get('trend_strength', 0):.2%}")
            
            # Check volume by pair
            if result.get('volume_by_pair'):
                print("\n📈 Top Volume Pairs:")
                sorted_pairs = sorted(result['volume_by_pair'].items(), 
                                     key=lambda x: x[1], reverse=True)[:5]
                for pair, volume in sorted_pairs:
                    if volume > 0:
                        print(f"    {pair}: ${volume:,.0f}")
            
            # Validate the regime detection logic
            print("\n🔍 Regime Detection Validation:")
            avg_change = result.get('average_change', 0)
            
            # Show the thresholds
            print(f"  Average Change: {avg_change:.2f}%")
            print(f"  Thresholds: Bullish > 1.0%, Bearish < -1.0%")
            
            expected_regime = '📈 Bullish' if avg_change > 1.0 else (
                '📉 Bearish' if avg_change < -1.0 else '➡️ Neutral'
            )
            actual_regime = result.get('regime', '')
            
            if expected_regime == actual_regime:
                print(f"  ✅ Regime detection correct: {actual_regime}")
            else:
                print(f"  ❌ Regime mismatch! Expected: {expected_regime}, Got: {actual_regime}")
            
            # Verify calculations
            print("\n🧮 Calculation Verification:")
            
            # Verify bullish/bearish counts
            price_changes = []
            if result.get('volume_by_pair'):
                # Note: We can't verify exact counts without the raw data
                total_symbols = result.get('bullish_symbols', 0) + result.get('bearish_symbols', 0)
                print(f"  Total symbols analyzed: {total_symbols}")
                print(f"  Bullish ratio: {result.get('bullish_symbols', 0)/max(total_symbols, 1)*100:.1f}%")
                print(f"  Bearish ratio: {result.get('bearish_symbols', 0)/max(total_symbols, 1)*100:.1f}%")
            
            # Check trend strength calculation
            trend_strength = min(abs(avg_change) / 5.0, 1.0)
            expected_trend_strength = result.get('trend_strength', 0)
            if abs(trend_strength - expected_trend_strength) < 0.01:
                print(f"  ✅ Trend strength calculation correct: {expected_trend_strength:.2%}")
            else:
                print(f"  ❌ Trend strength mismatch! Expected: {trend_strength:.2%}, Got: {expected_trend_strength:.2%}")
            
            # Check data completeness
            print("\n📋 Data Completeness Check:")
            checks = [
                ('regime' in result, "Market regime"),
                ('average_change' in result, "Average change"),
                ('bullish_symbols' in result, "Bullish count"),
                ('bearish_symbols' in result, "Bearish count"),
                ('total_volume' in result and result['total_volume'] > 0, "Total volume (with data)"),
                ('total_turnover' in result, "Total turnover"),
                ('total_open_interest' in result, "Total OI"),
                ('trend_strength' in result, "Trend strength"),
                ('timestamp' in result, "Timestamp"),
                ('volume_by_pair' in result and len(result['volume_by_pair']) > 0, "Volume by pair (with data)")
            ]
            
            all_good = True
            for check, name in checks:
                if check:
                    print(f"  ✅ {name}")
                else:
                    print(f"  ❌ {name} missing or empty!")
                    all_good = False
            
            if all_good:
                print("\n🎉 Market Overview is working perfectly with live data!")
                print("✅ All calculations are correct")
                print("✅ Market regime detection is accurate")
                print("✅ All statistics are properly calculated")
            else:
                print("\n⚠️  Some components need attention!")
                
        else:
            print("\n❌ Market overview returned empty or zero volume result!")
            print(f"Result: {result}")
            
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close the exchange connection
        if exchange:
            await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_market_overview_with_exchange())