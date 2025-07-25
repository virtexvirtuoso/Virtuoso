#!/usr/bin/env python3
"""
Test all Bybit API endpoints using curl commands to verify correct usage.

This script tests:
1. Public endpoints (no authentication required)
2. The exact URLs and parameters we're using
3. Response formats and data structures
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

def test_kline_endpoint():
    """Test OHLCV/Kline endpoint."""
    print("\n" + "="*60)
    print("1. Testing Kline/OHLCV Endpoint")
    print("="*60)
    
    base_url = "https://api.bybit.com"
    symbol = "BTCUSDT"
    
    # Test different intervals
    intervals = {
        '1': '1 minute',
        '5': '5 minutes',
        '15': '15 minutes',
        '30': '30 minutes',
        '60': '1 hour',
        '240': '4 hours'
    }
    
    for interval, description in intervals.items():
        print(f"\nTesting {description} interval...")
        
        # Calculate start time (200 candles back)
        now = int(time.time() * 1000)
        interval_ms = int(interval) * 60 * 1000
        start = now - (200 * interval_ms)
        
        # Build the curl command
        endpoint = f"{base_url}/v5/market/kline"
        params = f"category=linear&symbol={symbol}&interval={interval}&limit=100"
        curl_cmd = f'curl -s -X GET "{endpoint}?{params}"'
        
        print(f"Command: {curl_cmd}")
        response = run_curl(curl_cmd)
        
        if isinstance(response, dict) and response.get('retCode') == 0:
            data = response.get('result', {})
            klines = data.get('list', [])
            print(f"✓ Success: Got {len(klines)} candles")
            
            if klines:
                # Show sample candle
                candle = klines[0]
                print(f"  Sample candle: timestamp={candle[0]}, O={candle[1]}, H={candle[2]}, L={candle[3]}, C={candle[4]}, V={candle[5]}")
        else:
            print(f"✗ Failed: {response}")

def test_trades_endpoint():
    """Test public trades endpoint."""
    print("\n" + "="*60)
    print("2. Testing Public Trades Endpoint")
    print("="*60)
    
    base_url = "https://api.bybit.com"
    symbol = "BTCUSDT"
    
    endpoint = f"{base_url}/v5/market/recent-trade"
    params = f"category=linear&symbol={symbol}&limit=100"
    curl_cmd = f'curl -s -X GET "{endpoint}?{params}"'
    
    print(f"Command: {curl_cmd}")
    response = run_curl(curl_cmd)
    
    if isinstance(response, dict) and response.get('retCode') == 0:
        data = response.get('result', {})
        trades = data.get('list', [])
        print(f"✓ Success: Got {len(trades)} trades")
        
        if trades:
            # Show sample trade
            trade = trades[0]
            print(f"  Sample trade: time={trade.get('time')}, price={trade.get('price')}, "
                  f"size={trade.get('size')}, side={trade.get('side')}")
    else:
        print(f"✗ Failed: {response}")

def test_orderbook_endpoint():
    """Test orderbook endpoint."""
    print("\n" + "="*60)
    print("3. Testing Orderbook Endpoint")
    print("="*60)
    
    base_url = "https://api.bybit.com"
    symbol = "BTCUSDT"
    
    endpoint = f"{base_url}/v5/market/orderbook"
    params = f"category=linear&symbol={symbol}&limit=25"
    curl_cmd = f'curl -s -X GET "{endpoint}?{params}"'
    
    print(f"Command: {curl_cmd}")
    response = run_curl(curl_cmd)
    
    if isinstance(response, dict) and response.get('retCode') == 0:
        data = response.get('result', {})
        bids = data.get('b', [])
        asks = data.get('a', [])
        print(f"✓ Success: Got {len(bids)} bids and {len(asks)} asks")
        
        if bids:
            print(f"  Best bid: price={bids[0][0]}, size={bids[0][1]}")
        if asks:
            print(f"  Best ask: price={asks[0][0]}, size={asks[0][1]}")
            
        print(f"  Update ID: {data.get('u')}")
        print(f"  Timestamp: {data.get('ts')}")
    else:
        print(f"✗ Failed: {response}")

def test_ticker_endpoint():
    """Test 24hr ticker endpoint."""
    print("\n" + "="*60)
    print("4. Testing 24hr Ticker Endpoint")
    print("="*60)
    
    base_url = "https://api.bybit.com"
    symbol = "BTCUSDT"
    
    endpoint = f"{base_url}/v5/market/tickers"
    params = f"category=linear&symbol={symbol}"
    curl_cmd = f'curl -s -X GET "{endpoint}?{params}"'
    
    print(f"Command: {curl_cmd}")
    response = run_curl(curl_cmd)
    
    if isinstance(response, dict) and response.get('retCode') == 0:
        data = response.get('result', {})
        tickers = data.get('list', [])
        
        if tickers:
            ticker = tickers[0]
            print(f"✓ Success: Got ticker data")
            print(f"  Symbol: {ticker.get('symbol')}")
            print(f"  Last Price: {ticker.get('lastPrice')}")
            print(f"  24h High: {ticker.get('highPrice24h')}")
            print(f"  24h Low: {ticker.get('lowPrice24h')}")
            print(f"  24h Volume: {ticker.get('volume24h')}")
            print(f"  24h Turnover: {ticker.get('turnover24h')}")
            print(f"  Bid: {ticker.get('bid1Price')}")
            print(f"  Ask: {ticker.get('ask1Price')}")
            print(f"  Open Interest: {ticker.get('openInterest')}")
            print(f"  Funding Rate: {ticker.get('fundingRate')}")
    else:
        print(f"✗ Failed: {response}")

def test_instruments_endpoint():
    """Test instruments info endpoint."""
    print("\n" + "="*60)
    print("5. Testing Instruments Info Endpoint")
    print("="*60)
    
    base_url = "https://api.bybit.com"
    
    endpoint = f"{base_url}/v5/market/instruments-info"
    params = "category=linear&limit=10"
    curl_cmd = f'curl -s -X GET "{endpoint}?{params}"'
    
    print(f"Command: {curl_cmd}")
    response = run_curl(curl_cmd)
    
    if isinstance(response, dict) and response.get('retCode') == 0:
        data = response.get('result', {})
        instruments = data.get('list', [])
        print(f"✓ Success: Got {len(instruments)} instruments")
        
        if instruments:
            # Show BTC perpetual info
            btc_perp = next((i for i in instruments if i.get('symbol') == 'BTCUSDT'), None)
            if btc_perp:
                print(f"\n  BTCUSDT Info:")
                print(f"    Status: {btc_perp.get('status')}")
                print(f"    Contract Type: {btc_perp.get('contractType')}")
                print(f"    Base Currency: {btc_perp.get('baseCoin')}")
                print(f"    Quote Currency: {btc_perp.get('quoteCoin')}")
                print(f"    Min Order Qty: {btc_perp.get('minOrderQty')}")
                print(f"    Max Order Qty: {btc_perp.get('maxOrderQty')}")
                print(f"    Tick Size: {btc_perp.get('priceFilter', {}).get('tickSize')}")
    else:
        print(f"✗ Failed: {response}")

def test_funding_rate_endpoint():
    """Test funding rate endpoint."""
    print("\n" + "="*60)
    print("6. Testing Funding Rate Endpoint")
    print("="*60)
    
    base_url = "https://api.bybit.com"
    symbol = "BTCUSDT"
    
    endpoint = f"{base_url}/v5/market/funding/history"
    params = f"category=linear&symbol={symbol}&limit=10"
    curl_cmd = f'curl -s -X GET "{endpoint}?{params}"'
    
    print(f"Command: {curl_cmd}")
    response = run_curl(curl_cmd)
    
    if isinstance(response, dict) and response.get('retCode') == 0:
        data = response.get('result', {})
        funding_history = data.get('list', [])
        print(f"✓ Success: Got {len(funding_history)} funding rate records")
        
        if funding_history:
            latest = funding_history[0]
            print(f"  Latest funding:")
            print(f"    Symbol: {latest.get('symbol')}")
            print(f"    Funding Rate: {latest.get('fundingRate')}")
            print(f"    Funding Time: {datetime.fromtimestamp(int(latest.get('fundingRateTimestamp', 0))/1000)}")
    else:
        print(f"✗ Failed: {response}")

def test_open_interest_endpoint():
    """Test open interest endpoint."""
    print("\n" + "="*60)
    print("7. Testing Open Interest Endpoint")
    print("="*60)
    
    base_url = "https://api.bybit.com"
    symbol = "BTCUSDT"
    
    endpoint = f"{base_url}/v5/market/open-interest"
    params = f"category=linear&symbol={symbol}&intervalTime=1h&limit=10"
    curl_cmd = f'curl -s -X GET "{endpoint}?{params}"'
    
    print(f"Command: {curl_cmd}")
    response = run_curl(curl_cmd)
    
    if isinstance(response, dict) and response.get('retCode') == 0:
        data = response.get('result', {})
        oi_history = data.get('list', [])
        print(f"✓ Success: Got {len(oi_history)} open interest records")
        
        if oi_history:
            latest = oi_history[0]
            print(f"  Latest OI:")
            print(f"    Symbol: {latest.get('symbol')}")
            print(f"    Open Interest: {latest.get('openInterest')}")
            print(f"    Timestamp: {datetime.fromtimestamp(int(latest.get('timestamp', 0))/1000)}")
    else:
        print(f"✗ Failed: {response}")

def generate_curl_examples():
    """Generate example curl commands for reference."""
    print("\n" + "="*60)
    print("Example CURL Commands for Bybit API")
    print("="*60)
    
    examples = [
        {
            "name": "Get OHLCV/Klines",
            "curl": 'curl -X GET "https://api.bybit.com/v5/market/kline?category=linear&symbol=BTCUSDT&interval=1&limit=100"'
        },
        {
            "name": "Get Recent Trades",
            "curl": 'curl -X GET "https://api.bybit.com/v5/market/recent-trade?category=linear&symbol=BTCUSDT&limit=100"'
        },
        {
            "name": "Get Orderbook",
            "curl": 'curl -X GET "https://api.bybit.com/v5/market/orderbook?category=linear&symbol=BTCUSDT&limit=25"'
        },
        {
            "name": "Get 24hr Ticker",
            "curl": 'curl -X GET "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"'
        },
        {
            "name": "Get Instruments Info",
            "curl": 'curl -X GET "https://api.bybit.com/v5/market/instruments-info?category=linear&limit=10"'
        },
        {
            "name": "Get Funding Rate History",
            "curl": 'curl -X GET "https://api.bybit.com/v5/market/funding/history?category=linear&symbol=BTCUSDT&limit=10"'
        },
        {
            "name": "Get Open Interest",
            "curl": 'curl -X GET "https://api.bybit.com/v5/market/open-interest?category=linear&symbol=BTCUSDT&intervalTime=1h&limit=10"'
        }
    ]
    
    print("\nYou can run these commands directly in your terminal:\n")
    for example in examples:
        print(f"{example['name']}:")
        print(f"  {example['curl']}")
        print()

def main():
    """Run all endpoint tests."""
    print("="*60)
    print("Bybit API Endpoint Testing")
    print("="*60)
    print(f"Time: {datetime.now()}")
    
    # Test all endpoints
    test_kline_endpoint()
    test_trades_endpoint()
    test_orderbook_endpoint()
    test_ticker_endpoint()
    test_instruments_endpoint()
    test_funding_rate_endpoint()
    test_open_interest_endpoint()
    
    # Generate examples
    generate_curl_examples()
    
    print("\n" + "="*60)
    print("Testing Complete!")
    print("="*60)

if __name__ == "__main__":
    main()