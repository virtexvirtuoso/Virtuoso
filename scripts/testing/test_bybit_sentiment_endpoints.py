#!/usr/bin/env python3
"""
Test Bybit API endpoints used by the sentiment indicator.

The sentiment indicator expects the following data:
1. Funding Rate - from ticker or funding history
2. Long/Short Ratio - not directly available from Bybit public API
3. Liquidations - not available from public API
4. Open Interest - from ticker or OI endpoint
5. Volume sentiment - calculated from trades
"""

import subprocess
import json
import time
from datetime import datetime
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import Logger
from src.config.manager import ConfigManager
from src.core.exchanges.bybit import BybitExchange

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

def test_funding_rate_from_ticker():
    """Test getting funding rate from ticker endpoint."""
    print("\n" + "="*60)
    print("1. Testing Funding Rate from Ticker")
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
            funding_rate = ticker.get('fundingRate')
            next_funding_time = ticker.get('nextFundingTime')
            
            print(f"✓ Success: Got funding rate data")
            print(f"  Funding Rate: {funding_rate} ({float(funding_rate)*100:.4f}%)")
            print(f"  Next Funding Time: {datetime.fromtimestamp(int(next_funding_time)/1000) if next_funding_time else 'N/A'}")
            
            # This is what sentiment indicator expects
            print(f"\n  Data for sentiment indicator:")
            print(f"    market_data['ticker']['fundingRate'] = {funding_rate}")
    else:
        print(f"✗ Failed: {response}")

def test_funding_history():
    """Test funding rate history endpoint."""
    print("\n" + "="*60)
    print("2. Testing Funding Rate History")
    print("="*60)
    
    base_url = "https://api.bybit.com"
    symbol = "BTCUSDT"
    
    endpoint = f"{base_url}/v5/market/funding/history"
    params = f"category=linear&symbol={symbol}&limit=20"
    curl_cmd = f'curl -s -X GET "{endpoint}?{params}"'
    
    print(f"Command: {curl_cmd}")
    response = run_curl(curl_cmd)
    
    if isinstance(response, dict) and response.get('retCode') == 0:
        data = response.get('result', {})
        funding_history = data.get('list', [])
        print(f"✓ Success: Got {len(funding_history)} funding rate records")
        
        if funding_history:
            # Show sample for sentiment indicator
            print(f"\n  Data for sentiment indicator:")
            print(f"    market_data['sentiment']['funding_history'] = [")
            for i, record in enumerate(funding_history[:3]):
                print(f"      {{'fundingRate': '{record.get('fundingRate')}', 'fundingRateTimestamp': '{record.get('fundingRateTimestamp')}'}},")
            print(f"      ... ({len(funding_history)} total records)")
            print(f"    ]")
            
            # Calculate volatility like sentiment indicator does
            rates = [float(r.get('fundingRate', 0)) for r in funding_history]
            if len(rates) >= 2:
                import numpy as np
                volatility = np.std(rates)
                mean_rate = np.mean(rates)
                print(f"\n  Funding rate statistics:")
                print(f"    Mean: {mean_rate:.6f} ({mean_rate*100:.4f}%)")
                print(f"    Volatility: {volatility:.6f}")
    else:
        print(f"✗ Failed: {response}")

def test_open_interest():
    """Test open interest data."""
    print("\n" + "="*60)
    print("3. Testing Open Interest Data")
    print("="*60)
    
    # From ticker first
    base_url = "https://api.bybit.com"
    symbol = "BTCUSDT"
    
    endpoint = f"{base_url}/v5/market/tickers"
    params = f"category=linear&symbol={symbol}"
    curl_cmd = f'curl -s -X GET "{endpoint}?{params}"'
    
    print(f"From Ticker:")
    print(f"Command: {curl_cmd}")
    response = run_curl(curl_cmd)
    
    if isinstance(response, dict) and response.get('retCode') == 0:
        data = response.get('result', {})
        tickers = data.get('list', [])
        
        if tickers:
            ticker = tickers[0]
            open_interest = ticker.get('openInterest')
            open_interest_value = ticker.get('openInterestValue')
            
            print(f"✓ Success: Got open interest from ticker")
            print(f"  Open Interest: {open_interest} contracts")
            print(f"  Open Interest Value: ${float(open_interest_value):,.2f}" if open_interest_value else "  Open Interest Value: N/A")

    # Also test OI history endpoint
    print(f"\nFrom Open Interest History:")
    endpoint = f"{base_url}/v5/market/open-interest"
    params = f"category=linear&symbol={symbol}&intervalTime=1h&limit=10"
    curl_cmd = f'curl -s -X GET "{endpoint}?{params}"'
    
    print(f"Command: {curl_cmd}")
    response = run_curl(curl_cmd)
    
    if isinstance(response, dict) and response.get('retCode') == 0:
        data = response.get('result', {})
        oi_history = data.get('list', [])
        print(f"✓ Success: Got {len(oi_history)} OI history records")
        
        if oi_history:
            latest = oi_history[0]
            print(f"  Latest OI: {latest.get('openInterest')}")
            print(f"  Timestamp: {datetime.fromtimestamp(int(latest.get('timestamp', 0))/1000)}")

