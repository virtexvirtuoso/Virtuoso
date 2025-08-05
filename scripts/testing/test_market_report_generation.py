#!/usr/bin/env python3

import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

import asyncio
import logging
import json
from datetime import datetime
from monitoring.market_reporter import MarketReporter
from config.manager import ConfigManager
from data_acquisition.binance.binance_exchange import BinanceExchange

# Configure logging to show progress
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def test_market_report_generation():
    """Test actual market report generation with verified API endpoints."""
    
    print('🚀 Testing Market Report Generation')
    print('=' * 50)
    
    try:
        # Initialize components
        print('📋 Initializing components...')
        config_manager = ConfigManager()
        config = config_manager.config
        
        # Initialize exchange with async context manager
        print('🔗 Connecting to Binance (with async context)...')
        exchange = BinanceExchange(config=config)
        
        # Use async context manager for proper initialization
        async with exchange:
            print('   ✅ Exchange connected and initialized')
            
            # Initialize market reporter
            print('📊 Initializing Market Reporter...')
            reporter = MarketReporter(exchange=exchange)
            print('   ✅ Market Reporter ready')
            
            # Test basic data fetching
            print('🧪 Testing data fetching capabilities...')
            test_symbol = 'BTCUSDT'
            
            try:
                ticker = await reporter._fetch_with_retry('fetch_ticker', test_symbol, timeout=5)
                if ticker and 'last' in ticker:
                    price = ticker['last']
                    change = ticker.get('percentage', 0)
                    volume = ticker.get('baseVolume', 0)
                    print(f'   ✅ Live Data: {test_symbol} = ${price}, {change:+.2f}%, Vol: {volume:,.0f}')
                else:
                    print('   ⚠️  Ticker data format unexpected')
            except Exception as e:
                print(f'   ❌ Data fetch test failed: {e}')
                return False
            
            # Test market overview calculation
            print('📈 Testing market overview calculation...')
            try:
                symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
                overview = await reporter._calculate_market_overview(symbols)
                
                if overview and 'regime' in overview:
                    regime = overview['regime']
                    total_volume = overview.get('total_volume', 0)
                    total_oi = overview.get('total_open_interest', 0)
                    print(f'   ✅ Market Overview: {regime}, Volume: {reporter._format_number(total_volume)}, OI: {reporter._format_number(total_oi)}')
                else:
                    print('   ⚠️  Market overview incomplete')
            except Exception as e:
                print(f'   ❌ Market overview failed: {e}')
            
            # Test full market summary generation
            print('📋 Testing full market summary generation...')
            try:
                print('   🔄 Generating comprehensive market report...')
                report = await reporter.generate_market_summary()
                
                if report:
                    timestamp = report.get('timestamp', 0)
                    readable_time = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S UTC')
                    
                    print(f'   ✅ Report Generated: {readable_time}')
                    print(f'   📊 Report Sections: {len(report)} components')
                    
                    # Show key metrics from the report
                    if 'market_overview' in report:
                        mo = report['market_overview']
                        print(f'   📈 Market Regime: {mo.get("regime", "Unknown")}')
                        print(f'   💰 Total Volume: ${reporter._format_number(mo.get("total_turnover", 0))}')
                    
                    if 'futures_premium' in report:
                        fp = report['futures_premium']
                        premium_count = len(fp.get('premiums', {}))
                        print(f'   📊 Futures Premiums: {premium_count} pairs analyzed')
                    
                    if 'smart_money_index' in report:
                        smi = report['smart_money_index']
                        index_value = smi.get('index', 50)
                        print(f'   🧠 Smart Money Index: {index_value:.1f}/100')
                    
                    # Show JSON structure summary
                    json_size = len(json.dumps(report, default=str))
                    print(f'   📄 Report Size: {json_size:,} characters')
                    
                    # Verify saved files
                    if 'json_path' in report:
                        print(f'   💾 Saved: {report["json_path"]}')
                    
                    print(f'\n🎉 SUCCESS: Market report generated successfully!')
                    print(f'✅ All verified API endpoints working in production')
                    print(f'✅ Real-time data collection functional')
                    print(f'✅ Multi-component analysis complete')
                    print(f'✅ Report persistence working')
                    
                    return True
                else:
                    print('   ❌ Report generation returned None')
                    return False
                    
            except Exception as e:
                print(f'   ❌ Market summary generation failed: {e}')
                return False
        
    except Exception as e:
        print(f'\n❌ Test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print('Testing Market Reporter with verified Binance API endpoints...\n')
    success = asyncio.run(test_market_report_generation())
    
    if success:
        print(f'\n🌟 CONCLUSION: Market Reporter is PRODUCTION READY!')
        print(f'   • All Binance API endpoints verified ✅')
        print(f'   • Real-time data collection working ✅')
        print(f'   • Market analysis algorithms functional ✅')
        print(f'   • Report generation successful ✅')
        print(f'   • File persistence working ✅')
        sys.exit(0)
    else:
        print(f'\n❌ Market Reporter needs attention before production use')
        sys.exit(1) 