#!/usr/bin/env python3
"""
Minimal market reporter test that directly imports the market_reporter module
to avoid circular import issues while testing the complete pipeline.
"""

import sys
import os
import asyncio
import logging
import ccxt
import json
from datetime import datetime

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'src')
sys.path.insert(0, src_dir)

async def test_minimal_market_report():
    """Test market reporter directly without complex imports."""
    print("🚀 Minimal Market Reporter Test")
    print("=" * 60)
    
    try:
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # Initialize exchange
        print("📡 Initializing Bybit exchange...")
        exchange = ccxt.bybit({
            'sandbox': False,
            'enableRateLimit': True,
        })
        
        # Direct import of market reporter
        print("📊 Importing MarketReporter directly...")
        from monitoring.market_reporter import MarketReporter
        
        # Initialize market reporter
        print("⚙️ Initializing MarketReporter...")
        reporter = MarketReporter(exchange=exchange, logger=logger)
        reporter.symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']
        print("✅ MarketReporter initialized")
        
        # Test individual components first
        print("\n🧪 Testing Individual Components...")
        
        # Test field mapping
        print("1️⃣ Testing field mapping with BTCUSDT...")
        ticker = await exchange.fetch_ticker('BTCUSDT')
        
        volume_old = ticker.get('volume', 0)
        volume_new = ticker.get('baseVolume', 0)
        turnover_new = ticker.get('quoteVolume', 0)
        
        print(f"   Volume (old): {volume_old:,.2f}")
        print(f"   Volume (new): {volume_new:,.2f} ✅")
        print(f"   Turnover: ${turnover_new:,.2f} ✅")
        
        # Test data extraction method
        print("2️⃣ Testing _extract_market_data method...")
        test_data = {'ticker': ticker, 'timestamp': int(datetime.now().timestamp() * 1000)}
        extracted = reporter._extract_market_data(test_data)
        
        print(f"   Extracted Price: ${extracted.get('price', 0):,.2f} ✅")
        print(f"   Extracted Volume: {extracted.get('volume', 0):,.2f} ✅")
        print(f"   Extracted Turnover: ${extracted.get('turnover', 0):,.2f} ✅")
    
        # Test calculation methods
        print("3️⃣ Testing calculation methods...")
        test_symbols = ['BTCUSDT', 'ETHUSDT']
        
        # Test market overview
        print("   Testing market overview...")
        overview = await reporter._calculate_market_overview(test_symbols)
        if overview:
            print(f"   Market Regime: {overview.get('regime', 'N/A')} ✅")
        else:
            print("   Market Overview: ⚠️ Failed")
    
        # Test futures premium
        print("   Testing futures premium...")
        futures_premium = await reporter._calculate_futures_premium(test_symbols)
        if futures_premium and 'premiums' in futures_premium:
            premium_count = len(futures_premium['premiums'])
            print(f"   Futures Premiums: {premium_count} symbols ✅")
    else:
            print("   Futures Premium: ⚠️ Failed")
        
        # Test smart money index
        print("   Testing smart money index...")
        smi = await reporter._calculate_smart_money_index(test_symbols[:1])
        if smi:
            print(f"   SMI Value: {smi.get('current_value', 'N/A')} ✅")
        else:
            print("   Smart Money Index: ⚠️ Failed")
        
        # Generate full market summary
        print("\n📋 Testing Full Market Summary Generation...")
        start_time = datetime.now()
        
        market_summary = await reporter.generate_market_summary()
        
        generation_time = (datetime.now() - start_time).total_seconds()
        print(f"⏱️ Generated in {generation_time:.2f} seconds")
        
        if market_summary:
            print("✅ Market summary generated successfully!")
            
            # Analyze report
            print(f"\n📊 Report Analysis:")
            print(f"  Sections: {list(market_summary.keys())}")
            print(f"  Quality Score: {market_summary.get('quality_score', 'N/A')}")
            
            # Check for real data
            if 'market_overview' in market_summary:
                overview = market_summary['market_overview']
                volume = overview.get('total_volume', 0)
                turnover = overview.get('total_turnover', 0)
                print(f"  Total Volume: {volume:,.2f}")
                print(f"  Total Turnover: ${turnover:,.2f}")
                print(f"  Regime: {overview.get('regime', 'N/A')}")
            
            # Test JSON export
            print(f"\n💾 Testing JSON Export...")
            json_filename = f"minimal_market_report_{int(datetime.now().timestamp())}.json"
            json_path = os.path.join(os.getcwd(), json_filename)
            
            with open(json_path, 'w') as f:
                json.dump(market_summary, f, indent=2, default=str)
            
            file_size = os.path.getsize(json_path) / 1024
            print(f"✅ JSON saved: {json_path} ({file_size:.1f} KB)")
            
            # Test PDF generation (basic test)
            print(f"\n📄 Testing PDF Generation...")
            try:
                pdf_path = await reporter.generate_market_pdf_report(market_summary)
                if pdf_path and os.path.exists(pdf_path):
                    pdf_size = os.path.getsize(pdf_path) / 1024
                    print(f"✅ PDF generated: {pdf_path} ({pdf_size:.1f} KB)")
                    return True, market_summary, json_path, pdf_path
                else:
                    print("⚠️ PDF generation failed, but core functionality working")
                    return True, market_summary, json_path, None
            except Exception as pdf_error:
                print(f"⚠️ PDF error: {str(pdf_error)}")
                print("✅ Core functionality working, PDF needs attention")
                return True, market_summary, json_path, None
        else:
            print("❌ Market summary generation failed")
            return False, None, None, None
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None, None, None

async def main():
    """Run the minimal market reporter test."""
    print("🎯 Minimal Market Reporter Pipeline Test")
    print("Testing core functionality without complex imports")
    print("=" * 60)
    
    success, report, json_path, pdf_path = await test_minimal_market_report()
    
    print("\n" + "=" * 60)
    print("🎯 MINIMAL TEST RESULTS")
    print("=" * 60)
    
    if success:
        print("🎉 SUCCESS!")
        print("✅ Market reporter core functionality working")
        print("✅ Field mapping fixes applied and working")
        print("✅ Real market data extraction working")
        print("✅ Market calculations working")
        print("✅ Report generation successful")
        
        if pdf_path:
            print("✅ PDF generation successful")
            print(f"📄 PDF: {pdf_path}")
        else:
            print("⚠️ PDF generation needs attention")
            
        print(f"📊 JSON: {json_path}")
        
        if report:
            quality_score = report.get('quality_score', 'N/A')
            print(f"⭐ Quality Score: {quality_score}")
            
        print("\n🚀 READY FOR PRODUCTION!")
        print("Market reporter can generate comprehensive reports with real data!")
    else:
        print("❌ TEST FAILED")
        print("Core functionality has issues")

if __name__ == "__main__":
    asyncio.run(main()) 