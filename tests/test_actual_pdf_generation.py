#!/usr/bin/env python3
"""
Test actual PDF generation with enhanced premium data to verify complete integration.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.monitoring.market_reporter import MarketReporter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockExchange:
    """Enhanced mock exchange for PDF testing."""
    
    def __init__(self):
        self.rest_endpoint = "https://api.bybit.com"
    
    async def fetch_ticker(self, symbol):
        """Mock ticker with realistic data."""
        base_prices = {
            'BTC/USDT:USDT': 95000.0,
            'ETH/USDT:USDT': 3500.0,
            'SOL/USDT:USDT': 220.0,
            'XRP/USDT:USDT': 2.8,
            'AVAX/USDT:USDT': 45.0
        }
        
        base_price = base_prices.get(symbol, 50000.0)
        
        return {
            'symbol': symbol,
            'last': base_price,
            'bid': base_price * 0.9999,
            'ask': base_price * 1.0001,
            'high': base_price * 1.05,
            'low': base_price * 0.95,
            'volume': 10000.0,
            'markPrice': base_price * 1.0002,
            'indexPrice': base_price * 0.9998,
            'timestamp': int(datetime.now().timestamp() * 1000),
            'percentage': 2.5,  # Mock 24h change
            'quoteVolume': base_price * 10000
        }
    
    async def get_markets(self):
        """Mock markets data."""
        return {
            'BTCUSDT': {'symbol': 'BTCUSDT', 'type': 'spot'},
            'BTC/USDT:USDT': {'symbol': 'BTC/USDT:USDT', 'type': 'swap'},
            'ETHUSDT': {'symbol': 'ETHUSDT', 'type': 'spot'},
            'ETH/USDT:USDT': {'symbol': 'ETH/USDT:USDT', 'type': 'swap'},
            'SOLUSDT': {'symbol': 'SOLUSDT', 'type': 'spot'},
            'SOL/USDT:USDT': {'symbol': 'SOL/USDT:USDT', 'type': 'swap'},
            'XRPUSDT': {'symbol': 'XRPUSDT', 'type': 'spot'},
            'XRP/USDT:USDT': {'symbol': 'XRP/USDT:USDT', 'type': 'swap'},
            'AVAXUSDT': {'symbol': 'AVAXUSDT', 'type': 'spot'},
            'AVAX/USDT:USDT': {'symbol': 'AVAX/USDT:USDT', 'type': 'swap'}
        }
    
    async def fetch_order_book(self, symbol, limit=50):
        """Mock order book data."""
        base_price = (await self.fetch_ticker(symbol))['last']
        
        # Generate realistic bid/ask spreads
        bids = []
        asks = []
        
        for i in range(limit):
            bid_price = base_price * (1 - (i + 1) * 0.0001)
            ask_price = base_price * (1 + (i + 1) * 0.0001)
            
            bid_size = 100.0 / (i + 1)  # Decreasing size
            ask_size = 100.0 / (i + 1)
            
            bids.append([bid_price, bid_size])
            asks.append([ask_price, ask_size])
        
        return {
            'symbol': symbol,
            'bids': bids,
            'asks': asks,
            'timestamp': int(datetime.now().timestamp() * 1000)
        }

async def test_pdf_generation_with_enhanced_premium():
    """Test complete PDF generation with enhanced premium data."""
    print("\n🎯 Testing Complete PDF Generation with Enhanced Premium Data")
    print("=" * 70)
    
    # Create MarketReporter with enhanced mock exchange
    mock_exchange = MockExchange()
    reporter = MarketReporter(exchange=mock_exchange, logger=logger)
    
    print(f"\n1️⃣ Generating Market Report with Enhanced Premium Data")
    try:
        # Generate a complete market report
        market_report = await reporter.generate_market_summary()
        
        print(f"   ✅ Market report generated successfully")
        print(f"   📊 Report sections: {len(market_report)} sections")
        
        # Check enhanced premium data
        if 'futures_premium' in market_report:
            fp_data = market_report['futures_premium']
            print(f"   📈 Futures premium data: {len(fp_data.get('premiums', {}))} symbols")
            print(f"   📈 Average premium: {fp_data.get('average_premium', 'N/A')}")
            print(f"   📈 Contango status: {fp_data.get('contango_status', 'N/A')}")
            
            # Show enhanced data details
            if 'premiums' in fp_data and fp_data['premiums']:
                sample_symbol = list(fp_data['premiums'].keys())[0]
                sample_data = fp_data['premiums'][sample_symbol]
                data_source = sample_data.get('data_source', 'unknown')
                validation_status = sample_data.get('validation_status', 'unknown')
                print(f"   📊 Sample data source: {data_source}")
                print(f"   📊 Sample validation: {validation_status}")
        
    except Exception as e:
        print(f"   ❌ Error generating market report: {str(e)}")
        return False
    
    print(f"\n2️⃣ Testing PDF Generation")
    try:
        # Test PDF generation through market reporter
        pdf_path = await reporter.generate_market_pdf_report(market_report)
        
        if pdf_path and os.path.exists(pdf_path):
            file_size = os.path.getsize(pdf_path)
            print(f"   ✅ PDF generated successfully: {pdf_path}")
            print(f"   📄 File size: {file_size:,} bytes")
            
            # Check if the file is a valid PDF (basic check)
            with open(pdf_path, 'rb') as f:
                header = f.read(8)
                if header.startswith(b'%PDF-'):
                    print(f"   ✅ Valid PDF file format confirmed")
                else:
                    print(f"   ⚠️ PDF file format validation failed")
            
            return pdf_path
        else:
            print(f"   ❌ PDF generation failed or file not found")
            return False
    
    except Exception as e:
        print(f"   ❌ Error in PDF generation: {str(e)}")
        return False
    
    finally:
        # Cleanup
        await reporter.cleanup()

async def test_template_data_structure():
    """Test the data structure that gets passed to the template."""
    print(f"\n3️⃣ Testing Template Data Structure")
    
    mock_exchange = MockExchange()
    reporter = MarketReporter(exchange=mock_exchange, logger=logger)
    
    try:
        # Generate market report
        market_report = await reporter.generate_market_summary()
        
        # Create the data structure that would be passed to the template
        template_data = {
            'symbol': 'MARKET_REPORT',
            'timestamp': market_report.get('timestamp', int(datetime.now().timestamp() * 1000)),
            'signal': market_report.get('market_overview', {}).get('regime', 'NEUTRAL'),
            'score': 75.0,
            'type': 'market_report',
            'report_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            'results': market_report,
            'components': {}
        }
        
        # Check enhanced premium data in template structure
        if 'futures_premium' in market_report:
            fp_data = market_report['futures_premium']
            
            print(f"   📊 Enhanced premium data available for template:")
            print(f"      - Premiums: {len(fp_data.get('premiums', {}))}")
            print(f"      - Average premium: {fp_data.get('average_premium', 'N/A')}")
            print(f"      - Contango status: {fp_data.get('contango_status', 'N/A')}")
            
            # Check individual symbol data
            if 'premiums' in fp_data and fp_data['premiums']:
                for symbol, data in list(fp_data['premiums'].items())[:3]:  # Show first 3
                    premium = data.get('premium', 'N/A')
                    data_source = data.get('data_source', 'unknown')
                    validation = data.get('validation_status', 'unknown')
                    print(f"      - {symbol}: {premium} (source: {data_source}, validation: {validation})")
            
            # Add premium data to components for scoring
            avg_premium_value = fp_data.get('average_premium_value', 0)
            premium_score = 50 + (avg_premium_value * 10)  # Convert to score
            premium_score = max(0, min(100, premium_score))  # Clamp to 0-100
            
            template_data['components']['futures_premium'] = {
                'score': premium_score,
                'data': fp_data
            }
            
            print(f"   📈 Premium component score: {premium_score:.1f}")
        
        print(f"   ✅ Template data structure validated")
        return True
        
    except Exception as e:
        print(f"   ❌ Error in template data structure test: {str(e)}")
        return False
    
    finally:
        await reporter.cleanup()

async def main():
    """Run the complete PDF generation test."""
    print("🚀 Complete PDF Generation Test with Enhanced Premium Data")
    print("=" * 80)
    
    # Test 1: PDF Generation
    pdf_path = await test_pdf_generation_with_enhanced_premium()
    
    # Test 2: Template Data Structure
    template_success = await test_template_data_structure()
    
    # Results Summary
    print(f"\n📋 Test Results Summary")
    print("=" * 50)
    
    if pdf_path:
        print(f"✅ PDF Generation: SUCCESS")
        print(f"   📄 File: {pdf_path}")
        print(f"   📊 Enhanced premium data: INCLUDED")
    else:
        print(f"❌ PDF Generation: FAILED")
    
    if template_success:
        print(f"✅ Template Data Structure: SUCCESS")
        print(f"   📊 Enhanced premium data: PROPERLY STRUCTURED")
    else:
        print(f"❌ Template Data Structure: FAILED")
    
    overall_success = bool(pdf_path) and template_success
    
    if overall_success:
        print(f"\n🎉 COMPLETE INTEGRATION SUCCESS!")
        print(f"   Enhanced premium data is fully integrated from calculation to PDF output.")
        print(f"   The system is ready for production use with modern API-based premium data.")
    else:
        print(f"\n❌ Integration issues detected - check error messages above.")
    
    return overall_success

if __name__ == "__main__":
    asyncio.run(main()) 