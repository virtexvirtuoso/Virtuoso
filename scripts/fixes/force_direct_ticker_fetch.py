#!/usr/bin/env python3
"""
Force Direct Ticker Fetch for Market Overview

This script modifies the market overview calculation to bypass top_symbols_manager 
and use direct ticker fetching with the fixed field mappings.
"""

import os
import re

def force_direct_ticker_fetch():
    """Modify market overview to bypass top_symbols_manager and use direct ticker fetch"""
    reporter_file = "src/monitoring/market_reporter.py"
    
    with open(reporter_file, 'r') as f:
        content = f.read()
    
    # Find the market overview calculation function
    pattern = r"(async def _calculate_market_overview\(self, symbols: List\[str\]\) -> Dict\[str, Any\]:.*?)(# Try getting data from top_symbols_manager first\s+if self\.top_symbols_manager:.*?continue)"
    
    replacement = r"\1# TEMPORARY FIX: Skip top_symbols_manager and use direct ticker fetch\n                if False:  # self.top_symbols_manager:"
    
    # Replace the conditional to always skip top_symbols_manager
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Alternative approach - comment out the top_symbols_manager section
    content = re.sub(
        r"(\s+)# Try getting data from top_symbols_manager first\s+if self\.top_symbols_manager:",
        r"\1# BYPASSED: Try getting data from top_symbols_manager first\n\1if False:  # self.top_symbols_manager:",
        content
    )
    
    with open(reporter_file, 'w') as f:
        f.write(content)
    
    print("✅ Modified market overview to bypass top_symbols_manager")
    print("   This forces the use of direct ticker fetching with correct field mappings.")

def main():
    """Apply the fix"""
    print("🔧 Forcing Direct Ticker Fetch for Market Overview...")
    print("=" * 60)
    
    try:
        # Change to the project root directory
        if os.path.exists('src'):
            os.chdir('.')
        elif os.path.exists('../src'):
            os.chdir('..')
        elif os.path.exists('../../src'):
            os.chdir('../..')
        else:
            print("❌ Could not find project root directory")
            return False
        
        force_direct_ticker_fetch()
        
        print("\n🎉 Market overview will now use direct ticker fetching!")
        print("\nThis should resolve the volume/turnover 0.0 issue by:")
        print("  1. Bypassing potentially cached/stale top_symbols_manager data")
        print("  2. Using direct ticker fetch with correct baseVolume/quoteVolume fields")
        print("  3. Ensuring fresh data from the exchange API")
        print("\nGenerate a new market report to test the fix.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying fix: {str(e)}")
        return False

if __name__ == "__main__":
    main() 