#!/usr/bin/env python3
"""
Test script for Binance Futures fixes.

This script tests the custom implementations that fix the three key issues:
1. Futures Funding Rates via direct API calls
2. Open Interest via direct API calls  
3. Symbol Format Handling between spot/futures formats

Usage:
    python scripts/test_binance_futures_fixes.py
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add the src directory to Python path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Import our custom futures client
from data_acquisition.binance.futures_client import BinanceFuturesClient, BinanceSymbolConverter

class BinanceFuturesFixTester:
    """Test our custom Binance futures implementation fixes."""
    
    def __init__(self):
        """Initialize the tester."""
        self.test_symbols = {
            'spot': ['BTC/USDT', 'ETH/USDT', 'BNB/USDT'],
            'futures': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        }
        self.results = {}
        
        print("🔧 Binance Futures Fixes Tester")
        print("=" * 50)
        print(f"Testing fixes for:")
        print(f"  1. ✅ Futures Funding Rates (custom API calls)")
        print(f"  2. ✅ Open Interest (custom API calls)")  
        print(f"  3. ✅ Symbol Format Handling (conversion utilities)")
        print("-" * 50)
    
    def pretty_print_json(self, data, title: str = None):
        """Pretty print JSON data."""
        if title:
            print(f"\n📋 {title}")
            print("=" * len(title))
        
        print(json.dumps(data, indent=2, default=str))
        print()
    
    async def test_symbol_conversion(self):
        """Test Fix #3: Symbol Format Handling."""
        print("\n🔄 Testing Fix #3: Symbol Format Handling")
        print("-" * 45)
        
        converter = BinanceSymbolConverter()
        
        # Test cases for conversion
        test_cases = [
            # (input, target_format, expected_output)
            ('BTC/USDT', 'futures', 'BTCUSDT'),
            ('ETH/USDT', 'futures', 'ETHUSDT'),
            ('BNB/USDT', 'futures', 'BNBUSDT'),
            ('BTCUSDT', 'spot', 'BTC/USDT'),
            ('ETHUSDT', 'spot', 'ETH/USDT'),
            ('BNBUSDT', 'spot', 'BNB/USDT'),
        ]
        
        conversion_results = []
        
        print("1️⃣  Testing Symbol Conversion:")
        for input_symbol, target_format, expected in test_cases:
            try:
                result = converter.normalize_symbol(input_symbol, target_format)
                success = result == expected
                status = "✅" if success else "❌"
                
                print(f"   {status} {input_symbol} -> {target_format}: {result}")
                
                conversion_results.append({
                    'input': input_symbol,
                    'target_format': target_format,
                    'expected': expected,
                    'actual': result,
                    'success': success
                })
                
            except Exception as e:
                print(f"   ❌ Error converting {input_symbol}: {str(e)}")
                conversion_results.append({
                    'input': input_symbol,
                    'target_format': target_format,
                    'expected': expected,
                    'actual': None,
                    'success': False,
                    'error': str(e)
                })
        
        print("\n2️⃣  Testing Format Detection:")
        format_tests = [
            ('BTC/USDT', False),  # Spot format, not futures
            ('BTCUSDT', True),    # Futures format
            ('ETH/USDT', False),  # Spot format
            ('ETHUSDT', True),    # Futures format
        ]
        
        for symbol, expected_is_futures in format_tests:
            is_futures = converter.is_futures_symbol(symbol)
            status = "✅" if is_futures == expected_is_futures else "❌"
            format_type = "futures" if is_futures else "spot"
            print(f"   {status} {symbol} -> {format_type} format")
        
        # Store results
        self.results['symbol_conversion'] = {
            'conversion_tests': conversion_results,
            'format_detection_tests': format_tests,
            'total_tests': len(conversion_results) + len(format_tests),
            'passed_tests': sum(1 for r in conversion_results if r['success']) + sum(1 for s, e in format_tests if converter.is_futures_symbol(s) == e)
        }
        
        success_rate = (self.results['symbol_conversion']['passed_tests'] / self.results['symbol_conversion']['total_tests']) * 100
        print(f"\n📊 Symbol Conversion Test Results: {success_rate:.1f}% success rate")
    
    async def test_funding_rates(self):
        """Test Fix #1: Futures Funding Rates via custom API calls."""
        print("\n💸 Testing Fix #1: Futures Funding Rates")
        print("-" * 42)
        
        funding_results = []
        
        async with BinanceFuturesClient() as client:
            for symbol in self.test_symbols['futures']:
                print(f"\n🎯 Testing funding rate for {symbol}")
                print(f"   {'-' * 25}")
                
                try:
                    # Test current funding rate
                    print("   1️⃣  Fetching current funding rate...")
                    funding = await client.get_current_funding_rate(symbol)
                    
                    # Display results
                    rate_pct = funding['fundingRatePercentage']
                    next_time = datetime.fromtimestamp(funding['nextFundingTime'] / 1000)
                    
                    print(f"      💸 Current Rate: {rate_pct:+.4f}%")
                    print(f"      ⏰ Next Funding: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"      📊 Raw Rate: {funding['fundingRate']:.8f}")
                    
                    # Test historical funding rates
                    print("   2️⃣  Fetching historical funding rates...")
                    historical = await client.get_funding_rate(symbol, limit=3)
                    
                    print(f"      📈 Retrieved {len(historical)} historical records")
                    
                    # Show sample data structure
                    funding_sample = {
                        'symbol': funding['symbol'],
                        'currentRate': funding['fundingRate'],
                        'percentage': funding['fundingRatePercentage'],
                        'nextFundingTime': funding['nextFundingTime'],
                        'historicalCount': len(historical)
                    }
                    
                    self.pretty_print_json(funding_sample, f"Funding Rate Data for {symbol}")
                    
                    print(f"   ✅ Funding rate test passed for {symbol}")
                    
                    funding_results.append({
                        'symbol': symbol,
                        'success': True,
                        'current_rate': funding['fundingRate'],
                        'percentage': funding['fundingRatePercentage'],
                        'historical_count': len(historical)
                    })
                    
                except Exception as e:
                    print(f"   ❌ Error getting funding rate for {symbol}: {str(e)}")
                    funding_results.append({
                        'symbol': symbol,
                        'success': False,
                        'error': str(e)
                    })
        
        # Store results
        self.results['funding_rates'] = {
            'results': funding_results,
            'total_symbols': len(self.test_symbols['futures']),
            'successful_symbols': sum(1 for r in funding_results if r['success'])
        }
        
        success_rate = (self.results['funding_rates']['successful_symbols'] / self.results['funding_rates']['total_symbols']) * 100
        print(f"\n📊 Funding Rates Test Results: {success_rate:.1f}% success rate")
    
    async def test_open_interest(self):
        """Test Fix #2: Open Interest via custom API calls."""
        print("\n📊 Testing Fix #2: Open Interest")
        print("-" * 35)
        
        oi_results = []
        
        async with BinanceFuturesClient() as client:
            for symbol in self.test_symbols['futures']:
                print(f"\n🎯 Testing open interest for {symbol}")
                print(f"   {'-' * 30}")
                
                try:
                    # Test open interest
                    print("   1️⃣  Fetching open interest...")
                    oi = await client.get_open_interest(symbol)
                    
                    # Display results
                    oi_value = oi['openInterest']
                    timestamp = datetime.fromtimestamp(oi['timestamp'] / 1000)
                    
                    print(f"      📊 Open Interest: {oi_value:,.0f}")
                    print(f"      ⏰ Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Show sample data structure
                    oi_sample = {
                        'symbol': oi['symbol'],
                        'openInterest': oi['openInterest'],
                        'timestamp': oi['timestamp'],
                        'formatted_time': timestamp.isoformat()
                    }
                    
                    self.pretty_print_json(oi_sample, f"Open Interest Data for {symbol}")
                    
                    print(f"   ✅ Open interest test passed for {symbol}")
                    
                    oi_results.append({
                        'symbol': symbol,
                        'success': True,
                        'open_interest': oi['openInterest'],
                        'timestamp': oi['timestamp']
                    })
                    
                except Exception as e:
                    print(f"   ❌ Error getting open interest for {symbol}: {str(e)}")
                    oi_results.append({
                        'symbol': symbol,
                        'success': False,
                        'error': str(e)
                    })
        
        # Store results
        self.results['open_interest'] = {
            'results': oi_results,
            'total_symbols': len(self.test_symbols['futures']),
            'successful_symbols': sum(1 for r in oi_results if r['success'])
        }
        
        success_rate = (self.results['open_interest']['successful_symbols'] / self.results['open_interest']['total_symbols']) * 100
        print(f"\n📊 Open Interest Test Results: {success_rate:.1f}% success rate")
    
    async def test_comprehensive_futures_data(self):
        """Test comprehensive futures data integration."""
        print("\n🚀 Testing Comprehensive Futures Data Integration")
        print("-" * 52)
        
        async with BinanceFuturesClient() as client:
            # Test one symbol with all data
            test_symbol = 'BTCUSDT'
            print(f"\n🎯 Testing complete futures data for {test_symbol}")
            print(f"   {'-' * 35}")
            
            try:
                print("   1️⃣  Fetching comprehensive futures market data...")
                market_data = await client.get_futures_market_data(test_symbol)
                
                # Display key metrics
                ticker = market_data['ticker']
                funding = market_data['funding']
                oi = market_data['openInterest']
                sentiment = market_data['sentiment']
                
                print(f"      💰 Price: ${ticker['lastPrice']:,.2f}")
                print(f"      📈 24h Change: {ticker['priceChangePercent']:+.2f}%")
                print(f"      💸 Funding Rate: {funding['fundingRatePercentage']:+.4f}%")
                print(f"      📊 Open Interest: {oi['openInterest']:,.0f}")
                print(f"      📊 Volume: {ticker['volume']:,.0f}")
                
                # Show comprehensive data structure
                comprehensive_sample = {
                    'symbol': market_data['symbol'],
                    'price': ticker['lastPrice'],
                    'change_24h_pct': ticker['priceChangePercent'],
                    'volume_24h': ticker['volume'],
                    'funding_rate_pct': funding['fundingRatePercentage'],
                    'open_interest': oi['openInterest'],
                    'sentiment_score': sentiment['fundingRate'] * 100,
                    'data_timestamp': market_data['timestamp']
                }
                
                self.pretty_print_json(comprehensive_sample, f"Comprehensive Futures Data for {test_symbol}")
                
                print(f"   ✅ Comprehensive futures data test passed!")
                
                self.results['comprehensive'] = {
                    'success': True,
                    'symbol': test_symbol,
                    'data_points': len(comprehensive_sample),
                    'sample': comprehensive_sample
                }
                
            except Exception as e:
                print(f"   ❌ Error getting comprehensive data: {str(e)}")
                self.results['comprehensive'] = {
                    'success': False,
                    'error': str(e)
                }
    
    async def generate_final_report(self):
        """Generate final test report."""
        print("\n📋 Final Test Report")
        print("=" * 30)
        
        print(f"\n🔧 Test Configuration:")
        print(f"   Test Date: {datetime.now().isoformat()}")
        print(f"   Spot Symbols: {', '.join(self.test_symbols['spot'])}")
        print(f"   Futures Symbols: {', '.join(self.test_symbols['futures'])}")
        
        print(f"\n✅ Fix #1: Futures Funding Rates")
        funding_success = self.results.get('funding_rates', {}).get('successful_symbols', 0)
        funding_total = self.results.get('funding_rates', {}).get('total_symbols', 0)
        print(f"   Success Rate: {funding_success}/{funding_total} symbols ({(funding_success/funding_total*100 if funding_total > 0 else 0):.1f}%)")
        print(f"   Status: {'✅ FIXED' if funding_success == funding_total else '⚠️ PARTIAL'}")
        
        print(f"\n✅ Fix #2: Open Interest")
        oi_success = self.results.get('open_interest', {}).get('successful_symbols', 0)
        oi_total = self.results.get('open_interest', {}).get('total_symbols', 0)
        print(f"   Success Rate: {oi_success}/{oi_total} symbols ({(oi_success/oi_total*100 if oi_total > 0 else 0):.1f}%)")
        print(f"   Status: {'✅ FIXED' if oi_success == oi_total else '⚠️ PARTIAL'}")
        
        print(f"\n✅ Fix #3: Symbol Format Handling")
        symbol_success = self.results.get('symbol_conversion', {}).get('passed_tests', 0)
        symbol_total = self.results.get('symbol_conversion', {}).get('total_tests', 0)
        print(f"   Success Rate: {symbol_success}/{symbol_total} tests ({(symbol_success/symbol_total*100 if symbol_total > 0 else 0):.1f}%)")
        print(f"   Status: {'✅ FIXED' if symbol_success == symbol_total else '⚠️ PARTIAL'}")
        
        print(f"\n🚀 Comprehensive Integration")
        comp_success = self.results.get('comprehensive', {}).get('success', False)
        print(f"   Status: {'✅ WORKING' if comp_success else '❌ FAILED'}")
        
        print(f"\n💡 Summary:")
        total_fixes = 3
        working_fixes = sum([
            1 if funding_success == funding_total else 0,
            1 if oi_success == oi_total else 0,
            1 if symbol_success == symbol_total else 0
        ])
        
        print(f"   Fixed Issues: {working_fixes}/{total_fixes} ({working_fixes/total_fixes*100:.1f}%)")
        
        if working_fixes == total_fixes:
            print(f"   🎉 ALL BINANCE FUTURES ISSUES FIXED!")
            print(f"   ✅ Ready for production integration")
        else:
            print(f"   ⚠️  Some issues remain - review failed tests above")
        
        print(f"\n🚀 Next Steps:")
        print(f"   1. Integrate custom futures client into BinanceExchange class")
        print(f"   2. Update Virtuoso configuration to use new features")
        print(f"   3. Add comprehensive error handling and fallbacks")
        print(f"   4. Deploy to production with monitoring")
    
    async def run_all_tests(self):
        """Run all fix tests."""
        print(f"🧪 Starting Binance Futures Fixes Tests")
        print(f"{'=' * 60}")
        
        # Test all fixes
        await self.test_symbol_conversion()
        await self.test_funding_rates()
        await self.test_open_interest()
        await self.test_comprehensive_futures_data()
        
        # Generate final report
        await self.generate_final_report()

async def main():
    """Main function."""
    try:
        tester = BinanceFuturesFixTester()
        await tester.run_all_tests()
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n👋 Test session ended")

if __name__ == "__main__":
    asyncio.run(main()) 