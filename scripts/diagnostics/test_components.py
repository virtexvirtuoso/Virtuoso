#!/usr/bin/env python3
"""
Simple component test script
"""

import asyncio
import aiohttp
import os
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

logging.basicConfig(level=logging.INFO)

async def test_exchange_connectivity():
    """Test direct exchange connectivity"""
    print("=== Testing Exchange Connectivity ===")
    
    # Test Bybit API direct access
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.bybit.com/v5/market/time"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Bybit API accessible: {data}")
                    return True
                else:
                    print(f"❌ Bybit API error: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Exchange connectivity error: {e}")
        return False

async def test_database_connectivity():
    """Test direct database connectivity"""
    print("=== Testing Database Connectivity ===")
    
    try:
        async with aiohttp.ClientSession() as session:
            url = "http://localhost:8086/health"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ InfluxDB accessible: {data}")
                    return True
                else:
                    print(f"❌ InfluxDB error: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Database connectivity error: {e}")
        return False

def test_api_credentials():
    """Test API credentials configuration"""
    print("=== Testing API Credentials ===")
    
    bybit_key = os.getenv('BYBIT_API_KEY')
    bybit_secret = os.getenv('BYBIT_API_SECRET')
    
    if bybit_key and bybit_secret:
        print(f"✅ Bybit credentials found - Key: {bybit_key[:10]}...")
        return True
    else:
        print("❌ Bybit credentials missing")
        return False

async def test_authenticated_request():
    """Test authenticated API request"""
    print("=== Testing Authenticated Request ===")
    
    bybit_key = os.getenv('BYBIT_API_KEY')
    bybit_secret = os.getenv('BYBIT_API_SECRET')
    
    if not (bybit_key and bybit_secret):
        print("❌ No credentials for authenticated test")
        return False
    
    try:
        import hashlib
        import hmac
        import time
        
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        
        # Simple wallet balance check (no params needed)
        query_string = f"timestamp={timestamp}&recvWindow={recv_window}"
        signature = hmac.new(
            bybit_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'X-BAPI-API-KEY': bybit_key,
            'X-BAPI-SIGN': signature,
            'X-BAPI-SIGN-TYPE': '2',
            'X-BAPI-TIMESTAMP': timestamp,
            'X-BAPI-RECV-WINDOW': recv_window,
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            url = f"https://api.bybit.com/v5/account/wallet-balance?{query_string}"
            async with session.get(url, headers=headers) as response:
                print(f"Response status: {response.status}")
                text_response = await response.text()
                print(f"Response text: {text_response}")
                
                try:
                    data = await response.json()
                    print(f"Response data: {data}")
                except:
                    data = {"error": "Could not parse JSON", "text": text_response}
                
                if response.status == 200 and data.get('retCode') == 0:
                    print("✅ Authenticated API request successful")
                    return True
                else:
                    print(f"❌ Authenticated API error: Status {response.status}, Data: {data}")
                    
                    # Check for specific error codes
                    if data.get('retCode') == 10003:
                        print("   💡 This appears to be an API key permissions issue")
                    elif data.get('retCode') == 10004:
                        print("   💡 This appears to be an API signature issue")
                    
                    return False
                    
    except Exception as e:
        print(f"❌ Authentication test error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("🔍 Starting Component Health Check\n")
    
    results = []
    
    # Test 1: API Credentials
    results.append(test_api_credentials())
    
    # Test 2: Exchange Connectivity
    results.append(await test_exchange_connectivity())
    
    # Test 3: Database Connectivity  
    results.append(await test_database_connectivity())
    
    # Test 4: Authenticated Request
    results.append(await test_authenticated_request())
    
    print("\n=== SUMMARY ===")
    print(f"Tests passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✅ All components healthy - ready to start application")
    else:
        print("❌ Some components have issues - investigate failed tests")
    
    return all(results)

if __name__ == "__main__":
    asyncio.run(main()) 