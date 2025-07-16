#!/usr/bin/env python3
"""
Test Dark Theme PDF Generation with WeasyPrint
"""

import sys
import os
import asyncio
import time

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

async def test_timestamp_processing():
    """Test timestamp processing with different formats to ensure no 1970 dates."""
    
    print("🕐 Testing timestamp processing...")
    
    try:
        from core.reporting.pdf_generator import ReportGenerator
        
        generator = ReportGenerator()
        
        # Test data with different timestamp formats
        test_cases = [
            {
                "name": "Milliseconds timestamp",
                "timestamp": int(time.time() * 1000),  # Current time in milliseconds
                "expected_year": "2025"
            },
            {
                "name": "Seconds timestamp", 
                "timestamp": int(time.time()),  # Current time in seconds
                "expected_year": "2025"
            },
            {
                "name": "Small invalid timestamp",
                "timestamp": 1747767,  # This was causing the 1970 issue
                "expected_year": "2025"  # Should fallback to current time
            }
        ]
        
        all_passed = True
        
        for test_case in test_cases:
            print(f"\n📝 Testing: {test_case['name']}")
            print(f"   Input timestamp: {test_case['timestamp']}")
            
            # Create test market data
            market_data = {
                "timestamp": test_case["timestamp"],
                "market_overview": {"test": "data"},
                "futures_premium": {},
                "smart_money_index": {},
                "whale_activity": {},
                "top_performers": [],
                "trading_signals": [],
                "notable_news": []
            }
            
            # Test HTML generation first (lighter weight)
            success = await generator.generate_market_html_report(
                market_data, 
                output_path=f"test_timestamp_{test_case['name'].replace(' ', '_').lower()}.html"
            )
            
            if success:
                # Check if the generated HTML file contains the expected year
                html_files = [f for f in os.listdir('.') if f.startswith('test_timestamp_')]
                if html_files:
                    latest_html = max(html_files, key=os.path.getctime)
                    with open(latest_html, 'r') as f:
                        content = f.read()
                        
                    if test_case["expected_year"] in content and "1970" not in content:
                        print(f"   ✅ PASSED: Generated correct date (contains {test_case['expected_year']}, no 1970)")
                    else:
                        print(f"   ❌ FAILED: Generated incorrect date (missing {test_case['expected_year']} or contains 1970)")
                        all_passed = False
                        
                    # Clean up test file
                    try:
                        os.remove(latest_html)
                    except:
                        pass
                else:
                    print(f"   ❌ FAILED: No HTML file generated")
                    all_passed = False
            else:
                print(f"   ❌ FAILED: HTML generation failed")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Error in timestamp test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_dark_pdf():
    """Test WeasyPrint PDF generation with dark theme."""
    
    print("🎨 Testing WeasyPrint with dark theme...")
    
    try:
        from core.reporting.pdf_generator import ReportGenerator
        
        generator = ReportGenerator()
        
        # Use the latest HTML file
        html_path = 'reports/html/market_report_NEU_20250603_120405.html'
        pdf_path = 'reports/pdf/test_dark_theme.pdf'
        
        print(f"📄 HTML: {html_path}")
        print(f"📄 PDF: {pdf_path}")
        
        if not os.path.exists(html_path):
            print(f"❌ HTML file not found: {html_path}")
            return False
        
        success = await generator.generate_pdf(html_path, pdf_path)
        
        if success and os.path.exists(pdf_path):
            size_kb = os.path.getsize(pdf_path) / 1024
            print(f"✅ Dark theme PDF generated: {pdf_path} ({size_kb:.1f} KB)")
            return True
        else:
            print("❌ PDF generation failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("🧪 Running PDF Generation Tests\n")
    
    # Test 1: Timestamp processing
    timestamp_result = await test_timestamp_processing()
    
    # Test 2: Dark theme PDF  
    pdf_result = await test_dark_pdf()
    
    print(f"\n🎯 Test Results:")
    print(f"   📅 Timestamp processing: {'✅ PASSED' if timestamp_result else '❌ FAILED'}")
    print(f"   🎨 Dark theme PDF: {'✅ PASSED' if pdf_result else '❌ FAILED'}")
    
    overall_success = timestamp_result and pdf_result
    print(f"\n🏆 Overall: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    return overall_success

if __name__ == "__main__":
    result = asyncio.run(main()) 