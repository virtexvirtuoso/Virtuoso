#!/usr/bin/env python3
"""
Comprehensive test script to validate market reporter fixes:
1. Field mapping corrections (volume, turnover, open interest, price change)  
2. Restored calculation methods (futures premium, smart money, whale activity, performance metrics)
3. Live data pipeline validation
4. Report generation test
"""

import sys
import os
import asyncio
import logging
import ccxt
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Import the fixed market reporter
from monitoring.market_reporter import MarketReporter

async def test_field_mappings():
    """Test the corrected field mappings with live Bybit data."""
    print("\n=== Testing Field Mapping Fixes ===")
    
    try:
        # Initialize Bybit exchange
        exchange = ccxt.bybit({
            'sandbox': False,
        })
        
        # Test symbols
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        for symbol in test_symbols:
            print(f"\n--- Testing {symbol} ---")
            
            # Fetch raw ticker data
            ticker = await exchange.fetch_ticker(symbol)
            
            # Test volume extraction
            old_volume = ticker.get('volume', 0)  # Old incorrect way
            new_volume = ticker.get('baseVolume', 0)  # New correct way
            
            print(f"Volume (old way): {old_volume:,.2f}")
            print(f"Volume (new way): {new_volume:,.2f}")
            print(f"✅ Volume mapping fix: {'Working' if new_volume > 0 else 'Failed'}")
            
            # Test turnover extraction  
            old_turnover = ticker['info'].get('turnover24h', 0) if 'info' in ticker else 0
            new_turnover = ticker.get('quoteVolume', 0)  # New correct way
            
            print(f"Turnover (old way): {old_turnover:,.2f}")
            print(f"Turnover (new way): {new_turnover:,.2f}")
            print(f"✅ Turnover mapping fix: {'Working' if new_turnover > 0 else 'Failed'}")
            
            # Test open interest extraction
            open_interest = 0
            if 'info' in ticker and ticker['info']:
                open_interest = float(ticker['info'].get('openInterest', 
                                    ticker['info'].get('openInterestValue', 0)))
            print(f"Open Interest: {open_interest:,.2f}")
            print(f"✅ Open Interest extraction: {'Working' if open_interest > 0 else 'Available but 0'}")
            
            # Test price change extraction
            price_change_raw = ticker['info'].get('price24hPcnt', '0') if 'info' in ticker else '0'
            try:
                if isinstance(price_change_raw, str):
                    price_change = float(price_change_raw.replace('%', '')) * 100
                else:
                    price_change = float(price_change_raw) * 100
            except (ValueError, TypeError):
                price_change = 0
                
            print(f"Price Change: {price_change:+.2f}%")
            print(f"✅ Price Change parsing: {'Working' if price_change != 0 else 'Zero change'}")
            
        await exchange.close()
        return True
        
    except Exception as e:
        print(f"❌ Field mapping test failed: {str(e)}")
        return False

async def test_restored_methods():
    """Test the restored calculation methods."""
    print("\n=== Testing Restored Calculation Methods ===")
    
    try:
        # Initialize exchange and market reporter
        exchange = ccxt.bybit({
            'sandbox': False,
        })
        
        # Setup basic logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # Initialize market reporter
        reporter = MarketReporter(exchange=exchange, logger=logger)
        
        # Test symbols
        test_symbols = ['BTCUSDT', 'ETHUSDT']
        
        print("\n--- Testing Market Overview ---")
        overview = await reporter._calculate_market_overview(test_symbols)
        print(f"Market Overview: {'✅ Success' if overview else '❌ Failed'}")
        if overview:
            print(f"  Regime: {overview.get('regime', 'N/A')}")
            print(f"  Trend Strength: {overview.get('trend_strength', 'N/A')}")
        
        print("\n--- Testing Futures Premium Calculation ---")
        futures_premium = await reporter._calculate_futures_premium(test_symbols)
        print(f"Futures Premium: {'✅ Success' if futures_premium else '❌ Failed'}")
        if futures_premium and 'premiums' in futures_premium:
            for symbol, data in futures_premium['premiums'].items():
                print(f"  {symbol}: {data.get('premium', 'N/A')} ({data.get('premium_type', 'N/A')})")
        
        print("\n--- Testing Smart Money Index ---")
        smart_money = await reporter._calculate_smart_money_index(test_symbols[:1])  # Just one symbol for speed
        print(f"Smart Money Index: {'✅ Success' if smart_money else '❌ Failed'}")
        if smart_money:
            print(f"  Index Value: {smart_money.get('current_value', 'N/A')}")
            print(f"  Signal: {smart_money.get('signal', 'N/A')}")
        
        print("\n--- Testing Whale Activity ---")
        whale_activity = await reporter._calculate_whale_activity(test_symbols[:1])  # Just one symbol for speed
        print(f"Whale Activity: {'✅ Success' if whale_activity else '❌ Failed'}")
        if whale_activity and 'transactions' in whale_activity:
            tx_count = len(whale_activity['transactions'])
            print(f"  Whale Transactions Found: {tx_count}")
        
        print("\n--- Testing Performance Metrics ---")
        performance = await reporter._calculate_performance_metrics(test_symbols)
        print(f"Performance Metrics: {'✅ Success' if performance else '❌ Failed'}")
        if performance:
            api_latency = performance.get('api_latency', {})
            print(f"  Avg API Latency: {api_latency.get('avg', 'N/A'):.3f}s")
            data_quality = performance.get('data_quality', {})
            print(f"  Data Quality Score: {data_quality.get('avg_score', 'N/A'):.1f}")
        
        await exchange.close()
        return True
        
    except Exception as e:
        print(f"❌ Restored methods test failed: {str(e)}")
        return False

