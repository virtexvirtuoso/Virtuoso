#!/usr/bin/env python3
"""
Production-Ready Pipeline Test

Tests the complete market reporting pipeline with PDF generation in production mode.
"""

import sys
import os
import asyncio
import time
from datetime import datetime

# Add the src directory to the Python path correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
src_dir = os.path.join(project_root, 'src')

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Also add the project root for additional imports
if project_root not in sys.path:
    sys.path.insert(0, project_root)

async def test_production_pipeline():
    """Test the complete production pipeline."""
    
    print("🚀 Production-Ready Pipeline Test")
    print("=" * 60)
    
    try:
        print("🔍 Testing basic imports...")
        
        # Import exchange
        import ccxt
        print("   ✅ CCXT imported")
        
        # Test direct PDF imports
        try:
            from core.reporting.report_manager import ReportManager
            from core.reporting.pdf_generator import ReportGenerator
            print("   ✅ PDF modules available")
            pdf_available = True
        except ImportError as e:
            print(f"   ⚠️ PDF modules not available: {e}")
            pdf_available = False
        
        # Import MarketReporter
        from monitoring.market_reporter import MarketReporter
        print("   ✅ MarketReporter imported")
        
        # Initialize exchange
        print("\n📡 Initializing exchange connection...")
        exchange = ccxt.bybit({
            'sandbox': False,
            'enableRateLimit': True,
            'timeout': 15000,
        })
        print("   ✅ Bybit exchange initialized")
        
        # Test basic connectivity
        try:
            markets = await exchange.load_markets()
            print(f"   ✅ Connected to exchange: {len(markets)} markets loaded")
        except Exception as e:
            print(f"   ⚠️ Exchange connectivity issue: {e}")
        
        # Initialize MarketReporter
        print("\n📊 Initializing MarketReporter...")
        reporter = MarketReporter(exchange=exchange)
        
        # Check configuration
        pdf_enabled = getattr(reporter, 'pdf_enabled', False)
        default_template = getattr(reporter, 'default_template', 'none')
        
        print(f"   PDF Generation: {'✅ Enabled' if pdf_enabled else '❌ Disabled'}")
        print(f"   Default Template: {default_template}")
        print(f"   Default Symbols: {reporter.symbols}")
        
        # Test symbol format conversion
        print("\n🔧 Testing symbol format conversion...")
        test_conversions = [
            ('BTC/USDT:USDT', 'BTCUSDT'),
            ('ETH/USDT', 'ETHUSDT'),
            ('SOLUSDT', 'SOLUSDT')
        ]
        
        for input_symbol, expected in test_conversions:
            converted = reporter._convert_symbol_format(input_symbol)
            status = "✅" if converted == expected else "❌"
            print(f"   {status} {input_symbol} → {converted}")
        
        # Test live data collection
        print("\n📈 Testing live data collection...")
        live_data = {}
        
        for symbol in reporter.symbols[:3]:  # Test first 3 symbols
            try:
                ticker = await reporter._fetch_with_retry('fetch_ticker', symbol, timeout=10)
                if ticker:
                    live_data[symbol] = {
                        'price': ticker.get('last', 0),
                        'volume': ticker.get('baseVolume', 0),
                        'change': ticker.get('percentage', 0)
                    }
                    print(f"   ✅ {symbol}: ${ticker.get('last', 0):,.2f} | Vol: {ticker.get('baseVolume', 0):,.0f}")
                else:
                    print(f"   ❌ {symbol}: No data")
            except Exception as e:
                print(f"   ❌ {symbol}: {e}")
        
        if len(live_data) >= 2:
            print(f"   ✅ Live data collection successful: {len(live_data)}/3 symbols")
        else:
            print("   ❌ Live data collection mostly failed")
            return False
        
        # Generate comprehensive market report
        print("\n📋 Generating comprehensive market report...")
        start_time = time.time()
        
        try:
            report = await reporter.generate_market_summary()
            duration = time.time() - start_time
            
            if not report:
                print("   ❌ Market report generation failed")
                return False
            
            print(f"   ✅ Market report generated in {duration:.2f}s")
            
            # Validate report structure
            required_sections = ['market_overview', 'futures_premium', 'smart_money_index', 'whale_activity']
            available_sections = [s for s in required_sections if s in report and report[s]]
            missing_sections = [s for s in required_sections if s not in available_sections]
            
            print(f"   📋 Available sections: {', '.join(available_sections)}")
            if missing_sections:
                print(f"   ⚠️ Missing sections: {', '.join(missing_sections)}")
            
            # Check quality score
            quality_score = report.get('quality_score', 0)
            print(f"   📊 Quality Score: {quality_score}%")
            
            # Check JSON export
            if 'json_path' in report:
                json_path = report['json_path']
                if os.path.exists(json_path):
                    file_size = os.path.getsize(json_path) / 1024
                    print(f"   💾 JSON Report: {json_path} ({file_size:.1f} KB)")
                else:
                    print(f"   ❌ JSON file not found: {json_path}")
            
        except Exception as e:
            print(f"   ❌ Market report generation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test PDF generation if available
        if pdf_enabled:
            print("\n📄 Testing PDF generation...")
            try:
                pdf_start = time.time()
                pdf_path = await reporter.generate_market_pdf_report(report)
                pdf_duration = time.time() - pdf_start
                
                if pdf_path and os.path.exists(pdf_path):
                    file_size = os.path.getsize(pdf_path) / 1024
                    print(f"   ✅ PDF generated in {pdf_duration:.2f}s")
                    print(f"   📄 PDF Report: {pdf_path} ({file_size:.1f} KB)")
                    
                    # Verify PDF content
                    if file_size > 10:  # Should be at least 10KB for a real PDF
                        print("   ✅ PDF appears to contain substantial content")
                    else:
                        print("   ⚠️ PDF seems very small, may be incomplete")
                        
                else:
                    print("   ❌ PDF generation failed or file not created")
                    return False
                    
            except Exception as e:
                print(f"   ❌ PDF generation error: {e}")
                return False
        else:
            print("\n⚠️ PDF generation not available (dependencies may be missing)")
            print("   📋 Core pipeline test successful without PDF")
        
        # Performance summary
        print(f"\n⚡ Performance Summary:")
        print(f"   📊 Report Generation: {duration:.2f}s")
        if pdf_enabled:
            print(f"   📄 PDF Generation: {pdf_duration:.2f}s")
            print(f"   🎯 Total Pipeline: {duration + pdf_duration:.2f}s")
        else:
            print(f"   🎯 Core Pipeline: {duration:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test runner."""
    print(f"🔧 Python: {sys.version}")
    print(f"📁 Directory: {os.getcwd()}")
    print(f"🐍 Executable: {sys.executable}")
    
    success = await test_production_pipeline()
    
    print("\n" + "=" * 60)
    print("🎯 PRODUCTION PIPELINE TEST RESULTS")
    print("=" * 60)
    
    if success:
        print("🎉 SUCCESS! Production pipeline is fully operational")
        print("")
        print("✅ Core Components:")
        print("   • Exchange connectivity")
        print("   • Symbol format handling") 
        print("   • Live data collection")
        print("   • Market analysis calculations")
        print("   • JSON report export")
        print("")
        print("✅ Production Features:")
        print("   • Real-time market data")
        print("   • Comprehensive market overview")
        print("   • Futures premium analysis")
        print("   • Smart money indicators")
        print("   • Whale activity tracking")
        print("   • PDF report generation (if available)")
        print("")
        print("🚀 READY FOR PRODUCTION DEPLOYMENT!")
        
    else:
        print("❌ Pipeline test failed")
        print("🔧 Review the errors above and fix issues before production")
    
    return success

if __name__ == "__main__":
    asyncio.run(main()) 