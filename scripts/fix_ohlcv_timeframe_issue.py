#!/usr/bin/env python3
"""
Fix for the OHLCV timeframe unhashable dict issue.

This script patches the bybit.py file to add proper type checking and error handling
for the timeframe parameter in fetch_ohlcv method.
"""

import os
import shutil
from datetime import datetime

def fix_bybit_fetch_ohlcv():
    """Fix the fetch_ohlcv method in bybit.py to handle invalid timeframe types."""
    
    bybit_file = "src/core/exchanges/bybit.py"
    backup_file = f"{bybit_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"🔧 Fixing OHLCV timeframe issue in {bybit_file}")
    
    # Create backup
    shutil.copy2(bybit_file, backup_file)
    print(f"✅ Created backup: {backup_file}")
    
    # Read the file
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Find and replace the problematic line
    old_code = """        try:
            # Convert the timeframe to Bybit format if needed
            tf = self.TIMEFRAME_MAP.get(timeframe, timeframe)"""
    
    new_code = """        try:
            # Validate and convert the timeframe to Bybit format
            if not isinstance(timeframe, str):
                self.logger.error(f"❌ ERROR: Invalid timeframe type: {type(timeframe)}, value: {timeframe}")
                if isinstance(timeframe, dict) and 'timeframe' in timeframe:
                    timeframe = timeframe['timeframe']
                elif isinstance(timeframe, dict) and 'interval' in timeframe:
                    timeframe = timeframe['interval']
                else:
                    self.logger.error(f"❌ ERROR: Cannot extract timeframe string from: {timeframe}")
                    return []
            
            # Convert the timeframe to Bybit format if needed
            tf = self.TIMEFRAME_MAP.get(timeframe, timeframe)"""
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        print("✅ Applied timeframe type checking patch")
    else:
        print("⚠️  Could not find exact match for timeframe code, trying alternative approach...")
        
        # Try alternative pattern
        alt_old_code = "tf = self.TIMEFRAME_MAP.get(timeframe, timeframe)"
        alt_new_code = """# Validate timeframe type first
            if not isinstance(timeframe, str):
                self.logger.error(f"❌ ERROR: Invalid timeframe type: {type(timeframe)}, value: {timeframe}")
                if isinstance(timeframe, dict) and 'timeframe' in timeframe:
                    timeframe = timeframe['timeframe']
                elif isinstance(timeframe, dict) and 'interval' in timeframe:
                    timeframe = timeframe['interval']
                else:
                    self.logger.error(f"❌ ERROR: Cannot extract timeframe string from: {timeframe}")
                    return []
            
            tf = self.TIMEFRAME_MAP.get(timeframe, timeframe)"""
        
        if alt_old_code in content:
            content = content.replace(alt_old_code, alt_new_code)
            print("✅ Applied alternative timeframe type checking patch")
        else:
            print("❌ ERROR: Could not find timeframe conversion line to patch")
            return False
    
    # Write the fixed content back
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    print("✅ Patched bybit.py with timeframe type validation")
    return True

def main():
    """Apply the OHLCV fix."""
    print("VIRTUOSO CCXT - OHLCV TIMEFRAME FIX")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("src/core/exchanges/bybit.py"):
        print("❌ ERROR: Must run from Virtuoso_ccxt root directory")
        return 1
    
    # Apply the fix
    if fix_bybit_fetch_ohlcv():
        print("\n✅ OHLCV fix applied successfully!")
        print("This should resolve the 'unhashable type: dict' error.")
        print("The fix adds proper type checking for the timeframe parameter.")
        return 0
    else:
        print("\n❌ Failed to apply OHLCV fix")
        return 1

if __name__ == "__main__":
    exit(main())