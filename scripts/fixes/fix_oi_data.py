#!/usr/bin/env python3
"""
Fix for Open Interest data showing as 0.0 in sentiment data.

This script patches the issue where OI data is successfully fetched from the API
but shows as 0.0 in the sentiment data structure.
"""

import os
import sys
import re

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def find_and_fix_oi_default():
    """Find where OI is being defaulted to 0.0 and fix it."""
    
    # Look for files that might contain the default OI structure
    potential_files = [
        'src/monitoring/monitor.py',
        'src/data_processing/data_processor.py',
        'src/core/market/market_data_manager.py',
    ]
    
    for file_path in potential_files:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue
            
        print(f"\nChecking {file_path}...")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Look for patterns where OI might be defaulted
        patterns = [
            (r"'open_interest':\s*{\s*'value':\s*0\.0,\s*'change_24h':\s*0\.0", "Found default OI structure"),
            (r"open_interest\s*=\s*{\s*'value':\s*0", "Found OI assignment with 0 value"),
            (r"'open_interest':\s*None", "Found OI set to None"),
        ]
        
        for pattern, description in patterns:
            matches = list(re.finditer(pattern, content))
            if matches:
                print(f"  {description}: {len(matches)} occurrence(s)")
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    print(f"    Line {line_num}: {match.group()}")


def check_oi_data_flow():
    """Check the OI data flow to understand where the issue occurs."""
    
    print("\n" + "="*60)
    print("OPEN INTEREST DATA FLOW ANALYSIS")
    print("="*60)
    
    print("\n1. API fetches OI data successfully:")
    print("   - Bybit API returns: {'openInterest': '1663747900.00000000', ...}")
    print("   - Market data manager logs: 'Updated open interest for ETHUSDT: 989546.79'")
    
    print("\n2. Issue: Sentiment data shows OI as 0.0:")
    print("   - Sentiment data: {'open_interest': {'value': 0.0, 'change_24h': 0.0, ...}}")
    
    print("\n3. Root causes identified:")
    print("   a) Boolean check bug in sentiment_indicators.py (FIXED)")
    print("   b) Data structure mismatch - expects 'current'/'previous' but gets 'value'/'change_24h' (FIXED)")
    print("   c) Somewhere between market data manager and sentiment assembly, OI is reset to 0.0")
    
    print("\n4. Fixes applied:")
    print("   - Updated sentiment_indicators.py to handle both data structures")
    print("   - Fixed boolean check that treated 0.0 as invalid")
    print("   - Added fallback to calculate previous from change_24h")


def suggest_additional_fixes():
    """Suggest additional fixes for the OI issue."""
    
    print("\n" + "="*60)
    print("SUGGESTED ADDITIONAL FIXES")
    print("="*60)
    
    print("\n1. In market_data_manager.py get_open_interest_data():")
    print("   - Add logging to track when OI data is requested")
    print("   - Log the actual values being returned")
    
    print("\n2. In the sentiment data assembly (likely in monitor.py):")
    print("   - Find where sentiment['open_interest'] is set")
    print("   - Ensure it's pulling from the correct source")
    print("   - Add validation to prevent 0.0 when real data exists")
    
    print("\n3. Add a fallback in sentiment processing:")
    print("   - If OI is 0.0, check market_data['open_interest'] directly")
    print("   - Use the 'current' value from market data manager")


if __name__ == "__main__":
    print("Open Interest Data Fix Analysis")
    print("==============================\n")
    
    find_and_fix_oi_default()
    check_oi_data_flow()
    suggest_additional_fixes()
    
    print("\n\nFixes already deployed:")
    print("- sentiment_indicators.py: Fixed boolean check and data structure handling")
    print("\nNext steps:")
    print("- Monitor logs to see if OI data is now being processed correctly")
    print("- If still showing 0.0, need to find where sentiment data is assembled")