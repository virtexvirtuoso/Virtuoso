#!/usr/bin/env python3
"""
Test script for futures premium integration with signal generation and PDF reporting.
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from signal_generation.signal_generator import SignalGenerator
from core.reporting.pdf_generator import ReportGenerator


async def test_futures_premium_integration():
    """Test the futures premium integration with signal generation and PDF reporting."""
    print("🧪 Testing Futures Premium Integration")
    print("=" * 50)
    
    # Mock futures premium data
    mock_futures_premium = {
        'market_status': 'CONTANGO',
        'average_premium': 2.5,
        'premiums': {
            'BTCUSDT': {
                'premium': '3.25%',
                'premium_value': 3.25,
                'premium_type': '📈 Contango',
                'mark_price': 45000,
                'index_price': 43580,
                'funding_rate': 0.0001
            },
            'ETHUSDT': {
                'premium': '1.85%',
                'premium_value': 1.85,
                'premium_type': '📈 Contango',
                'mark_price': 3200,
                'index_price': 3142,
                'funding_rate': 0.00008
            },
            'SOLUSDT': {
                'premium': '-0.75%',
                'premium_value': -0.75,
                'premium_type': '📉 Backwardation',
                'mark_price': 98.5,
                'index_price': 99.25,
                'funding_rate': -0.00005
            }
        },
        'quarterly_futures': {
            'BTCUSDT': [
                {
                    'symbol': 'BTCUSDM25',
                    'price': 45500,
                    'basis': '4.2%',
                    'months_to_expiry': 3,
                    'volume': 1250000
                },
                {
                    'symbol': 'BTCUSDU25',
                    'price': 46200,
                    'basis': '5.8%',
                    'months_to_expiry': 6,
                    'volume': 850000
                }
            ],
            'ETHUSDT': [
                {
                    'symbol': 'ETHUSDM25',
                    'price': 3250,
                    'basis': '2.1%',
                    'months_to_expiry': 3,
                    'volume': 980000
                }
            ]
        },
        'funding_rates': {
            'BTCUSDT': {
                'current_rate': 0.0001,
                'predicted_rate': 0.00012,
                'rate_history': [0.0001, 0.00009, 0.00011]
            }
        }
    }
    
    # Mock indicators data with futures premium
    mock_indicators = {
        'symbol': 'BTCUSDT',
        'current_price': 45000,
        'momentum_score': 65.0,
        'volume_score': 72.0,
        'orderflow_score': 58.0,
        'orderbook_score': 63.0,
        'sentiment_score': 55.0,
        'price_structure_score': 68.0,
        'futures_premium_score': 75.0,  # Strong contango score
        'futures_premium': mock_futures_premium,
        'timestamp': int(datetime.now().timestamp() * 1000)
    }
    
    print("1. Testing Signal Generation with Futures Premium")
    print("-" * 40)
    
    try:
        # Initialize signal generator
        config = {
            'thresholds': {
                'buy': 65.0,
                'sell': 35.0
            },
            'confluence_weights': {
                'momentum': 1.0,
                'volume': 1.0,
                'orderflow': 1.0,
                'orderbook': 1.0,
                'sentiment': 1.0,
                'price_structure': 1.0,
                'futures_premium': 0.8  # Add futures premium weight
            }
        }
        
        signal_generator = SignalGenerator(config)
        
        # Test futures premium component extraction
        futures_components = signal_generator._extract_futures_premium_components(mock_indicators)
        print(f"✅ Futures Premium Components: {json.dumps(futures_components, indent=2)}")
        
        # Generate signal with futures premium data
        signal_result = await signal_generator.generate_signal(mock_indicators)
        
        if signal_result:
            print(f"✅ Signal Generated: {signal_result['signal']}")
            print(f"   Score: {signal_result['score']:.2f}")
            print(f"   Components: {list(signal_result['components'].keys())}")
            
            # Check if futures_premium is included
            if 'futures_premium' in signal_result['components']:
                print(f"   Futures Premium Score: {signal_result['components']['futures_premium']:.2f}")
            
            if 'results' in signal_result and 'futures_premium' in signal_result['results']:
                interpretation = signal_result['results']['futures_premium'].get('interpretation', 'N/A')
                print(f"   Futures Premium Interpretation: {interpretation}")
        else:
            print("❌ No signal generated")
            
    except Exception as e:
        print(f"❌ Signal generation test failed: {str(e)}")
    
    print("\n2. Testing PDF Report Generation with Futures Premium")
    print("-" * 40)
    
    try:
        # Initialize PDF generator
        pdf_generator = ReportGenerator()
        
        # Mock market data for PDF report
        mock_market_data = {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'market_overview': {
                'total_market_cap': 2500000000000,
                'btc_dominance': 42.5,
                'fear_greed_index': 65
            },
            'futures_premium': mock_futures_premium,
            'top_performers': {
                'gainers': [
                    {'symbol': 'BTC', 'change_percent': 5.2},
                    {'symbol': 'ETH', 'change_percent': 3.8}
                ],
                'losers': [
                    {'symbol': 'SOL', 'change_percent': -2.1}
                ]
            }
        }
        
        # Test futures premium chart creation
        output_dir = "tests/output"
        os.makedirs(output_dir, exist_ok=True)
        
        chart_path = pdf_generator._create_futures_premium_chart(mock_futures_premium, output_dir)
        if chart_path and os.path.exists(chart_path):
            print(f"✅ Futures Premium Chart Created: {chart_path}")
        else:
            print("❌ Failed to create futures premium chart")
        
        term_chart_path = pdf_generator._create_term_structure_chart(mock_futures_premium, output_dir)
        if term_chart_path and os.path.exists(term_chart_path):
            print(f"✅ Term Structure Chart Created: {term_chart_path}")
        else:
            print("❌ Failed to create term structure chart")
        
        # Test PDF report generation
        pdf_success = await pdf_generator.generate_market_report(mock_market_data, 
                                                               os.path.join(output_dir, "test_market_report.pdf"))
        if pdf_success:
            print("✅ PDF Market Report Generated Successfully")
        else:
            print("❌ Failed to generate PDF market report")
        
        # Test HTML report generation
        html_success = await pdf_generator.generate_market_html_report(mock_market_data,
                                                                     os.path.join(output_dir, "test_market_report.html"))
        if html_success:
            print("✅ HTML Market Report Generated Successfully")
        else:
            print("❌ Failed to generate HTML market report")
            
    except Exception as e:
        print(f"❌ PDF generation test failed: {str(e)}")
    
    print("\n3. Testing Alert Conditions")
    print("-" * 40)
    
    try:
        # Test extreme contango condition
        extreme_contango_data = mock_indicators.copy()
        extreme_contango_data['futures_premium']['market_status'] = 'STRONG_CONTANGO'
        extreme_contango_data['futures_premium']['average_premium'] = 8.5
        
        signal_generator = SignalGenerator(config)
        
        # This should trigger futures premium alerts
        await signal_generator._check_futures_premium_alerts(extreme_contango_data, 'BTCUSDT')
        print("✅ Extreme contango alert check completed")
        
        # Test extreme backwardation condition
        extreme_backwardation_data = mock_indicators.copy()
        extreme_backwardation_data['futures_premium']['market_status'] = 'STRONG_BACKWARDATION'
        extreme_backwardation_data['futures_premium']['average_premium'] = -6.2
        
        await signal_generator._check_futures_premium_alerts(extreme_backwardation_data, 'BTCUSDT')
        print("✅ Extreme backwardation alert check completed")
        
    except Exception as e:
        print(f"❌ Alert condition test failed: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 Futures Premium Integration Test Complete!")
    print("\nKey Features Tested:")
    print("✓ Futures premium component extraction")
    print("✓ Signal generation with futures premium scoring")
    print("✓ Contango/backwardation interpretation")
    print("✓ PDF report with futures premium charts")
    print("✓ HTML report with futures premium data")
    print("✓ Alert conditions for extreme market conditions")
    print("✓ Term structure analysis and visualization")


if __name__ == "__main__":
    asyncio.run(test_futures_premium_integration()) 