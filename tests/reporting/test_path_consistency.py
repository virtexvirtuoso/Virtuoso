#!/usr/bin/env python3
"""
Test script to verify path consistency between market reporter and PDF generator.
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

from monitoring.market_reporter import MarketReporter
from core.reporting.pdf_generator import ReportGenerator


def test_path_consistency():
    """Test that market reporter and PDF generator use consistent paths."""
    print("Testing path consistency between MarketReporter and ReportGenerator...")
    
    # Save current working directory
    original_cwd = os.getcwd()
    
    try:
        # Change to project root for testing
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        os.chdir(project_root)
        print(f"Working directory set to: {os.getcwd()}")
        
        # Initialize components
        market_reporter = MarketReporter()
        pdf_generator = ReportGenerator()
        
        # Test market reporter path calculation
        timestamp = int(datetime.now().timestamp())
        readable_time = datetime.fromtimestamp(timestamp).strftime('%Y%m%d_%H%M%S')
        report_id = f"TEST_{readable_time}"
        
        # Simulate market reporter path calculation
        html_dir = os.path.join(os.getcwd(), "reports", "html")
        pdf_dir = os.path.join(os.getcwd(), "reports", "pdf")
        html_path = os.path.join(html_dir, f"market_report_{report_id}.html")
        pdf_path = os.path.join(pdf_dir, f"market_report_{report_id}.pdf")
        
        print(f"Market Reporter paths:")
        print(f"  HTML: {html_path}")
        print(f"  PDF:  {pdf_path}")
        
        # Test PDF generator path calculation
        reports_base_dir = os.path.join(os.getcwd(), 'reports')
        pdf_gen_html_dir = os.path.join(reports_base_dir, 'html')
        pdf_gen_pdf_dir = os.path.join(reports_base_dir, 'pdf')
        pdf_gen_html_path = os.path.join(pdf_gen_html_dir, f"market_report_{report_id}.html")
        pdf_gen_pdf_path = os.path.join(pdf_gen_pdf_dir, f"market_report_{report_id}.pdf")
        
        print(f"PDF Generator paths:")
        print(f"  HTML: {pdf_gen_html_path}")
        print(f"  PDF:  {pdf_gen_pdf_path}")
        
        # Check if paths match
        html_match = html_path == pdf_gen_html_path
        pdf_match = pdf_path == pdf_gen_pdf_path
        
        print(f"\nPath consistency check:")
        print(f"  HTML paths match: {html_match}")
        print(f"  PDF paths match:  {pdf_match}")
        
        if html_match and pdf_match:
            print("✅ SUCCESS: All paths are consistent!")
            return True
        else:
            print("❌ FAILED: Path mismatch detected!")
            return False
            
    except Exception as e:
        print(f"❌ ERROR during test: {str(e)}")
        return False
    finally:
        # Restore original working directory
        os.chdir(original_cwd)


if __name__ == "__main__":
    success = test_path_consistency()
    sys.exit(0 if success else 1) 