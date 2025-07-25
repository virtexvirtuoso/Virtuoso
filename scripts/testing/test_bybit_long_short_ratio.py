#!/usr/bin/env python3
"""
Test Bybit Long/Short Ratio API endpoint.

Documentation: https://bybit-exchange.github.io/docs/api-explorer/v5/market/long-short-ratio
"""

import subprocess
import json
import time
from datetime import datetime

def run_curl(command):
    """Run a curl command and return the response."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except:
                return result.stdout
        else:
            return f"Error: {result.stderr}"
    except Exception as e:
        return f"Exception: {str(e)}"

def test_long_short_ratio():
    """Test the Long/Short ratio endpoint."""
    print("="*60)
    print("Testing Bybit Long/Short Ratio Endpoint")
    print("="*60)
    
    base_url = "https://api.bybit.com"
    symbol = "BTCUSDT"
    
    # Test different periods
    periods = ['5min', '15min', '30min', '1h', '4h', '1d']
    
    for period in periods:
        print(f"\nTesting period: {period}")
        
        endpoint = f"{base_url}/v5/market/account-ratio"
        params = f"category=linear&symbol={symbol}&period={period}&limit=10"
        curl_cmd = f'curl -s -X GET "{endpoint}?{params}"'
        
        print(f"Command: {curl_cmd}")
        response = run_curl(curl_cmd)
        
        if isinstance(response, dict):
            ret_code = response.get('retCode')
            if ret_code == 0:
                data = response.get('result', {})
                ratio_list = data.get('list', [])
                
                print(f"✓ Success: Got {len(ratio_list)} records")
                
                if ratio_list:
                    # Show the latest ratio
                    latest = ratio_list[0]
                    buy_ratio = float(latest.get('buyRatio', 0))
                    sell_ratio = float(latest.get('sellRatio', 0))
                    timestamp = int(latest.get('timestamp', 0))
                    
                    print(f"\n  Latest Long/Short Ratio:")
                    print(f"    Timestamp: {datetime.fromtimestamp(timestamp/1000)}")
                    print(f"    Buy/Long Ratio: {buy_ratio:.4f} ({buy_ratio*100:.2f}%)")
                    print(f"    Sell/Short Ratio: {sell_ratio:.4f} ({sell_ratio*100:.2f}%)")
                    print(f"    Long percentage: {buy_ratio*100:.2f}%")
                    print(f"    Short percentage: {sell_ratio*100:.2f}%")
                    
                    # Show data format for sentiment indicator
                    print(f"\n  Data for sentiment indicator:")
                    print(f"    market_data['sentiment']['long_short_ratio'] = {{")
                    print(f"        'long': {buy_ratio*100:.2f},")
                    print(f"        'short': {sell_ratio*100:.2f}")
                    print(f"    }}")
            else:
                print(f"✗ API returned error code: {ret_code}")
                print(f"  Message: {response.get('retMsg', 'Unknown error')}")
        else:
            print(f"✗ Failed to get response")

def test_all_parameters():
    """Test with all available parameters."""
    print("\n" + "="*60)
    print("Testing with all parameter combinations")
    print("="*60)
    
    base_url = "https://api.bybit.com"
    
    # Test different categories and symbols
    test_cases = [
        {"category": "linear", "symbol": "BTCUSDT", "period": "1h"},
        {"category": "linear", "symbol": "ETHUSDT", "period": "1h"},
        {"category": "inverse", "symbol": "BTCUSD", "period": "1h"},
    ]
    
    for test in test_cases:
        print(f"\nTesting: {test}")
        
        endpoint = f"{base_url}/v5/market/account-ratio"
        params = f"category={test['category']}&symbol={test['symbol']}&period={test['period']}&limit=1"
        curl_cmd = f'curl -s -X GET "{endpoint}?{params}"'
        
        response = run_curl(curl_cmd)
        
        if isinstance(response, dict) and response.get('retCode') == 0:
            data = response.get('result', {})
            ratio_list = data.get('list', [])
            
            if ratio_list:
                latest = ratio_list[0]
                buy_ratio = float(latest.get('buyRatio', 0))
                sell_ratio = float(latest.get('sellRatio', 0))
                
                print(f"✓ Success: Long: {buy_ratio*100:.2f}%, Short: {sell_ratio*100:.2f}%")
            else:
                print(f"✓ Success but no data")
        else:
            print(f"✗ Failed: {response.get('retMsg', 'Unknown error') if isinstance(response, dict) else response}")

def generate_example_code():
    """Generate example code for using L/S ratio."""
    print("\n" + "="*60)
    print("Example Implementation")
    print("="*60)
    
    print("""
# Add to BybitExchange class:
async def fetch_long_short_ratio(self, symbol: str, period: str = '1h', limit: int = 10):
    \"\"\"
    Fetch long/short ratio data.
    
    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT')
        period: Time period ('5min', '15min', '30min', '1h', '4h', '1d')
        limit: Number of data points (max 500)
    
    Returns:
        List of L/S ratio data points
    \"\"\"
    endpoint = '/v5/market/account-ratio'
    params = {
        'category': 'linear',
        'symbol': symbol,
        'period': period,
        'limit': limit
    }
    
    response = await self._make_request('GET', endpoint, params)
    
    if response.get('retCode') == 0:
        return response.get('result', {}).get('list', [])
    else:
        raise Exception(f"Failed to fetch L/S ratio: {response.get('retMsg')}")

# Usage in sentiment indicator:
async def get_sentiment_data(exchange, symbol):
    # Fetch L/S ratio
    ls_data = await exchange.fetch_long_short_ratio(symbol, period='1h', limit=1)
    
    if ls_data:
        latest = ls_data[0]
        long_ratio = float(latest.get('buyRatio', 0.5)) * 100
        short_ratio = float(latest.get('sellRatio', 0.5)) * 100
        
        sentiment_data['long_short_ratio'] = {
            'long': long_ratio,
            'short': short_ratio
        }
""")

def main():
    """Run all tests."""
    print("="*60)
    print("Bybit Long/Short Ratio API Testing")
    print("="*60)
    print(f"Time: {datetime.now()}\n")
    
    # Test L/S ratio endpoint
    test_long_short_ratio()
    
    # Test different parameters
    test_all_parameters()
    
    # Show implementation example
    generate_example_code()
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print("\n✅ Long/Short Ratio IS AVAILABLE from Bybit API!")
    print("\nEndpoint: GET /v5/market/account-ratio")
    print("Parameters:")
    print("  - category: 'linear' or 'inverse'")
    print("  - symbol: Trading symbol")
    print("  - period: 5min, 15min, 30min, 1h, 4h, 1d")
    print("  - limit: Max 500")
    print("\nResponse format:")
    print("  - buyRatio: Long position ratio (0-1)")
    print("  - sellRatio: Short position ratio (0-1)")
    print("  - timestamp: Unix timestamp in milliseconds")

if __name__ == "__main__":
    main()