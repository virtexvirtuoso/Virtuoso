#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

async def test_pdf_only():
    from src.monitoring.market_reporter import MarketReporter
    reporter = MarketReporter()
    
    test_data = {
        'market_overview': {
            'timestamp': '2025-06-03 19:10:00',
            'total_symbols': 5,
            'avg_volume': 1234567,
            'market_cap': 2000000000
        },
        'timestamp': 1733270400
    }
    
    if reporter.pdf_enabled:
        try:
            pdf_file = await reporter.pdf_generator.generate_market_html_report(
                test_data, 
                output_path='exports/test_report_fix.html',
                generate_pdf=True
            )
            print(f'✅ PDF generation test: {bool(pdf_file)}')
            if pdf_file and os.path.exists(pdf_file):
                print(f'✅ File exists: {pdf_file}')
                return True
            else:
                print(f'❌ File not found: {pdf_file}')
                return False
        except Exception as e:
            print(f'❌ PDF generation failed: {e}')
            return False
    else:
        print('❌ PDF not enabled')
        return False

if __name__ == "__main__":
    result = asyncio.run(test_pdf_only())
    print(f'Final result: {result}') 