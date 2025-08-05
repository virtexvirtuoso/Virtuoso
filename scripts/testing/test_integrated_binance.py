#!/usr/bin/env python3
"""
Test script for the integrated Binance exchange client.

This script tests the comprehensive Binance exchange that combines:
- CCXT for spot market data
- Custom futures client for advanced features
- Symbol format handling utilities

Usage:
    python scripts/test_integrated_binance.py
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Import our integrated Binance exchange
from data_acquisition.binance.binance_exchange import BinanceExchange
from data_acquisition.binance.futures_client import BinanceSymbolConverter

class IntegratedBinanceExchangeTester:
    """Test the integrated Binance exchange client."""
    
    def __init__(self):
        """Initialize the tester."""
        self.test_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        self.results = {}
        
        print("🚀 Integrated Binance Exchange Tester")
        print("=" * 50)
        print("Testing comprehensive Binance integration:")
        print("  ✅ CCXT for spot market data")
        print("  ✅ Custom futures client for advanced features")
        print("  ✅ Symbol format conversion utilities")
        print("  ✅ Market sentiment calculation")
        print("-" * 50)
    
    def pretty_print_json(self, data, title: str = None):
        """Pretty print JSON data."""
        if title:
            print(f"\n📋 {title}")
            print("=" * len(title))
        
        print(json.dumps(data, indent=2, default=str))
        print()
    
    async def test_spot_market_data(self, exchange: BinanceExchange):
        """Test spot market data functionality via CCXT."""
        print("\n📈 Testing Spot Market Data (via CCXT)")
        print("-" * 42)
        
        test_symbol = 'BTC/USDT'
        
        try:
            print(f"🎯 Testing spot data for {test_symbol}")
            
            # Test ticker
            print("   1️⃣  Getting ticker data...")
            ticker = await exchange.get_ticker(test_symbol)
            print(f"      💰 Price: ${ticker['last']:,.2f}")
            print(f"      📊 Volume: {ticker['baseVolume']:,.0f} BTC")
            print(f"      📈 24h Change: {ticker['percentage']:+.2f}%")
            
            # Test order book
            print("   2️⃣  Getting order book...")
            orderbook = await exchange.get_order_book(test_symbol, limit=5)
            print(f"      📊 Best Bid: ${orderbook['bids'][0][0]:,.2f}")
            print(f"      📊 Best Ask: ${orderbook['asks'][0][0]:,.2f}")
            print(f"      📊 Spread: ${orderbook['asks'][0][0] - orderbook['bids'][0][0]:.2f}")
            
            # Test recent trades
            print("   3️⃣  Getting recent trades...")
            trades = await exchange.get_recent_trades(test_symbol, limit=5)
            print(f"      📈 Retrieved {len(trades)} recent trades")
            print(f"      💰 Latest Trade: ${trades[0]['price']:,.2f}")
            
            # Test OHLCV
            print("   4️⃣  Getting OHLCV data...")
            ohlcv = await exchange.get_ohlcv(test_symbol, '1h', limit=5)
            print(f"      📊 Retrieved {len(ohlcv)} hourly candles")
            latest_candle = ohlcv[-1]
            print(f"      📈 Latest Close: ${latest_candle[4]:,.2f}")
            
            print(f"   ✅ Spot market data test passed!")
            
            self.results['spot_data'] = {
                'success': True,
                'ticker_price': ticker['last'],
                'volume_24h': ticker['baseVolume'],
                'change_24h_pct': ticker['percentage'],
                'spread': orderbook['asks'][0][0] - orderbook['bids'][0][0],
                'trades_count': len(trades),
                'candles_count': len(ohlcv)
            }
            
        except Exception as e:
            print(f"   ❌ Error in spot data test: {str(e)}")
            self.results['spot_data'] = {'success': False, 'error': str(e)}
    
    async def test_futures_data(self, exchange: BinanceExchange):
        """Test futures-specific data functionality."""
        print("\n💸 Testing Futures Data (via Custom Client)")
        print("-" * 44)
        
        test_symbol = 'BTC/USDT'
        
        try:
            print(f"🎯 Testing futures data for {test_symbol}")
            
            # Test funding rate
            print("   1️⃣  Getting funding rate...")
            funding = await exchange.get_current_funding_rate(test_symbol)
            print(f"      💸 Current Rate: {funding['fundingRatePercentage']:+.4f}%")
            next_time = datetime.fromtimestamp(funding['nextFundingTime'] / 1000)
            print(f"      ⏰ Next Funding: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Test open interest
            print("   2️⃣  Getting open interest...")
            oi = await exchange.get_open_interest(test_symbol)
            print(f"      📊 Open Interest: {oi['openInterest']:,.0f}")
            oi_time = datetime.fromtimestamp(oi['timestamp'] / 1000)
            print(f"      ⏰ OI Timestamp: {oi_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Test premium index
            print("   3️⃣  Getting premium index...")
            premium = await exchange.get_premium_index(test_symbol)
            print(f"      📈 Mark Price: ${premium['markPrice']:,.2f}")
            print(f"      📊 Index Price: ${premium['indexPrice']:,.2f}")
            print(f"      💰 Premium: ${premium['markPrice'] - premium['indexPrice']:+.2f}")
            
            # Test futures ticker
            print("   4️⃣  Getting futures ticker...")
            futures_ticker = await exchange.get_futures_ticker(test_symbol)
            print(f"      💰 Futures Price: ${futures_ticker['lastPrice']:,.2f}")
            print(f"      📊 24h Volume: {futures_ticker['volume']:,.0f}")
            print(f"      📈 24h Change: {futures_ticker['priceChangePercent']:+.2f}%")
            
            print(f"   ✅ Futures data test passed!")
            
            self.results['futures_data'] = {
                'success': True,
                'funding_rate_pct': funding['fundingRatePercentage'],
                'open_interest': oi['openInterest'],
                'mark_price': premium['markPrice'],
                'index_price': premium['indexPrice'],
                'premium': premium['markPrice'] - premium['indexPrice'],
                'futures_price': futures_ticker['lastPrice'],
                'futures_volume': futures_ticker['volume']
            }
            
        except Exception as e:
            print(f"   ❌ Error in futures data test: {str(e)}")
            self.results['futures_data'] = {'success': False, 'error': str(e)}
    
    async def test_symbol_conversion(self, exchange: BinanceExchange):
        """Test symbol format conversion functionality."""
        print("\n🔄 Testing Symbol Format Conversion")
        print("-" * 37)
        
        test_cases = [
            ('BTC/USDT', 'futures', 'BTCUSDT'),
            ('ETH/USDT', 'futures', 'ETHUSDT'),
            ('BTCUSDT', 'spot', 'BTC/USDT'),
            ('ETHUSDT', 'spot', 'ETH/USDT'),
        ]
        
        conversion_results = []
        
        for input_symbol, target_format, expected in test_cases:
            result = exchange.convert_symbol(input_symbol, target_format)
            success = result == expected
            status = "✅" if success else "❌"
            
            print(f"   {status} {input_symbol} -> {target_format}: {result}")
            conversion_results.append(success)
        
        # Test format detection
        print(f"\n   🔍 Format Detection:")
        print(f"      BTC/USDT is futures: {exchange.is_futures_symbol('BTC/USDT')}")
        print(f"      BTCUSDT is futures: {exchange.is_futures_symbol('BTCUSDT')}")
        
        success_rate = (sum(conversion_results) / len(conversion_results)) * 100
        print(f"   📊 Conversion Success Rate: {success_rate:.0f}%")
        
        self.results['symbol_conversion'] = {
            'success': success_rate == 100,
            'success_rate': success_rate,
            'total_tests': len(conversion_results)
        }
    
    async def test_comprehensive_data(self, exchange: BinanceExchange):
        """Test comprehensive market data functionality."""
        print("\n📊 Testing Comprehensive Market Data")
        print("-" * 37)
        
        test_symbol = 'BTC/USDT'
        
        try:
            print(f"🎯 Getting comprehensive data for {test_symbol}")
            
            # Test complete market data
            print("   1️⃣  Getting complete market data...")
            complete_data = await exchange.get_complete_market_data(test_symbol)
            
            spot_data = complete_data['spot']
            futures_data = complete_data['futures']
            
            print(f"      ✅ Spot ticker: {spot_data['ticker'] is not None}")
            print(f"      ✅ Spot orderbook: {spot_data['orderbook'] is not None}")
            print(f"      ✅ Spot trades: {spot_data['recent_trades'] is not None}")
            print(f"      ✅ Spot OHLCV: {spot_data['ohlcv'] is not None}")
            print(f"      ✅ Futures data: {futures_data is not None}")
            
            if futures_data:
                print(f"      💰 Integrated Price: ${futures_data['ticker']['lastPrice']:,.2f}")
                print(f"      💸 Integrated Funding: {futures_data['funding']['fundingRatePercentage']:+.4f}%")
                print(f"      📊 Integrated OI: {futures_data['openInterest']['openInterest']:,.0f}")
            
            # Test market sentiment
            print("   2️⃣  Getting market sentiment...")
            sentiment = await exchange.get_market_sentiment(test_symbol)
            
            print(f"      😊 Sentiment Score: {sentiment['sentiment_score']:+.3f}")
            print(f"      💸 Funding Rate: {sentiment['funding_rate_percentage']:+.4f}%")
            print(f"      📊 Open Interest: {sentiment['open_interest']:,.0f}")
            print(f"      💰 Premium: ${sentiment['premium']:+.2f}")
            print(f"      📈 Premium %: {sentiment['premium_percentage']:+.4f}%")
            
            # Sample the comprehensive data
            comprehensive_sample = {
                'symbol': complete_data['symbol'],
                'spot_price': spot_data['ticker']['last'] if spot_data['ticker'] else None,
                'futures_price': futures_data['ticker']['lastPrice'] if futures_data else None,
                'funding_rate_pct': futures_data['funding']['fundingRatePercentage'] if futures_data else None,
                'open_interest': futures_data['openInterest']['openInterest'] if futures_data else None,
                'sentiment_score': sentiment['sentiment_score'],
                'data_sections': len(complete_data)
            }
            
            self.pretty_print_json(comprehensive_sample, f"Comprehensive Market Data Sample for {test_symbol}")
            
            print(f"   ✅ Comprehensive data test passed!")
            
            self.results['comprehensive_data'] = {
                'success': True,
                'has_spot_data': spot_data['ticker'] is not None,
                'has_futures_data': futures_data is not None,
                'sentiment_score': sentiment['sentiment_score'],
                'data_sections': len(complete_data)
            }
            
        except Exception as e:
            print(f"   ❌ Error in comprehensive data test: {str(e)}")
            self.results['comprehensive_data'] = {'success': False, 'error': str(e)}
    
    async def test_exchange_info(self, exchange: BinanceExchange):
        """Test exchange information functionality."""
        print("\n📋 Testing Exchange Information")
        print("-" * 32)
        
        try:
            print("🎯 Getting exchange information...")
            
            info = await exchange.get_exchange_info()
            
            print(f"   📊 Exchange: {info['exchange']}")
            print(f"   📈 Total Markets: {info['total_markets']:,}")
            print(f"   💱 Spot Markets: {info['spot_markets']:,}")
            print(f"   🔮 Futures Markets: {info['futures_markets']:,}")
            print(f"   ✅ Status: {info['status']}")
            
            print(f"\n   🔧 Features:")
            for feature, available in info['features'].items():
                status = "✅" if available else "❌"
                print(f"      {status} {feature.replace('_', ' ').title()}")
            
            print(f"   ✅ Exchange info test passed!")
            
            self.results['exchange_info'] = {
                'success': True,
                'total_markets': info['total_markets'],
                'spot_markets': info['spot_markets'],
                'futures_markets': info['futures_markets'],
                'all_features_available': all(info['features'].values())
            }
            
        except Exception as e:
            print(f"   ❌ Error in exchange info test: {str(e)}")
            self.results['exchange_info'] = {'success': False, 'error': str(e)}
    
    async def generate_final_report(self):
        """Generate final test report."""
        print("\n📋 Final Integration Test Report")
        print("=" * 35)
        
        print(f"\n🔧 Test Configuration:")
        print(f"   Test Date: {datetime.now().isoformat()}")
        print(f"   Test Symbols: {', '.join(self.test_symbols)}")
        print(f"   Integration Components: CCXT + Custom Futures Client")
        
        # Calculate overall success
        test_categories = ['spot_data', 'futures_data', 'symbol_conversion', 'comprehensive_data', 'exchange_info']
        successful_tests = sum(1 for category in test_categories if self.results.get(category, {}).get('success', False))
        total_tests = len(test_categories)
        
        print(f"\n📊 Test Results Summary:")
        for category in test_categories:
            result = self.results.get(category, {})
            success = result.get('success', False)
            status = "✅ PASSED" if success else "❌ FAILED"
            category_name = category.replace('_', ' ').title()
            print(f"   {status} {category_name}")
            
            if not success and 'error' in result:
                print(f"        Error: {result['error']}")
        
        success_rate = (successful_tests / total_tests) * 100
        print(f"\n💡 Overall Results:")
        print(f"   Successful Tests: {successful_tests}/{total_tests} ({success_rate:.1f}%)")
        
        if success_rate == 100:
            print(f"   🎉 ALL INTEGRATION TESTS PASSED!")
            print(f"   ✅ Binance integration is ready for production")
            print(f"   ✅ All three original issues have been resolved:")
            print(f"      ✅ Futures funding rates working")
            print(f"      ✅ Open interest data available")
            print(f"      ✅ Symbol format conversion functional")
        elif success_rate >= 80:
            print(f"   🟨 MOST TESTS PASSED - Minor issues remain")
            print(f"   ⚠️  Review failed tests before production deployment")
        else:
            print(f"   🔴 SIGNIFICANT ISSUES DETECTED")
            print(f"   ❌ Integration needs fixes before production")
        
        print(f"\n🚀 Next Steps:")
        if success_rate == 100:
            print(f"   1. Deploy integrated Binance client to Virtuoso")
            print(f"   2. Update configuration files")
            print(f"   3. Monitor production performance")
            print(f"   4. Add WebSocket support for real-time data")
        else:
            print(f"   1. Fix failing test categories")
            print(f"   2. Re-run integration tests")
            print(f"   3. Address error handling edge cases")
            print(f"   4. Implement fallback mechanisms")
    
    async def run_all_tests(self):
        """Run all integration tests."""
        print(f"🧪 Starting Integrated Binance Exchange Tests")
        print(f"{'=' * 65}")
        
        async with BinanceExchange() as exchange:
            # Run all test categories
            await self.test_spot_market_data(exchange)
            await self.test_futures_data(exchange)
            await self.test_symbol_conversion(exchange)
            await self.test_comprehensive_data(exchange)
            await self.test_exchange_info(exchange)
            
            # Generate final report
            await self.generate_final_report()

async def main():
    """Main function."""
    try:
        tester = IntegratedBinanceExchangeTester()
        await tester.run_all_tests()
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n👋 Integration test session ended")

if __name__ == "__main__":
    asyncio.run(main()) 