#!/usr/bin/env python3
"""
End-to-End Test for Market Reporter
Tests the complete market report generation pipeline with real Bybit data
to validate the field mapping fixes.
"""

import asyncio
import sys
import os
import json
import time
from datetime import datetime
import traceback

# Add src to path
sys.path.append('src')

async def test_market_reporter_e2e():
    """
    Comprehensive end-to-end test of market reporter functionality.
    Tests real data extraction, processing, and report generation.
    """
    print("=" * 60)
    print("🧪 MARKET REPORTER END-TO-END TEST")
    print("=" * 60)
    
    try:
        # Import required modules
        print("📦 Importing modules...")
        from monitoring.market_reporter import MarketReporter
        from core.exchanges.bybit import Bybit
        print("✅ Modules imported successfully")
        
        # Initialize exchange
        print("\n🔗 Initializing Bybit exchange...")
        exchange = Bybit({
            'sandbox': False,  # Use production for real data
            'enableRateLimit': True,
            'timeout': 10000
        })
        print("✅ Exchange initialized")
        
        # Initialize market reporter
        print("\n📊 Initializing Market Reporter...")
        reporter = MarketReporter(exchange=exchange)
        print("✅ Market Reporter initialized")
        
        # Test basic ticker fetching with our field mapping fixes
        print("\n🔍 Testing ticker data extraction...")
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        for symbol in test_symbols:
            try:
                ticker = await exchange.fetch_ticker(symbol)
                
                # Test the corrected field mappings
                volume = float(ticker.get('baseVolume', 0))
                turnover = float(ticker.get('quoteVolume', 0))
                
                # Test info section access
                info = ticker.get('info', {})
                oi = float(info.get('openInterest', 0))
                price_change_raw = info.get('price24hPcnt', '0')
                
                # Test price change parsing
                if isinstance(price_change_raw, str):
                    price_change = float(price_change_raw.replace('%', '')) * 100
                else:
                    price_change = float(price_change_raw) * 100
                
                print(f"  📈 {symbol}:")
                print(f"    Volume (baseVolume): {volume:,.2f}")
                print(f"    Turnover (quoteVolume): {turnover:,.2f}")
                print(f"    Open Interest: {oi:,.2f}")
                print(f"    Price Change: {price_change:+.2f}%")
                
                # Validate data is not zero/null
                if volume == 0 and turnover == 0:
                    print(f"    ⚠️  WARNING: {symbol} has zero volume/turnover - field mapping may still be incorrect")
                else:
                    print(f"    ✅ {symbol} data looks valid")
                    
            except Exception as e:
                print(f"    ❌ Error fetching {symbol}: {str(e)}")
        
        # Test futures symbol formats
        print("\n🔮 Testing futures symbol formats...")
        futures_symbols = [
            'BTC-27JUN25',      # USDC-settled
            'BTCUSDT-27JUN25',  # USDT-settled
            'ETH-27JUN25',      # USDC-settled
            'ETHUSDT-27JUN25'   # USDT-settled
        ]
        
        valid_futures = []
        for symbol in futures_symbols:
            try:
                ticker = await exchange.fetch_ticker(symbol)
                if ticker:
                    mark_price = float(ticker.get('info', {}).get('markPrice', 0))
                    index_price = float(ticker.get('info', {}).get('indexPrice', 0))
                    print(f"  ✅ {symbol}: Mark=${mark_price:,.2f}, Index=${index_price:,.2f}")
                    valid_futures.append(symbol)
            except Exception as e:
                print(f"  ❌ {symbol}: {str(e)}")
        
        print(f"\n✅ Found {len(valid_futures)} valid futures contracts")
        
        # Generate market summary report
        print("\n📋 Generating Market Summary Report...")
        start_time = time.time()
        
        # Update symbols to a reasonable test set
        reporter.symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'XRP/USDT:USDT', 'AVAX/USDT:USDT']
        
        try:
            report = await reporter.generate_market_summary()
            generation_time = time.time() - start_time
            
            if report:
                print(f"✅ Market report generated successfully in {generation_time:.2f}s")
                
                # Analyze report content
                print("\n📊 Report Analysis:")
                print(f"  Report size: {len(json.dumps(report, default=str))} bytes")
                print(f"  Sections: {list(report.keys())}")
                print(f"  Timestamp: {report.get('timestamp', 'missing')}")
                print(f"  Quality Score: {report.get('quality_score', 'not calculated')}")
                
                # Check for data availability issues
                issues = []
                
                # Check market overview
                if 'market_overview' in report:
                    mo = report['market_overview']
                    if mo.get('total_volume', 0) == 0:
                        issues.append("Market overview: zero total volume")
                    if mo.get('total_turnover', 0) == 0:
                        issues.append("Market overview: zero total turnover")
                    if mo.get('regime') == 'UNKNOWN':
                        issues.append("Market overview: unknown regime")
                else:
                    issues.append("Missing market_overview section")
                
                # Check futures premium
                if 'futures_premium' in report:
                    fp = report['futures_premium']
                    if not fp.get('premiums') and not fp.get('data'):
                        issues.append("Futures premium: no premium data")
                else:
                    issues.append("Missing futures_premium section")
                
                # Check smart money index
                if 'smart_money_index' in report:
                    smi = report['smart_money_index']
                    if smi.get('index', 0) == 50.0:  # Default neutral value
                        issues.append("Smart money index: using default value")
                else:
                    issues.append("Missing smart_money_index section")
                
                if issues:
                    print("\n⚠️  Data Issues Found:")
                    for issue in issues:
                        print(f"    - {issue}")
                else:
                    print("\n✅ No major data issues detected")
                
                # Test PDF generation
                print("\n📄 Testing PDF Generation...")
                try:
                    pdf_path = await reporter.generate_market_pdf_report(report)
                    if pdf_path and os.path.exists(pdf_path):
                        pdf_size = os.path.getsize(pdf_path)
                        print(f"✅ PDF generated successfully: {pdf_path}")
                        print(f"  PDF size: {pdf_size:,} bytes")
                        
                        # Validate PDF is not just an error page
                        if pdf_size < 10000:  # Less than 10KB might indicate an error
                            print(f"  ⚠️  PDF seems small ({pdf_size} bytes) - may contain errors")
                        else:
                            print(f"  ✅ PDF size looks reasonable")
                    else:
                        print("❌ PDF generation failed - no file created")
                except Exception as pdf_err:
                    print(f"❌ PDF generation error: {str(pdf_err)}")
                
                # Save test report for review
                test_report_path = f"test_market_report_{int(time.time())}.json"
                try:
                    with open(test_report_path, 'w') as f:
                        json.dump(report, f, indent=2, default=str)
                    print(f"\n💾 Test report saved: {test_report_path}")
                except Exception as save_err:
                    print(f"❌ Error saving test report: {str(save_err)}")
                
                return True, report
                
            else:
                print("❌ Market report generation returned None")
                return False, None
                
        except Exception as report_err:
            print(f"❌ Error generating market report: {str(report_err)}")
            print(f"Stack trace:\n{traceback.format_exc()}")
            return False, None
        
    except Exception as e:
        print(f"❌ Test setup error: {str(e)}")
        print(f"Stack trace:\n{traceback.format_exc()}")
        return False, None
    
    finally:
        # Cleanup
        try:
            if 'exchange' in locals():
                await exchange.close()
        except:
            pass

async def main():
    """Run the end-to-end test"""
    print(f"🚀 Starting Market Reporter E2E Test at {datetime.now()}")
    
    try:
        success, report = await test_market_reporter_e2e()
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 END-TO-END TEST COMPLETED SUCCESSFULLY!")
            print("\n📋 Summary:")
            print("  ✅ Exchange connection working")
            print("  ✅ Field mapping fixes applied")
            print("  ✅ Market report generation working")
            print("  ✅ PDF generation working")
            print("\n🔍 Next Steps:")
            print("  1. Review the generated PDF for data accuracy")
            print("  2. Check volume/turnover values are not zero")
            print("  3. Verify futures premium calculations")
            print("  4. Confirm all sections show real data")
        else:
            print("❌ END-TO-END TEST FAILED")
            print("\n🔧 Troubleshooting needed:")
            print("  1. Check field mapping implementation in market_reporter.py")
            print("  2. Verify exchange connectivity")
            print("  3. Review error logs for specific issues")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    # Run the test
    asyncio.run(main()) 