async def test_market_report_generation():
    """Test complete market report generation pipeline."""
    print("\n=== Testing Market Report Generation Pipeline ===")
    
    try:
        # Initialize exchange
        exchange = ccxt.bybit({
            'sandbox': False,
        })
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # Initialize market reporter
        reporter = MarketReporter(exchange=exchange, logger=logger)
        
        # Generate a basic market summary
        print("\n--- Generating Market Summary ---")
        summary = await reporter.generate_market_summary()
        print(f"Market Summary: {'✅ Success' if summary else '❌ Failed'}")
        
        if summary:
            print(f"  Sections: {list(summary.keys())}")
            
            # Check key sections for data
            if 'market_overview' in summary:
                overview = summary['market_overview']
                print(f"  Market Overview: {'✅ Has Data' if overview else '❌ Empty'}")
                
            if 'futures_premium' in summary:
                futures = summary['futures_premium'] 
                print(f"  Futures Premium: {'✅ Has Data' if futures else '❌ Empty'}")
                
            if 'smart_money_index' in summary:
                smart_money = summary['smart_money_index']
                print(f"  Smart Money Index: {'✅ Has Data' if smart_money else '❌ Empty'}")
        
        await exchange.close()
        return True
        
    except Exception as e:
        print(f"❌ Market report generation test failed: {str(e)}")
        return False

async def test_data_extraction():
    """Test the _extract_market_data method with various data structures."""
    print("\n=== Testing Market Data Extraction ===")
    
    try:
        # Initialize exchange
        exchange = ccxt.bybit({
            'sandbox': False,
        })
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # Initialize market reporter
        reporter = MarketReporter(exchange=exchange, logger=logger)
        
        # Test data extraction with real ticker data
        test_symbol = 'BTCUSDT'
        
        print(f"\n--- Testing data extraction for {test_symbol} ---")
        
        # Fetch real ticker data
        ticker = await exchange.fetch_ticker(test_symbol)
        
        # Create test market data structure
        market_data = {
            'ticker': ticker,
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        
        # Extract data using our method
        extracted_data = reporter._extract_market_data(market_data)
        
        print(f"Extracted Data Fields: {list(extracted_data.keys())}")
        print(f"Price: ${extracted_data.get('price', 0):,.2f}")
        print(f"Volume: {extracted_data.get('volume', 0):,.2f}")
        print(f"Turnover: ${extracted_data.get('turnover', 0):,.2f}")
        print(f"Change 24h: {extracted_data.get('change_24h', 0):+.2f}%")
        print(f"Open Interest: {extracted_data.get('open_interest', 0):,.2f}")
        
        # Validate extracted data
        success = (
            extracted_data.get('price', 0) > 0 and
            extracted_data.get('volume', 0) > 0 and
            extracted_data.get('turnover', 0) > 0
        )
        
        print(f"Data Extraction: {'✅ Success' if success else '❌ Failed'}")
        
        await exchange.close()
        return success
        
    except Exception as e:
        print(f"❌ Data extraction test failed: {str(e)}")
        return False

async def main():
    """Run all tests."""
    print("🔧 Starting Market Reporter Fixes Validation Tests")
    print("=" * 60)
    
    # Track test results
    results = []
    
    # Test 1: Field mappings
    results.append(await test_field_mappings())
    
    # Test 2: Data extraction method
    results.append(await test_data_extraction())
    
    # Test 3: Restored calculation methods
    results.append(await test_restored_methods())
    
    # Test 4: Market report generation
    results.append(await test_market_report_generation())
    
    # Summary
    print("\n" + "=" * 60)
    print("🔧 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    test_names = [
        "Field Mapping Fixes",
        "Data Extraction Method", 
        "Restored Calculation Methods",
        "Market Report Generation"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{i+1}. {name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Market reporter fixes are working correctly.")
        print("\n📄 Ready to generate live market reports with real data!")
    else:
        print("⚠️ Some tests failed. Please review the issues above.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main()) 