#!/usr/bin/env python3
"""Test script to verify market overview calculation works properly"""

import asyncio
import sys
import os
sys.path.insert(0, '/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

from src.monitoring.market_reporter import MarketReporter
import logging

logging.basicConfig(level=logging.INFO)

async def test_market_overview():
    """Test the market overview calculation"""
    print("=" * 60)
    print("Testing Market Overview Calculation")
    print("=" * 60)
    
    # Initialize market reporter
    market_reporter = MarketReporter()
    
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
        
        if result:
            print("\n✅ Market Overview Calculation Successful!")
            print("\n📊 Results:")
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
                    print(f"    {pair}: ${volume:,.0f}")
            
            # Check for any failed symbols
            if result.get('failed_symbols'):
                print(f"\n⚠️  Failed Symbols: {len(result['failed_symbols'])}")
                
            # Validate the regime detection logic
            print("\n🔍 Regime Detection Validation:")
            avg_change = result.get('average_change', 0)
            expected_regime = '📈 Bullish' if avg_change > 1.0 else (
                '📉 Bearish' if avg_change < -1.0 else '➡️ Neutral'
            )
            actual_regime = result.get('regime', '')
            
            if expected_regime == actual_regime:
                print(f"  ✅ Regime detection correct: {actual_regime}")
            else:
                print(f"  ❌ Regime mismatch! Expected: {expected_regime}, Got: {actual_regime}")
            
            # Check data completeness
            print("\n📋 Data Completeness Check:")
            checks = [
                ('regime' in result, "Market regime"),
                ('average_change' in result, "Average change"),
                ('bullish_symbols' in result, "Bullish count"),
                ('bearish_symbols' in result, "Bearish count"),
                ('total_volume' in result, "Total volume"),
                ('total_turnover' in result, "Total turnover"),
                ('total_open_interest' in result, "Total OI"),
                ('trend_strength' in result, "Trend strength"),
                ('timestamp' in result, "Timestamp")
            ]
            
            all_good = True
            for check, name in checks:
                if check:
                    print(f"  ✅ {name}")
                else:
                    print(f"  ❌ {name} missing!")
                    all_good = False
            
            if all_good:
                print("\n🎉 All market overview components working properly!")
            else:
                print("\n⚠️  Some components are missing!")
                
        else:
            print("\n❌ Market overview returned empty result!")
            
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close the exchange connection
        if hasattr(market_reporter, 'exchange') and market_reporter.exchange:
            await market_reporter.exchange.close()

if __name__ == "__main__":
    asyncio.run(test_market_overview())