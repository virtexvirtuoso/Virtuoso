#!/usr/bin/env python3
"""
Test Bybit LSR API directly to diagnose permission/access issues
"""

import asyncio
import aiohttp
import os
import sys
import json
from datetime import datetime

# Test symbols
TEST_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

async def test_public_api():
    """Test the public Bybit API endpoint for LSR data"""
    
    print(f"\n{'='*60}")
    print("Testing PUBLIC Bybit Account Ratio API")
    print(f"Time: {datetime.now()}")
    print('='*60)
    
    async with aiohttp.ClientSession() as session:
        for symbol in TEST_SYMBOLS:
            try:
                url = 'https://api.bybit.com/v5/market/account-ratio'
                params = {
                    'category': 'linear',
                    'symbol': symbol,
                    'period': '5min',
                    'limit': 1
                }
                
                print(f"\n📊 Testing {symbol}...")
                print(f"URL: {url}")
                print(f"Params: {params}")
                
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    
                    if response.status == 200:
                        print(f"✅ Status: {response.status} OK")
                        
                        if data.get('retCode') == 0:
                            result = data.get('result', {})
                            items = result.get('list', [])
                            
                            if items:
                                latest = items[0]
                                buy_ratio = float(latest.get('buyRatio', 0))
                                sell_ratio = float(latest.get('sellRatio', 0))
                                
                                print(f"📈 Buy Ratio: {buy_ratio * 100:.2f}%")
                                print(f"📉 Sell Ratio: {sell_ratio * 100:.2f}%")
                                print(f"🕐 Timestamp: {latest.get('timestamp')}")
                                
                                if buy_ratio == 0.5 and sell_ratio == 0.5:
                                    print("⚠️  WARNING: Data shows exactly 50/50 - might be default!")
                                else:
                                    print("✅ LSR data looks valid!")
                            else:
                                print("❌ No data returned in list")
                        else:
                            print(f"❌ API Error: {data.get('retMsg')} (code: {data.get('retCode')})")
                    else:
                        print(f"❌ HTTP Error: Status {response.status}")
                        print(f"Response: {await response.text()}")
                        
            except Exception as e:
                print(f"❌ Exception for {symbol}: {str(e)}")
            
            await asyncio.sleep(0.5)  # Small delay between requests

async def test_authenticated_api():
    """Test if we can access the API with authentication (if keys are available)"""
    
    api_key = os.getenv('BYBIT_API_KEY')
    api_secret = os.getenv('BYBIT_API_SECRET')
    
    if not api_key:
        print("\n⚠️  No BYBIT_API_KEY found in environment")
        print("   LSR data is available via PUBLIC API, no authentication needed")
        return
    
    print(f"\n{'='*60}")
    print("API Key Configuration Check")
    print('='*60)
    print(f"✅ API Key found: {api_key[:8]}...")
    print(f"✅ API Secret found: {'Yes' if api_secret else 'No'}")

async def check_rate_limits():
    """Check rate limit headers from API response"""
    
    print(f"\n{'='*60}")
    print("Checking Rate Limits")
    print('='*60)
    
    async with aiohttp.ClientSession() as session:
        url = 'https://api.bybit.com/v5/market/account-ratio'
        params = {
            'category': 'linear',
            'symbol': 'BTCUSDT',
            'period': '5min',
            'limit': 1
        }
        
        async with session.get(url, params=params) as response:
            # Check rate limit headers
            headers = response.headers
            
            print("Rate Limit Headers:")
            for header, value in headers.items():
                if 'rate' in header.lower() or 'limit' in header.lower():
                    print(f"  {header}: {value}")
            
            if 'X-Bapi-Limit-Status' in headers:
                print(f"\n📊 Rate Limit Status: {headers['X-Bapi-Limit-Status']}")
            
            if 'X-Bapi-Limit' in headers:
                print(f"📊 Rate Limit: {headers['X-Bapi-Limit']}")

async def test_different_periods():
    """Test different time periods for LSR data"""
    
    print(f"\n{'='*60}")
    print("Testing Different Time Periods")
    print('='*60)
    
    periods = ['5min', '15min', '30min', '1h', '4h', '1d']
    
    async with aiohttp.ClientSession() as session:
        for period in periods:
            try:
                url = 'https://api.bybit.com/v5/market/account-ratio'
                params = {
                    'category': 'linear',
                    'symbol': 'BTCUSDT',
                    'period': period,
                    'limit': 1
                }
                
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    
                    if data.get('retCode') == 0:
                        result = data.get('result', {})
                        items = result.get('list', [])
                        
                        if items:
                            latest = items[0]
                            buy_ratio = float(latest.get('buyRatio', 0)) * 100
                            sell_ratio = float(latest.get('sellRatio', 0)) * 100
                            
                            status = "✅" if (buy_ratio != 50.0 or sell_ratio != 50.0) else "⚠️"
                            print(f"{status} {period:5s}: Long={buy_ratio:.1f}%, Short={sell_ratio:.1f}%")
                        else:
                            print(f"❌ {period:5s}: No data")
                    else:
                        print(f"❌ {period:5s}: {data.get('retMsg')}")
                        
            except Exception as e:
                print(f"❌ {period:5s}: Exception - {str(e)}")
            
            await asyncio.sleep(0.2)

async def main():
    """Run all tests"""
    
    print("\n" + "="*60)
    print(" BYBIT LSR API DIAGNOSTIC TEST")
    print("="*60)
    
    # Test public API
    await test_public_api()
    
    # Check authentication
    await test_authenticated_api()
    
    # Check rate limits
    await check_rate_limits()
    
    # Test different periods
    await test_different_periods()
    
    print("\n" + "="*60)
    print(" TEST COMPLETE")
    print("="*60)
    print("\nSummary:")
    print("• The account-ratio endpoint is PUBLIC (no auth required)")
    print("• If getting 50/50 for all symbols, check:")
    print("  1. Network connectivity from VPS to api.bybit.com")
    print("  2. Any firewall/proxy blocking the requests")
    print("  3. Whether the exchange has data for the symbols")
    print("\n")

if __name__ == "__main__":
    asyncio.run(main())