def test_volume_sentiment_data():
    """Test data needed for volume sentiment calculation."""
    print("\n" + "="*60)
    print("4. Testing Volume Sentiment Data (from trades)")
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
            # Calculate buy/sell volume like sentiment indicator would
            buy_volume = sum(float(t.get('size', 0)) for t in trades if t.get('side') == 'Buy')
            sell_volume = sum(float(t.get('size', 0)) for t in trades if t.get('side') == 'Sell')
            total_volume = buy_volume + sell_volume
            
            if total_volume > 0:
                buy_percentage = (buy_volume / total_volume) * 100
                
                print(f"\n  Volume sentiment calculation:")
                print(f"    Buy volume: {buy_volume:.4f}")
                print(f"    Sell volume: {sell_volume:.4f}")
                print(f"    Buy percentage: {buy_percentage:.2f}%")
                print(f"    Volume sentiment score: {buy_percentage:.2f}")
    else:
        print(f"✗ Failed: {response}")

def test_unavailable_data():
    """Document data that's not available from public API."""
    print("\n" + "="*60)
    print("5. Data NOT Available from Bybit Public API")
    print("="*60)
    
    print("\n❌ Long/Short Ratio:")
    print("  - Not available from public API")
    print("  - Would need to use external data source or estimate from other metrics")
    print("  - Sentiment indicator expects: market_data['sentiment']['long_short_ratio']")
    print("  - Format: {'long': 60, 'short': 40} or [0.6, 0.4]")
    
    print("\n❌ Liquidations Data:")
    print("  - Not available from public API")
    print("  - Would need WebSocket subscription or external data source")
    print("  - Sentiment indicator expects: market_data['sentiment']['liquidations']")
    print("  - Format: {'long': 1000000, 'short': 500000} or list of liquidation events")
    
    print("\n❌ Market Mood / Social Sentiment:")
    print("  - Not available from Bybit")
    print("  - Would need external sources (Twitter, Reddit, news APIs)")
    print("  - Sentiment indicator expects: market_data['sentiment']['market_mood']")
    print("  - Format: {'fear_and_greed': 50, 'social_sentiment': 0.6}")

async def test_with_exchange_class():
    """Test using the actual BybitExchange class."""
    print("\n" + "="*60)
    print("6. Testing with BybitExchange Class")
    print("="*60)
    
    logger = Logger('test_sentiment')
    config = ConfigManager().config
    exchange = BybitExchange(config, logger)
    
    symbol = 'BTCUSDT'
    
    # Test fetching sentiment-related data
    print("\nFetching data through exchange class...")
    
    # 1. Get ticker (includes funding rate and OI)
    try:
        ticker = await exchange.fetch_ticker(symbol)
        print(f"\n✓ Ticker data:")
        print(f"  Funding Rate: {ticker.get('fundingRate', 'N/A')}")
        print(f"  Open Interest: {ticker.get('openInterest', 'N/A')}")
    except Exception as e:
        print(f"✗ Failed to fetch ticker: {e}")
    
    # 2. Get trades for volume sentiment
    try:
        trades = await exchange.fetch_trades(symbol, limit=100)
        if trades:
            buy_count = sum(1 for t in trades if t.get('side') == 'buy')
            sell_count = len(trades) - buy_count
            print(f"\n✓ Trade data:")
            print(f"  Total trades: {len(trades)}")
            print(f"  Buy trades: {buy_count}")
            print(f"  Sell trades: {sell_count}")
    except Exception as e:
        print(f"✗ Failed to fetch trades: {e}")

def generate_sentiment_data_structure():
    """Show the expected data structure for sentiment indicator."""
    print("\n" + "="*60)
    print("Expected Data Structure for Sentiment Indicator")
    print("="*60)
    
    print("""
market_data = {
    'symbol': 'BTCUSDT',
    'ticker': {
        'fundingRate': 0.0001,      # From ticker endpoint
        'openInterest': 56660.198,   # From ticker endpoint
        # ... other ticker fields
    },
    'trades': [...],                 # From recent trades endpoint
    'sentiment': {
        'funding_rate': 0.0001,      # Can use ticker.fundingRate
        'funding_history': [...],     # From funding history endpoint
        'long_short_ratio': {        # NOT AVAILABLE - need external source
            'long': 60,
            'short': 40
        },
        'liquidations': {            # NOT AVAILABLE - need external source
            'long': 1000000,
            'short': 500000
        },
        'market_mood': {             # NOT AVAILABLE - need external source
            'fear_and_greed': 50,
            'social_sentiment': 0.6
        },
        'volume_sentiment': {        # Calculate from trades
            'buy_volume': 1234.56,
            'sell_volume': 987.65,
            'buy_volume_percent': 0.556
        }
    }
}
""")

def main():
    """Run all tests."""
    print("="*60)
    print("Bybit Sentiment Indicator Data Testing")
    print("="*60)
    print(f"Time: {datetime.now()}")
    
    # Test available endpoints
    test_funding_rate_from_ticker()
    test_funding_history()
    test_open_interest()
    test_volume_sentiment_data()
    
    # Document unavailable data
    test_unavailable_data()
    
    # Test with exchange class
    asyncio.run(test_with_exchange_class())
    
    # Show expected structure
    generate_sentiment_data_structure()
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print("\n✅ Available from Bybit Public API:")
    print("  - Funding Rate (ticker & history)")
    print("  - Open Interest (ticker & history)")
    print("  - Trade data for volume sentiment")
    print("\n❌ NOT Available from Bybit Public API:")
    print("  - Long/Short Ratio")
    print("  - Liquidations data")
    print("  - Market mood / social sentiment")
    print("\nThese missing data points would need to be:")
    print("  1. Obtained from external sources")
    print("  2. Estimated from available data")
    print("  3. Or disabled in the sentiment indicator")

if __name__ == "__main__":
    main()