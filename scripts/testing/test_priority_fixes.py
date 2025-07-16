#!/usr/bin/env python3
"""
Priority Fixes Verification Test

Tests the three priority fixes:
1. Symbol format correction (Priority 1)
2. Optimized API retry logic with circuit breaker (Priority 2) 
3. PDF template configuration with dark theme (Priority 3)
"""

import sys
import os
import asyncio
import logging
import ccxt
import time

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

async def test_priority_fixes():
    """Test all priority fixes implemented."""
    
    print("🔧 Testing Priority Fixes Implementation...")
    print("=" * 60)
    
    results = {
        'symbol_format': False,
        'api_retry': False, 
        'pdf_template': False,
        'live_data': False,
        'market_summary': False
    }
    
    try:
        # Import MarketReporter
        from monitoring.market_reporter import MarketReporter
        
        # Initialize Bybit exchange
        exchange = ccxt.bybit({
            'sandbox': False,
            'enableRateLimit': True,
            'timeout': 10000,
        })
        
        print("✅ Exchange initialized successfully")
        
        # Test 1: Symbol Format Fix
        print("\n🔍 Test 1: Symbol Format Correction")
        reporter = MarketReporter(exchange=exchange)
        
        # Check default symbols are in correct format
        print(f"   Default symbols: {reporter.symbols}")
        
        # Test symbol conversion method
        test_symbols = ['BTC/USDT:USDT', 'ETHUSDT', 'ETH/USDT']
        for symbol in test_symbols:
            converted = reporter._convert_symbol_format(symbol)
            bybit_fmt, ccxt_fmt = reporter._detect_symbol_format(symbol)
            print(f"   {symbol} → {converted} (Bybit: {bybit_fmt}, CCXT: {ccxt_fmt})")
        
        # Verify symbols are in correct format (no slashes/colons)
        correct_format = all('/' not in s and ':' not in s for s in reporter.symbols)
        if correct_format:
            print("   ✅ Symbol format fix verified")
            results['symbol_format'] = True
        else:
            print("   ❌ Symbol format still incorrect")
        
        # Test 2: API Retry with Circuit Breaker
        print("\n⚡ Test 2: Optimized API Retry Logic")
        
        # Test successful API call with symbol format auto-correction
        try:
            start_time = time.time()
            # This should auto-correct symbol format internally
            ticker = await reporter._fetch_with_retry('fetch_ticker', 'BTCUSDT', timeout=5)
            duration = time.time() - start_time
            
            if ticker and 'last' in ticker:
                print(f"   ✅ API retry with timeout optimization: {duration:.2f}s")
                print(f"   📊 BTC Price: ${ticker['last']:,.2f}")
                results['api_retry'] = True
            else:
                print(f"   ⚠️ API call succeeded but ticker format unexpected")
                
        except Exception as e:
            print(f"   ❌ API retry failed: {e}")
        
        # Test circuit breaker initialization
        if hasattr(reporter, '_circuit_breaker'):
            print("   ✅ Circuit breaker initialized")
        else:
            print("   ❌ Circuit breaker not found")
        
        # Test 3: PDF Template Configuration
        print("\n📄 Test 3: PDF Template Configuration")
        
        # Check PDF configuration
        if hasattr(reporter, 'default_template'):
            template = reporter.default_template
            print(f"   Default template: {template}")
            
            if template == "market_report_dark.html":
                print("   ✅ Dark theme template configured")
                results['pdf_template'] = True
            else:
                print(f"   ⚠️ Template not set to dark theme: {template}")
        else:
            print("   ❌ Default template not configured")
            
        # Check if PDF generation is enabled
        if hasattr(reporter, 'pdf_enabled'):
            print(f"   PDF generation enabled: {reporter.pdf_enabled}")
        
        # Test 4: Live Data Collection
        print("\n📈 Test 4: Live Data Collection")
        
        try:
            # Test live data collection with multiple symbols
            symbols_to_test = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
            collected_data = {}
            
            for symbol in symbols_to_test:
                try:
                    ticker = await reporter._fetch_with_retry('fetch_ticker', symbol)
                    collected_data[symbol] = {
                        'price': ticker.get('last', 0),
                        'volume': ticker.get('baseVolume', 0),
                        'turnover': ticker.get('quoteVolume', 0)
                    }
                    print(f"   {symbol}: ${ticker.get('last', 0):,.2f} | Vol: {ticker.get('baseVolume', 0):,.0f}")
                except Exception as e:
                    print(f"   ❌ {symbol} failed: {e}")
                    
            if len(collected_data) >= 2:
                print("   ✅ Live data collection successful")
                results['live_data'] = True
            else:
                print("   ❌ Live data collection failed for most symbols")
                
        except Exception as e:
            print(f"   ❌ Live data test failed: {e}")
        
        # Test 5: Market Summary Generation
        print("\n📊 Test 5: Complete Market Summary Generation")
        
        try:
            start_time = time.time()
            summary = await reporter.generate_market_summary()
            duration = time.time() - start_time
            
            if summary and 'timestamp' in summary:
                print(f"   ✅ Market summary generated in {duration:.2f}s")
                
                # Check key sections
                sections = ['market_overview', 'futures_premium', 'smart_money_index', 'whale_activity']
                available_sections = []
                
                for section in sections:
                    if section in summary and summary[section]:
                        available_sections.append(section)
                        
                print(f"   📋 Available sections: {', '.join(available_sections)}")
                
                if len(available_sections) >= 3:
                    print("   ✅ Comprehensive market summary with most sections")
                    results['market_summary'] = True
                else:
                    print("   ⚠️ Market summary missing some sections")
                    
            else:
                print("   ❌ Market summary generation failed")
                
        except Exception as e:
            print(f"   ❌ Market summary test failed: {e}")
    
    except Exception as e:
        print(f"❌ Critical error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    # Results Summary
    print("\n" + "=" * 60)
    print("🎯 PRIORITY FIXES TEST RESULTS")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test.replace('_', ' ').title():<25} {status}")
    
    print(f"\nOverall Score: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
    
    if passed_tests == total_tests:
        print("🎉 ALL PRIORITY FIXES WORKING PERFECTLY!")
    elif passed_tests >= 4:
        print("🚀 MOST FIXES WORKING - READY FOR PRODUCTION!")
    elif passed_tests >= 3:
        print("⚡ MAJOR FIXES WORKING - GOOD PROGRESS!")
    else:
        print("🔧 MORE FIXES NEEDED")
        
    return passed_tests, total_tests

if __name__ == "__main__":
    asyncio.run(test_priority_fixes()) 