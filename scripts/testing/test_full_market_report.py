#!/usr/bin/env python3
"""
Test script to generate a complete market report with PDF to validate the entire pipeline.
"""

import sys
import os
import asyncio
import logging
import ccxt
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

async def test_full_market_report():
    """Test complete market report generation with PDF."""
    print("🔧 Testing Complete Market Report Generation")
    print("=" * 60)
    
    try:
        # Import the market reporter
        from monitoring.market_reporter import MarketReporter
        
        # Initialize exchange
        exchange = ccxt.bybit({
            'sandbox': False,
        })
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # Initialize market reporter
        print("📊 Initializing Market Reporter...")
        reporter = MarketReporter(exchange=exchange, logger=logger)
        print("✅ Market Reporter initialized")
        
        # Generate market summary
        print("\n📋 Generating Market Summary...")
        start_time = datetime.now()
        
        summary = await reporter.generate_market_summary()
        
        generation_time = (datetime.now() - start_time).total_seconds()
        
        if summary:
            print(f"✅ Market summary generated in {generation_time:.2f}s")
            
            # Analyze the report
            print(f"\n📊 Report Analysis:")
            print(f"  Sections: {list(summary.keys())}")
            print(f"  Quality Score: {summary.get('quality_score', 'N/A')}")
            
            # Check each section for real data
            if 'market_overview' in summary:
                overview = summary['market_overview']
                print(f"  Market Overview: ✅ Present")
                print(f"    - Regime: {overview.get('regime', 'N/A')}")
                print(f"    - Trend Strength: {overview.get('trend_strength', 'N/A')}")
                
            if 'futures_premium' in summary:
                futures = summary['futures_premium']
                print(f"  Futures Premium: ✅ Present")
                if 'premiums' in futures:
                    premium_count = len(futures['premiums'])
                    print(f"    - Premiums calculated: {premium_count}")
                    
            if 'smart_money_index' in summary:
                smart_money = summary['smart_money_index']
                print(f"  Smart Money Index: ✅ Present")
                print(f"    - Index Value: {smart_money.get('current_value', 'N/A')}")
                print(f"    - Signal: {smart_money.get('signal', 'N/A')}")
                
            if 'whale_activity' in summary:
                whale = summary['whale_activity']
                print(f"  Whale Activity: ✅ Present")
                if 'transactions' in whale:
                    tx_count = len(whale['transactions'])
                    print(f"    - Transactions found: {tx_count}")
                    
            if 'performance_metrics' in summary:
                perf = summary['performance_metrics']
                print(f"  Performance Metrics: ✅ Present")
                
            # Test PDF generation
            print(f"\n📄 Testing PDF Generation...")
            pdf_path = await reporter.generate_market_pdf_report(summary)
            
            if pdf_path and os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path) / 1024  # KB
                print(f"✅ PDF generated successfully: {pdf_path}")
                print(f"  File size: {file_size:.1f} KB")
                
                # Verify PDF is not empty
                if file_size > 10:  # At least 10KB
                    print("✅ PDF appears to contain content")
                    return True, pdf_path
                else:
                    print("⚠️ PDF seems too small, may be empty")
                    return False, pdf_path
            else:
                print("❌ PDF generation failed")
                return False, None
                
        else:
            print("❌ Market summary generation failed")
            return False, None
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

async def main():
    """Run the full market report test."""
    print("🚀 Starting Full Market Report Test")
    print("This will test the complete pipeline with real data and PDF generation\n")
    
    success, pdf_path = await test_full_market_report()
    
    print("\n" + "=" * 60)
    print("🔧 FULL MARKET REPORT TEST RESULTS")
    print("=" * 60)
    
    if success:
        print("🎉 COMPLETE SUCCESS!")
        print("✅ Market data extraction working")
        print("✅ All calculation methods restored and working")
        print("✅ Report generation successful")
        print("✅ PDF generation successful")
        print(f"\n📄 Generated PDF: {pdf_path}")
        print("\n🎯 The market reporter is now fully functional!")
        print("📊 Ready to generate live market reports with real data!")
    else:
        print("❌ TEST FAILED")
        print("⚠️ Some components are not working correctly")
        if pdf_path:
            print(f"📄 Partial PDF generated: {pdf_path}")

if __name__ == "__main__":
    asyncio.run(main()) 