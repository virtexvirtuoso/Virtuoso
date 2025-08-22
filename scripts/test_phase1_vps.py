#!/usr/bin/env python3
"""Test Phase 1 DirectMarketData implementation on VPS"""
import asyncio
import sys
import os
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')
os.chdir('/home/linuxuser/trading/Virtuoso_ccxt')

from src.core.market_data_direct import DirectMarketData

async def test_phase1():
    print("Testing Phase 1 Direct Market Data...")
    print("=" * 50)
    
    # Test API endpoint functionality
    try:
        print("\n1. Testing fetch_tickers...")
        tickers = await DirectMarketData.fetch_tickers(3)
        if tickers:
            print(f"✅ Got {len(tickers)} tickers")
            for symbol, data in list(tickers.items())[:2]:
                print(f"   {symbol}: ${data['price']:.2f}")
        else:
            print("❌ No tickers returned")
            
        print("\n2. Testing dashboard data...")
        dashboard = await DirectMarketData.get_dashboard_data()
        if dashboard['status'] == 'success':
            print(f"✅ Dashboard data ready")
            print(f"   Total symbols: {dashboard['overview']['total_symbols']}")
            print(f"   Data source: {dashboard['overview']['data_source']}")
        else:
            print("❌ Dashboard data failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("Phase 1 test complete!")

if __name__ == "__main__":
    asyncio.run(test_phase1())