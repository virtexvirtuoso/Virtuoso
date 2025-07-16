#!/usr/bin/env python3
"""
Test script to verify template rendering fixes
"""

import os
import sys
import json
from jinja2 import Environment, FileSystemLoader

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_template_rendering():
    """Test that the template renders without string formatting errors"""
    
    # Set up template environment
    template_dir = os.path.join(os.getcwd(), 'src', 'core', 'reporting', 'templates')
    env = Environment(loader=FileSystemLoader(template_dir))
    
    try:
        template = env.get_template('market_report_dark.html')
        print(f"✓ Template loaded successfully from {template_dir}")
    except Exception as e:
        print(f"✗ Failed to load template: {e}")
        return False
    
    # Create test data with edge cases that might cause formatting errors
    test_data = {
        'timestamp': '2025-05-24 11:36:00',
        'report_date': '2025-05-24',
        'current_year': 2025,
        'market_overview': {
            'regime': 'BULLISH',
            'trend_strength': '75%',
            'volatility': '12.5%',
            'total_volume': '1000000',
            'summary': 'Test market overview'
        },
        'top_performers': {
            'gainers': [
                {'symbol': 'BTCUSDT', 'change': '5.2'},
                {'symbol': 'ETHUSDT', 'change': '3.1'}
            ],
            'losers': [
                {'symbol': 'ADAUSDT', 'change': '-2.1'},
                {'symbol': 'XRPUSDT', 'change': '-1.5'}
            ]
        },
        'futures_premium': {
            'premiums': {},
            'summary': 'No premium data available'
        },
        'smart_money_index': {
            'index': 65.7,
            'current_value': 65.7,
            'sentiment': 'BULLISH',
            'change': '2.3',
            'summary': 'Smart money showing bullish sentiment'
        },
        'whale_activity': {
            'whale_activity': {},
            'significant_activity': {
                'BTCUSDT': {
                    'net_whale_volume': 150.25,
                    'usd_value': 1500000.75
                }
            },
            'has_significant_activity': True,
            'transactions': [
                {
                    'symbol': 'BTCUSDT',
                    'time': '11:30:00',
                    'side': 'buy',
                    'usd_value': 2000000.50
                }
            ],
            'summary': 'Significant whale activity detected'
        },
        'performance_metrics': {
            'metrics': {
                'api_latency': {
                    'avg': 0.025,
                    'p95': 0.045,
                    'max': 0.080
                },
                'error_rate': {
                    'total': 0,
                    'errors_per_minute': 0.0
                },
                'data_quality': {
                    'avg_score': 98.5,
                    'min_score': 95.0
                },
                'processing_time': {
                    'avg': 15.25,
                    'max': 26.75
                }
            },
            'summary': 'System performance is optimal'
        }
    }
    
    # Test rendering
    try:
        html_content = template.render(**test_data)
        print(f"✓ Template rendered successfully, content length: {len(html_content)}")
        
        # Check for key content
        key_phrases = ['Market Intelligence Report', 'Market Overview', 'Smart Money Index']
        missing_phrases = []
        for phrase in key_phrases:
            if phrase not in html_content:
                missing_phrases.append(phrase)
        
        if missing_phrases:
            print(f"⚠ Missing expected phrases: {missing_phrases}")
        else:
            print("✓ All expected content phrases found")
            
        # Check for problematic format strings
        if '"%.1f"|format(' in html_content:
            print("✗ Still contains problematic format strings")
            return False
        else:
            print("✓ No problematic format strings found")
            
        return True
        
    except Exception as e:
        print(f"✗ Template rendering failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("Testing template rendering fixes...")
    print("=" * 50)
    
    success = test_template_rendering()
    
    print("=" * 50)
    if success:
        print("✓ All tests passed! Template fixes are working correctly.")
        return 0
    else:
        print("✗ Tests failed! Template still has issues.")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 