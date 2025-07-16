#!/usr/bin/env python3

import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

import asyncio
from data_acquisition.binance.futures_client import BinanceFuturesClient

async def test_risk_limits():
    """Test the fixed risk limits functionality."""
    
    print("🧪 Testing Risk Limits Fix")
    print("=" * 30)
    
    async with BinanceFuturesClient() as client:
        try:
            # Test a few symbols
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
            
            for symbol in symbols:
                print(f"\n🎯 Testing {symbol}:")
                risk_limits = await client.get_leverage_bracket(symbol)
                
                print(f"   Type: {type(risk_limits)}")
                print(f"   Length: {len(risk_limits) if risk_limits else 0}")
                
                if risk_limits and len(risk_limits) > 0:
                    print(f"   First bracket: {risk_limits[0]}")
                    max_lev = max(float(bracket.get('initialLeverage', 0)) for bracket in risk_limits)
                    print(f"   ✅ Max leverage: {max_lev}x")
                else:
                    print("   ❌ No risk limits data")
                    
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_risk_limits()) 