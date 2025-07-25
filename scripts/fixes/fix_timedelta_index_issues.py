#!/usr/bin/env python3
"""
Fix TimedeltaIndex issues in the codebase.

This script fixes issues where .idxmin() and .idxmax() are called on Series
with TimedeltaIndex, which causes AttributeError.
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def fix_time_diffs_idxmin(file_path: Path) -> bool:
    """Fix the time_diffs.idxmin() issue in price_structure_indicators.py"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Fix pattern 1: time_diffs.idxmin()
    pattern1 = r'(time_diffs = abs\(tf_data\.index - base_timestamp\))\s*\n\s*(nearest_idx = time_diffs\.idxmin\(\))\s*\n\s*(tf_index = tf_data\.index\.get_loc\(nearest_idx\))'
    
    replacement1 = r'\1\n                        nearest_pos = time_diffs.argmin()  # Use argmin() for TimedeltaIndex compatibility\n                        nearest_idx = tf_data.index[nearest_pos]  # Get the actual index value\n                        \3'
    
    content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE)
    
    # Fix pattern 2: swing high/low idxmax/idxmin
    pattern2 = r'(swing_high_idx = lookback_data\[\'high\'\]\.idxmax\(\))\s*\n\s*(swing_low_idx = lookback_data\[\'low\'\]\.idxmin\(\))'
    
    replacement2 = '''# Use argmax/argmin for compatibility with different index types
            swing_high_pos = lookback_data['high'].argmax()
            swing_low_pos = lookback_data['low'].argmin()
            swing_high_idx = lookback_data.index[swing_high_pos] if swing_high_pos >= 0 else None
            swing_low_idx = lookback_data.index[swing_low_pos] if swing_low_pos >= 0 else None'''
    
    content = re.sub(pattern2, replacement2, content, flags=re.MULTILINE)
    
    if content != original_content:
        # Create backup
        backup_path = file_path.with_suffix('.py.backup_timedelta_fix')
        with open(backup_path, 'w') as f:
            f.write(original_content)
        
        # Write fixed content
        with open(file_path, 'w') as f:
            f.write(content)
        
        print(f"✓ Fixed {file_path}")
        print(f"  Backup saved to: {backup_path}")
        return True
    
    return False

def add_defensive_checks_for_volume_profile(file_path: Path) -> bool:
    """Add defensive checks for volume profile POC calculation"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern to find poc = float(volume_profile.idxmax())
    pattern = r'(poc[_level]* = float\(volume_profile\.idxmax\(\)\))'
    
    # Check if we need to add defensive check
    if re.search(pattern, content) and 'isinstance(volume_profile.index, pd.TimedeltaIndex)' not in content:
        # Add import if needed
        if 'import pandas as pd' not in content:
            content = content.replace('import logging', 'import logging\nimport pandas as pd', 1)
        
        # Replace with defensive version
        replacement = '''# Defensive check for index type
            if isinstance(volume_profile.index, pd.TimedeltaIndex):
                poc_pos = volume_profile.argmax()
                \1 = float(volume_profile.index[poc_pos].total_seconds()) if poc_pos >= 0 else 0
            else:
                \1'''
        
        content = re.sub(pattern, replacement, content)
        
        if content != original_content:
            # Create backup
            backup_path = file_path.with_suffix('.py.backup_volume_profile_fix')
            with open(backup_path, 'w') as f:
                f.write(original_content)
            
            # Write fixed content
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"✓ Added defensive checks to {file_path}")
            print(f"  Backup saved to: {backup_path}")
            return True
    
    return False

def main():
    """Main function to apply fixes"""
    
    print("Fixing TimedeltaIndex issues in the codebase...")
    print("=" * 60)
    
    fixes_applied = 0
    
    # Fix price_structure_indicators.py
    price_structure_path = project_root / 'src' / 'indicators' / 'price_structure_indicators.py'
    if price_structure_path.exists():
        if fix_time_diffs_idxmin(price_structure_path):
            fixes_applied += 1
    else:
        print(f"⚠️  File not found: {price_structure_path}")
    
    # Add defensive checks to volume indicators
    volume_indicators_path = project_root / 'src' / 'indicators' / 'volume_indicators.py'
    if volume_indicators_path.exists():
        if add_defensive_checks_for_volume_profile(volume_indicators_path):
            fixes_applied += 1
    else:
        print(f"⚠️  File not found: {volume_indicators_path}")
    
    print("\n" + "=" * 60)
    print(f"✅ Fixes applied: {fixes_applied}")
    
    if fixes_applied > 0:
        print("\nNext steps:")
        print("1. Test the changes thoroughly")
        print("2. Run the application to verify fixes")
        print("3. Consider adding unit tests for TimedeltaIndex scenarios")

if __name__ == "__main__":
    main()