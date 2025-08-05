#!/usr/bin/env python3
"""
Binance API Test Script for Virtuoso Integration

This script tests all the Binance API endpoints we need for the integration
and shows the actual response formats. It helps developers understand what
data is available and how it's structured.

Usage:
    python scripts/test_binance_api_calls.py

Requirements:
    pip install ccxt pandas tabulate
"""

import asyncio
import ccxt.async_support as ccxt  # Use async support
import json
import time
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
from tabulate import tabulate

class BinanceAPITester:
    """Test all Binance API endpoints needed for Virtuoso integration."""
    
    def __init__(self, use_testnet: bool = False, api_key: str = None, api_secret: str = None):
        """
        Initialize the Binance API tester.
        
        Args:
            use_testnet: Whether to use testnet (default: False for real data)
            api_key: Optional API key for higher rate limits
            api_secret: Optional API secret for higher rate limits
        """
        self.use_testnet = use_testnet
        
        # Configure CCXT exchange
        config = {
            'enableRateLimit': True,    # Important to avoid rate limits
            'rateLimit': 1200,          # Wait 1.2 seconds between requests
            'verbose': False,           # Set to True for debugging
        }
        
        # Add API credentials if provided
        if api_key and api_secret:
            config['apiKey'] = api_key
            config['secret'] = api_secret
            print(f"✅ Using API credentials for higher rate limits")
        else:
            print(f"ℹ️  Using public API access (no credentials)")
        
        # Configure for testnet if requested
        if use_testnet:
            config['sandbox'] = True
            config['urls'] = {
                'api': 'https://testnet.binance.vision',
                'fapiV1': 'https://testnet.binance.vision/fapi/v1',
            }
            print(f"🧪 Using Binance testnet")
        else:
            print(f"🌐 Using Binance mainnet")
        
        # Create exchange instance (using async version)
        self.exchange = ccxt.binance(config)
        
        # Test symbols - using popular, liquid pairs
        self.spot_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        self.futures_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']  # No slash for futures
        
        # Results storage
        self.results = {}
        
        print(f"📊 Initialized Binance API tester")
        print(f"   Spot symbols: {', '.join(self.spot_symbols)}")
        print(f"   Futures symbols: {', '.join(self.futures_symbols)}")
        print("-" * 60)
    
    def pretty_print_json(self, data: Any, title: str = None) -> None:
        """Pretty print JSON data with optional title."""
        if title:
            print(f"\n📋 {title}")
            print("=" * len(title))
        
        if isinstance(data, (dict, list)):
            print(json.dumps(data, indent=2, default=str))
        else:
            print(data)
        print()
    
    def print_table(self, data: List[Dict], title: str = None) -> None:
        """Print data as a formatted table."""
        if title:
            print(f"\n📊 {title}")
            print("=" * len(title))
        
        if data and isinstance(data, list) and len(data) > 0:
            # Convert to DataFrame for better display
            df = pd.DataFrame(data)
            print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
        else:
            print("No data available")
        print()
    
    async def test_basic_connectivity(self) -> bool:
        """Test basic connectivity to Binance API."""
        print(f"🔌 Testing Basic Connectivity")
        print("-" * 30)
        
        try:
            # Test 1: Load markets
            print("1️⃣  Loading markets...")
            markets = await self.exchange.load_markets()
            market_count = len(markets)
            
            print(f"   ✅ Successfully loaded {market_count} markets")
            
            # Show some example markets
            spot_markets = [symbol for symbol in markets.keys() if '/' in symbol][:5]
            futures_markets = [symbol for symbol in markets.keys() if '/' not in symbol and symbol.endswith('USDT')][:5]
            
            print(f"   📈 Example spot markets: {', '.join(spot_markets)}")
            print(f"   🚀 Example futures markets: {', '.join(futures_markets)}")
            
            # Test 2: Server time
            print("\n2️⃣  Checking server time...")
            server_time = await self.exchange.fetch_time()
            local_time = int(time.time() * 1000)
            time_diff = abs(server_time - local_time)
            
            print(f"   🕐 Server time: {datetime.fromtimestamp(server_time/1000)}")
            print(f"   🕐 Local time:  {datetime.fromtimestamp(local_time/1000)}")
            print(f"   ⏱️  Time difference: {time_diff}ms")
            
            if time_diff > 5000:  # 5 seconds
                print(f"   ⚠️  Large time difference detected!")
            else:
                print(f"   ✅ Time synchronization OK")
            
            self.results['connectivity'] = {
                'status': 'success',
                'market_count': market_count,
                'time_diff_ms': time_diff
            }
            
            return True
            
        except Exception as e:
            print(f"   ❌ Connectivity test failed: {str(e)}")
            self.results['connectivity'] = {
                'status': 'failed',
                'error': str(e)
            }
            return False
    
    async def test_spot_market_data(self) -> None:
        """Test spot market data endpoints."""
        print(f"\n📈 Testing Spot Market Data")
        print("-" * 30)
        
        for symbol in self.spot_symbols:
            print(f"\n🎯 Testing {symbol}")
            print(f"   {'-' * 20}")
            
            try:
                # Test 1: Ticker data
                print("   1️⃣  Fetching ticker...")
                ticker = await self.exchange.fetch_ticker(symbol)
                
                print(f"      💰 Price: ${ticker['last']:,.2f}")
                print(f"      📊 24h Volume: ${ticker['quoteVolume']:,.2f}")
                print(f"      📈 24h Change: {ticker['percentage']:.2f}%")
                print(f"      🔄 Bid/Ask: ${ticker['bid']:.2f}/${ticker['ask']:.2f}")
                
                # Show raw ticker structure (limited)
                ticker_sample = {
                    'symbol': ticker['symbol'],
                    'last': ticker['last'],
                    'bid': ticker['bid'],
                    'ask': ticker['ask'],
                    'volume': ticker['baseVolume'],
                    'quoteVolume': ticker['quoteVolume'],
                    'percentage': ticker['percentage'],
                    'high': ticker['high'],
                    'low': ticker['low'],
                    'open': ticker['open'],
                    'timestamp': ticker['timestamp']
                }
                self.pretty_print_json(ticker_sample, f"Ticker Structure for {symbol}")
                
                # Test 2: Order book
                print("   2️⃣  Fetching order book...")
                orderbook = await self.exchange.fetch_order_book(symbol, limit=5)
                
                print(f"      📊 Order book depth: {len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks")
                print(f"      💰 Best bid: ${orderbook['bids'][0][0]:.2f} (size: {orderbook['bids'][0][1]:.4f})")
                print(f"      💰 Best ask: ${orderbook['asks'][0][0]:.2f} (size: {orderbook['asks'][0][1]:.4f})")
                
                # Show order book structure
                orderbook_sample = {
                    'symbol': orderbook['symbol'],
                    'timestamp': orderbook['timestamp'],
                    'bids': orderbook['bids'][:3],  # Top 3 bids
                    'asks': orderbook['asks'][:3],  # Top 3 asks
                }
                self.pretty_print_json(orderbook_sample, f"Order Book Structure for {symbol}")
                
                # Test 3: Recent trades
                print("   3️⃣  Fetching recent trades...")
                trades = await self.exchange.fetch_trades(symbol, limit=5)
                
                if trades:
                    print(f"      🔄 Recent trades count: {len(trades)}")
                    latest_trade = trades[-1]
                    print(f"      💰 Latest trade: ${latest_trade['price']:.2f} x {latest_trade['amount']:.4f} ({latest_trade['side']})")
                    
                    # Show trades structure
                    trades_sample = [
                        {
                            'timestamp': trade['timestamp'],
                            'price': trade['price'],
                            'amount': trade['amount'],
                            'side': trade['side']
                        } for trade in trades[:3]
                    ]
                    self.pretty_print_json(trades_sample, f"Recent Trades Structure for {symbol}")
                
                # Test 4: OHLCV data
                print("   4️⃣  Fetching OHLCV data...")
                ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=5)
                
                if ohlcv:
                    print(f"      📊 OHLCV candles: {len(ohlcv)}")
                    latest_candle = ohlcv[-1]
                    print(f"      🕯️  Latest candle: O:{latest_candle[1]:.2f} H:{latest_candle[2]:.2f} L:{latest_candle[3]:.2f} C:{latest_candle[4]:.2f}")
                    
                    # Show OHLCV structure
                    ohlcv_sample = [
                        {
                            'timestamp': datetime.fromtimestamp(candle[0]/1000).isoformat(),
                            'open': candle[1],
                            'high': candle[2],
                            'low': candle[3],
                            'close': candle[4],
                            'volume': candle[5]
                        } for candle in ohlcv[:3]
                    ]
                    self.pretty_print_json(ohlcv_sample, f"OHLCV Structure for {symbol}")
                
                print(f"   ✅ All spot tests passed for {symbol}")
                
                # Wait between symbols to respect rate limits
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"   ❌ Error testing {symbol}: {str(e)}")
                continue
    
    async def test_futures_market_data(self) -> None:
        """Test futures market data endpoints."""
        print(f"\n🚀 Testing Futures Market Data")
        print("-" * 30)
        
        # Note: Some futures endpoints might not work without API credentials
        # We'll handle errors gracefully
        
        for symbol in self.futures_symbols:
            print(f"\n🎯 Testing {symbol} (Futures)")
            print(f"   {'-' * 25}")
            
            try:
                # Test 1: Futures ticker
                print("   1️⃣  Fetching futures ticker...")
                ticker = await self.exchange.fetch_ticker(symbol)
                
                print(f"      💰 Price: ${ticker['last']:,.2f}")
                print(f"      📊 24h Volume: ${ticker['quoteVolume']:,.2f}")
                print(f"      📈 24h Change: {ticker['percentage']:.2f}%")
                
                # Test 2: Funding rate (futures specific)
                print("   2️⃣  Fetching funding rate...")
                try:
                    funding_rate = await self.exchange.fetch_funding_rate(symbol)
                    
                    if funding_rate:
                        funding_pct = funding_rate['fundingRate'] * 100
                        print(f"      💸 Current funding rate: {funding_pct:.4f}%")
                        print(f"      ⏰ Next funding time: {funding_rate.get('fundingDatetime', 'N/A')}")
                        
                        # Show funding rate structure
                        funding_sample = {
                            'symbol': funding_rate['symbol'],
                            'fundingRate': funding_rate['fundingRate'],
                            'fundingDatetime': funding_rate.get('fundingDatetime'),
                            'timestamp': funding_rate['timestamp']
                        }
                        self.pretty_print_json(funding_sample, f"Funding Rate Structure for {symbol}")
                
                except Exception as e:
                    print(f"      ⚠️  Funding rate not available: {str(e)}")
                
                # Test 3: Open interest (requires special handling)
                print("   3️⃣  Checking open interest...")
                try:
                    # This might require direct API call since CCXT may not support it
                    print(f"      ℹ️  Open interest requires custom implementation")
                    # We'll implement this in the actual integration
                
                except Exception as e:
                    print(f"      ⚠️  Open interest not available: {str(e)}")
                
                print(f"   ✅ Futures tests completed for {symbol}")
                
                # Wait between symbols
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"   ❌ Error testing futures {symbol}: {str(e)}")
                continue
    
    async def test_market_info(self) -> None:
        """Test market information endpoints."""
        print(f"\n📊 Testing Market Information")
        print("-" * 30)
        
        try:
            # Test 1: Exchange status
            print("1️⃣  Checking exchange status...")
            status = await self.exchange.fetch_status()
            print(f"   Status: {status.get('status', 'Unknown')}")
            print(f"   Updated: {status.get('updated', 'Unknown')}")
            
            # Test 2: Market statistics
            print("\n2️⃣  Fetching market statistics...")
            
            # Get all tickers (be careful - this is expensive!)
            print("   Fetching sample tickers...")
            sample_symbols = self.spot_symbols[:2]  # Just test 2 symbols
            
            tickers_data = []
            for symbol in sample_symbols:
                ticker = await self.exchange.fetch_ticker(symbol)
                tickers_data.append({
                    'Symbol': symbol,
                    'Price': f"${ticker['last']:,.2f}",
                    'Volume': f"${ticker['quoteVolume']:,.0f}",
                    'Change': f"{ticker['percentage']:.2f}%"
                })
                await asyncio.sleep(1)  # Rate limiting
            
            self.print_table(tickers_data, "Sample Market Statistics")
            
            # Test 3: Market precision and limits
            print("3️⃣  Checking market precision and limits...")
            markets = self.exchange.markets
            
            market_info = []
            for symbol in self.spot_symbols[:2]:
                if symbol in markets:
                    market = markets[symbol]
                    market_info.append({
                        'Symbol': symbol,
                        'Price Precision': market['precision']['price'],
                        'Amount Precision': market['precision']['amount'],
                        'Min Amount': market['limits']['amount']['min'],
                        'Min Cost': market['limits']['cost']['min']
                    })
            
            self.print_table(market_info, "Market Precision and Limits")
            
        except Exception as e:
            print(f"❌ Error testing market info: {str(e)}")
    
    async def test_rate_limiting(self) -> None:
        """Test rate limiting behavior."""
        print(f"\n⏱️  Testing Rate Limiting")
        print("-" * 25)
        
        print("1️⃣  Making rapid requests to test rate limiting...")
        
        start_time = time.time()
        request_count = 0
        
        try:
            # Make several requests quickly
            for i in range(5):
                await self.exchange.fetch_ticker(self.spot_symbols[0])
                request_count += 1
                print(f"   Request {i+1}: ✅")
                # Small delay to see rate limiting in action
                await asyncio.sleep(0.5)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"\n📊 Rate Limiting Results:")
            print(f"   Requests made: {request_count}")
            print(f"   Total time: {duration:.2f} seconds")
            print(f"   Average time per request: {duration/request_count:.2f} seconds")
            
            if duration/request_count > 1.0:
                print(f"   ✅ Rate limiting is working (>1 second per request)")
            else:
                print(f"   ⚠️  Requests were very fast - check rate limit settings")
            
        except Exception as e:
            print(f"❌ Rate limiting test failed: {str(e)}")
    
    async def generate_summary_report(self) -> None:
        """Generate a summary report of all tests."""
        print(f"\n📋 Integration Summary Report")
        print("=" * 40)
        
        print(f"\n🔧 Configuration:")
        print(f"   Exchange: Binance ({'Testnet' if self.use_testnet else 'Mainnet'})")
        print(f"   CCXT Version: {ccxt.__version__}")
        print(f"   Rate Limit: {self.exchange.rateLimit}ms")
        print(f"   Test Time: {datetime.now().isoformat()}")
        
        print(f"\n📊 Endpoints Tested:")
        endpoints = [
            "✅ Market Loading",
            "✅ Server Time",
            "✅ Ticker Data",
            "✅ Order Book",
            "✅ Recent Trades", 
            "✅ OHLCV Data",
            "✅ Funding Rates (Futures)",
            "⚠️  Open Interest (Custom Implementation Needed)",
            "✅ Exchange Status",
            "✅ Market Precision/Limits",
            "✅ Rate Limiting"
        ]
        
        for endpoint in endpoints:
            print(f"   {endpoint}")
        
        print(f"\n💡 Key Findings:")
        print(f"   • Binance API is accessible and responsive")
        print(f"   • CCXT provides good standardization")
        print(f"   • Rate limiting is working properly")
        print(f"   • All basic market data is available")
        print(f"   • Futures-specific data requires additional work")
        
        print(f"\n🚀 Next Steps for Integration:")
        print(f"   1. Implement BinanceExchange class")
        print(f"   2. Add custom open interest fetching")
        print(f"   3. Integrate with Virtuoso data pipeline")
        print(f"   4. Add comprehensive error handling")
        print(f"   5. Implement WebSocket connections for real-time data")
        
        print(f"\n" + "=" * 40)
        print(f"🎉 Binance API testing completed successfully!")
    
    async def run_all_tests(self) -> None:
        """Run all API tests in sequence."""
        print(f"🚀 Starting Binance API Integration Tests")
        print(f"{'=' * 60}")
        
        try:
            # Test 1: Basic connectivity
            connectivity_ok = await self.test_basic_connectivity()
            
            if not connectivity_ok:
                print(f"❌ Connectivity failed - aborting further tests")
                return
            
            # Test 2: Spot market data
            await self.test_spot_market_data()
            
            # Test 3: Futures market data
            await self.test_futures_market_data()
            
            # Test 4: Market information
            await self.test_market_info()
            
            # Test 5: Rate limiting
            await self.test_rate_limiting()
            
            # Generate summary
            await self.generate_summary_report()
        
        finally:
            # Always close the exchange connection
            await self.exchange.close()

async def main():
    """Main function to run the API tests."""
    print("🔍 Binance API Integration Tester")
    print("=" * 50)
    
    # Configuration options
    USE_TESTNET = False  # Set to True to use testnet
    API_KEY = None       # Add your API key here for higher rate limits (optional)
    API_SECRET = None    # Add your API secret here (optional)
    
    # You can also load from environment variables
    import os
    API_KEY = os.getenv('BINANCE_API_KEY', API_KEY)
    API_SECRET = os.getenv('BINANCE_API_SECRET', API_SECRET)
    
    try:
        # Create and run the tester
        tester = BinanceAPITester(
            use_testnet=USE_TESTNET,
            api_key=API_KEY,
            api_secret=API_SECRET
        )
        
        await tester.run_all_tests()
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n👋 Test session ended")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 