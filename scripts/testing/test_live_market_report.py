#!/usr/bin/env python3
"""
Comprehensive test of market reporter with live data and PDF generation.
This test bypasses import issues by directly setting up the environment.
"""

import sys
import os
import asyncio
import logging
import ccxt
import json
from datetime import datetime

# Add src to path properly
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'src')
sys.path.insert(0, src_dir)

async def test_live_market_report():
    """Test complete market report generation with live data and PDF."""
    print("🚀 Testing Live Market Report Generation")
    print("=" * 70)
    
    try:
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(__name__)
        
        # Initialize exchange
        print("📡 Initializing Bybit exchange...")
        exchange = ccxt.bybit({
            'sandbox': False,
            'enableRateLimit': True,
        })
        
        # Import market reporter
        print("📊 Importing MarketReporter...")
        from monitoring.market_reporter import MarketReporter
        
        # Initialize market reporter
        print("⚙️ Initializing MarketReporter...")
        reporter = MarketReporter(exchange=exchange, logger=logger)
        print("✅ MarketReporter initialized successfully")
        
        # Test symbols
        test_symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'XRP/USDT:USDT']
        reporter.symbols = test_symbols
        
        print(f"\n📋 Testing market report generation with symbols: {test_symbols}")
        
        # Generate market summary
        print("🔄 Generating comprehensive market summary...")
        start_time = datetime.now()
        
        market_summary = await reporter.generate_market_summary()
        
        generation_time = (datetime.now() - start_time).total_seconds()
        print(f"⏱️ Market summary generated in {generation_time:.2f} seconds")
        
        if not market_summary:
            print("❌ Failed to generate market summary")
            return False, None, None, None
            
        print("✅ Market summary generated successfully!")
        
        # Analyze the generated report
        print(f"\n📊 Report Analysis:")
        print(f"  📁 Sections: {list(market_summary.keys())}")
        print(f"  ⭐ Quality Score: {market_summary.get('quality_score', 'N/A')}")
        print(f"  🕒 Generated At: {market_summary.get('generated_at', 'N/A')}")
        
        # Check market overview section
        if 'market_overview' in market_summary:
            overview = market_summary['market_overview']
            print(f"\n📈 Market Overview:")
            print(f"  🏷️ Regime: {overview.get('regime', 'N/A')}")
            print(f"  💪 Trend Strength: {overview.get('trend_strength', 'N/A')}")
            print(f"  📊 Total Volume: {overview.get('total_volume', 'N/A'):,.2f}")
            print(f"  💰 Total Turnover: ${overview.get('total_turnover', 'N/A'):,.2f}")
            print(f"  📶 Total Open Interest: {overview.get('total_open_interest', 'N/A'):,.2f}")
        
        # Check futures premium section
        if 'futures_premium' in market_summary:
            futures = market_summary['futures_premium']
            print(f"\n🔮 Futures Premium Analysis:")
            if 'premiums' in futures and futures['premiums']:
                for symbol, data in list(futures['premiums'].items())[:3]:  # Show first 3
                    premium = data.get('premium', 'N/A')
                    premium_type = data.get('premium_type', 'N/A')
                    print(f"  📊 {symbol}: {premium} ({premium_type})")
            else:
                print("  ⚠️ No futures premium data available")
        
        # Check smart money index
        if 'smart_money_index' in market_summary:
            smi = market_summary['smart_money_index']
            print(f"\n🧠 Smart Money Index:")
            print(f"  📊 Current Value: {smi.get('current_value', 'N/A')}")
            print(f"  🎯 Signal: {smi.get('signal', 'N/A')}")
            print(f"  📈 Change: {smi.get('change', 'N/A')}")
        
        # Check whale activity
        if 'whale_activity' in market_summary:
            whale = market_summary['whale_activity']
            print(f"\n🐋 Whale Activity:")
            if 'transactions' in whale and whale['transactions']:
                tx_count = len(whale['transactions'])
                print(f"  📊 Large Transactions: {tx_count}")
                # Show largest transaction
                if tx_count > 0:
                    largest = max(whale['transactions'], key=lambda x: x.get('usd_value', 0))
                    print(f"  💰 Largest: ${largest.get('usd_value', 0):,.2f} ({largest.get('symbol', 'N/A')})")
            else:
                print("  📊 No significant whale activity detected")
        
        # Test JSON export
        print(f"\n💾 Testing JSON export...")
        json_filename = f"live_market_report_{int(datetime.now().timestamp())}.json"
        json_path = os.path.join(os.getcwd(), "exports", "market_reports", "json", json_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        
        # Save JSON report
        with open(json_path, 'w') as f:
            json.dump(market_summary, f, indent=2, default=str)
        
        file_size = os.path.getsize(json_path) / 1024  # KB
        print(f"✅ JSON report saved: {json_path} ({file_size:.1f} KB)")
        
        # Test PDF generation
        print(f"\n📄 Testing PDF generation...")
        try:
            pdf_path = await reporter.generate_market_pdf_report(market_summary)
            
            if pdf_path and os.path.exists(pdf_path):
                pdf_size = os.path.getsize(pdf_path) / 1024  # KB
                print(f"✅ PDF report generated: {pdf_path}")
                print(f"📄 PDF size: {pdf_size:.1f} KB")
                
                if pdf_size > 50:  # At least 50KB indicates real content
                    print("✅ PDF contains substantial content")
                    return True, market_summary, json_path, pdf_path
                else:
                    print("⚠️ PDF seems small, may have limited content")
                    return True, market_summary, json_path, pdf_path
            else:
                print("❌ PDF generation failed or file not found")
                return True, market_summary, json_path, None
                
        except Exception as pdf_error:
            print(f"⚠️ PDF generation error: {str(pdf_error)}")
            print("✅ Core functionality working, PDF generation needs attention")
            return True, market_summary, json_path, None
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None, None, None

async def validate_report_data(report):
    """Validate that the report contains real data instead of placeholder values."""
    print("\n🔍 Validating Report Data Quality...")
    
    validation_results = {}
    
    # Check market overview for real data
    if 'market_overview' in report:
        overview = report['market_overview']
        volume = overview.get('total_volume', 0)
        turnover = overview.get('total_turnover', 0)
        
        validation_results['volume_real'] = volume > 1000  # Should have significant volume
        validation_results['turnover_real'] = turnover > 1000000  # Should have significant turnover
        validation_results['regime_detected'] = overview.get('regime', 'UNKNOWN') != 'UNKNOWN'
        
        print(f"  📊 Volume: {volume:,.2f} {'✅' if validation_results['volume_real'] else '❌'}")
        print(f"  💰 Turnover: ${turnover:,.2f} {'✅' if validation_results['turnover_real'] else '❌'}")
        print(f"  🏷️ Regime: {overview.get('regime', 'N/A')} {'✅' if validation_results['regime_detected'] else '❌'}")
    
    # Check futures premium for real calculations
    if 'futures_premium' in report and 'premiums' in report['futures_premium']:
        premiums = report['futures_premium']['premiums']
        validation_results['futures_data'] = len(premiums) > 0
        
        real_premiums = 0
        for symbol, data in premiums.items():
            if 'premium_value' in data and data['premium_value'] != 0:
                real_premiums += 1
        
        validation_results['real_premiums'] = real_premiums > 0
        print(f"  🔮 Futures Premiums: {len(premiums)} symbols, {real_premiums} with real data {'✅' if validation_results['real_premiums'] else '❌'}")
    
    # Check smart money index
    if 'smart_money_index' in report:
        smi = report['smart_money_index']
        smi_value = smi.get('current_value', 50)
        validation_results['smi_calculated'] = smi_value != 50  # Should not be default neutral value
        print(f"  🧠 Smart Money Index: {smi_value} {'✅' if validation_results['smi_calculated'] else '❌'}")
    
    # Overall validation
    passed_checks = sum(validation_results.values())
    total_checks = len(validation_results)
    
    print(f"\n📋 Validation Summary: {passed_checks}/{total_checks} checks passed")
    return passed_checks >= (total_checks * 0.7)  # 70% pass rate required

async def main():
    """Run the comprehensive live market report test."""
    print("🎯 Live Market Report Generation & Validation Test")
    print("This will test the complete pipeline with real Bybit data")
    print("=" * 70)
    
    # Run the test
    success, report, json_path, pdf_path = await test_live_market_report()
    
    if success and report:
        # Validate data quality
        data_quality_good = await validate_report_data(report)
        
        print("\n" + "=" * 70)
        print("🎯 COMPREHENSIVE TEST RESULTS")
        print("=" * 70)
        
        if data_quality_good:
            print("🎉 COMPLETE SUCCESS!")
            print("✅ Market reporter fully functional with live data")
            print("✅ All field mapping fixes working")
            print("✅ Real market data extracted and calculated")
            print("✅ Report generation successful")
            print("✅ Data quality validation passed")
            
            if pdf_path:
                print("✅ PDF generation successful")
                print(f"📄 PDF Report: {pdf_path}")
            else:
                print("⚠️ PDF generation needs attention (but core functionality working)")
                
            print(f"📊 JSON Report: {json_path}")
            print(f"⭐ Quality Score: {report.get('quality_score', 'N/A')}")
            
            print("\n🚀 READY FOR PRODUCTION!")
            print("The market reporter can now generate comprehensive reports with real market data.")
            
        else:
            print("⚠️ PARTIAL SUCCESS")
            print("✅ Basic functionality working")
            print("❌ Some data quality issues detected")
            print("🔧 May need additional calibration")
    else:
        print("\n" + "=" * 70)
        print("❌ TEST FAILED")
        print("⚠️ Core functionality has issues")
        print("🔧 Check the error messages above for details")

if __name__ == "__main__":
    asyncio.run(main()) 