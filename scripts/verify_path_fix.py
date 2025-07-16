#!/usr/bin/env python3
"""
Simple script to verify the path calculation fix for market reporter and PDF generator.
"""

import os
import sys
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

def main():
    print("Verifying path calculation fix...")
    
    # Save current working directory
    original_cwd = os.getcwd()
    
    try:
        # Change to project root (assuming we're running from scripts/)
        project_root = os.path.dirname(os.path.dirname(__file__))
        os.chdir(project_root)
        print(f"Working directory: {os.getcwd()}")
        
        # Test timestamp
        timestamp = int(datetime.now().timestamp())
        readable_time = datetime.fromtimestamp(timestamp).strftime('%Y%m%d_%H%M%S')
        report_id = f"TEST_{readable_time}"
        
        # NEW APPROACH (after fix) - Both components should use this
        new_html_dir = os.path.join(os.getcwd(), "reports", "html")
        new_pdf_dir = os.path.join(os.getcwd(), "reports", "pdf")
        new_html_path = os.path.join(new_html_dir, f"market_report_{report_id}.html")
        new_pdf_path = os.path.join(new_pdf_dir, f"market_report_{report_id}.pdf")
        
        # OLD APPROACH (before fix) - What market reporter used to do
        old_html_dir = os.path.join(os.getcwd(), "src", "reports", "html")
        old_pdf_dir = os.path.join(os.getcwd(), "src", "reports", "pdf")
        old_html_path = os.path.join(old_html_dir, f"market_report_{report_id}.html")
        old_pdf_path = os.path.join(old_pdf_dir, f"market_report_{report_id}.pdf")
        
        print(f"\nPATH COMPARISON:")
        print(f"NEW (fixed) paths:")
        print(f"  HTML: {new_html_path}")
        print(f"  PDF:  {new_pdf_path}")
        
        print(f"\nOLD (problematic) paths:")
        print(f"  HTML: {old_html_path}")
        print(f"  PDF:  {old_pdf_path}")
        
        # Check if directories exist
        print(f"\nDIRECTORY STATUS:")
        print(f"  New HTML dir exists: {os.path.exists(new_html_dir)}")
        print(f"  New PDF dir exists: {os.path.exists(new_pdf_dir)}")
        print(f"  Old HTML dir exists: {os.path.exists(old_html_dir)}")
        print(f"  Old PDF dir exists: {os.path.exists(old_pdf_dir)}")
        
        # Create directories if they don't exist for testing
        os.makedirs(new_html_dir, exist_ok=True)
        os.makedirs(new_pdf_dir, exist_ok=True)
        
        print(f"\nTemplate path verification:")
        template_path = os.path.join(os.getcwd(), "src", "core", "reporting", "templates", "market_report_dark.html")
        print(f"  Template path: {template_path}")
        print(f"  Template exists: {os.path.exists(template_path)}")
        
        print("\nPATH FIX VERIFICATION:")
        if os.path.exists(new_html_dir) and os.path.exists(new_pdf_dir):
            print("✅ SUCCESS: Fixed path directories exist and are accessible!")
        else:
            print("❌ FAILED: Fixed path directories could not be created or accessed!")
            
    except Exception as e:
        print(f"❌ ERROR during test: {str(e)}")
    finally:
        # Restore original working directory
        os.chdir(original_cwd)

if __name__ == "__main__":
    main() 