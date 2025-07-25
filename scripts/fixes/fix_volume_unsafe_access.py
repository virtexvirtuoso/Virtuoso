#!/usr/bin/env python3
"""
Emergency fix for unsafe dictionary access in volume indicators.
This script automatically fixes crash-prone patterns in volume_indicators.py
"""

import re
import shutil
from pathlib import Path
from datetime import datetime
import sys

def fix_volume_indicators():
    """Apply emergency fixes to volume_indicators.py"""
    
    file_path = Path("src/indicators/volume_indicators.py")
    if not file_path.exists():
        print(f"❌ Error: {file_path} not found!")
        return 0
    
    backup_path = file_path.parent / f"{file_path.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    
    # Create backup
    shutil.copy2(file_path, backup_path)
    print(f"✅ Created backup: {backup_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Store original content for comparison
    original_content = content
    
    # Count fixes
    fixes_applied = 0
    
    print("\n🔧 Applying fixes...")
    
    # Fix 1: Direct base access pattern
    # Pattern: market_data['ohlcv']['base']
    pattern1 = r"market_data\['ohlcv'\]\['base'\]"
    replacement1 = "self._safe_get_timeframe(market_data, 'base')"
    content, count1 = re.subn(pattern1, replacement1, content)
    fixes_applied += count1
    if count1 > 0:
        print(f"  ✓ Fixed {count1} instances of direct base access")
    
    # Fix 2: Direct timeframe access with variable
    # Pattern: market_data['ohlcv'][timeframe]
    pattern2 = r"market_data\['ohlcv'\]\[(\w+)\]"
    def replace_timeframe_access(match):
        timeframe_var = match.group(1)
        # Don't replace if it's already inside a get() call
        if "'ohlcv'].get(" not in match.string[max(0, match.start()-20):match.start()]:
            return f"self._safe_get_timeframe(market_data, {timeframe_var})"
        return match.group(0)
    
    content, count2 = re.subn(pattern2, replace_timeframe_access, content)
    fixes_applied += count2
    if count2 > 0:
        print(f"  ✓ Fixed {count2} instances of variable timeframe access")
    
    # Fix 3: Primary timeframe pattern (most dangerous - can crash with IndexError)
    # Pattern: primary_tf = list(market_data['ohlcv'].keys())[0]
    #          df = market_data['ohlcv'][primary_tf]
    pattern3 = r"primary_tf\s*=\s*list\(market_data\['ohlcv'\]\.keys\(\)\)\[0\]\s*\n\s*df\s*=\s*market_data\['ohlcv'\]\[primary_tf\]"
    replacement3 = """tf_data = self._get_primary_timeframe(market_data)
        if not tf_data:
            return self.get_default_result("No timeframe data available")
        primary_tf, df = tf_data"""
    
    content, count3 = re.subn(pattern3, replacement3, content, flags=re.MULTILINE)
    fixes_applied += count3
    if count3 > 0:
        print(f"  ✓ Fixed {count3} instances of primary timeframe pattern")
    
    # Fix 4: Alternative primary timeframe pattern
    # Pattern: timeframes = list(market_data['ohlcv'].keys())
    pattern4 = r"timeframes\s*=\s*list\(market_data\['ohlcv'\]\.keys\(\)\)"
    replacement4 = """ohlcv = self._safe_get_ohlcv(market_data)
        timeframes = list(ohlcv.keys()) if ohlcv else []"""
    
    content, count4 = re.subn(pattern4, replacement4, content)
    fixes_applied += count4
    if count4 > 0:
        print(f"  ✓ Fixed {count4} instances of timeframes list pattern")
    
    # Fix 5: Direct ohlcv access without .get()
    # Pattern: ohlcv_data = market_data['ohlcv']
    pattern5 = r"ohlcv_data\s*=\s*market_data\['ohlcv'\](?!\s*\.get)"
    replacement5 = "ohlcv_data = self._safe_get_ohlcv(market_data)"
    
    content, count5 = re.subn(pattern5, replacement5, content)
    fixes_applied += count5
    if count5 > 0:
        print(f"  ✓ Fixed {count5} instances of direct ohlcv assignment")
    
    # Fix 6: Add null checks after ohlcv_data assignments
    # This is more complex and requires careful pattern matching
    pattern6 = r"(ohlcv_data\s*=\s*self\._safe_get_ohlcv\(market_data\))\s*\n(?!\s*if)"
    replacement6 = r"\1\n        if not ohlcv_data:\n            return self.get_default_result('No OHLCV data available')\n"
    
    content, count6 = re.subn(pattern6, replacement6, content)
    fixes_applied += count6
    if count6 > 0:
        print(f"  ✓ Added {count6} null checks after ohlcv_data assignments")
    
    # Fix 7: Fix df assignments that might be None
    # Pattern: df = ohlcv_data.get('base') without null check
    pattern7 = r"(df\s*=\s*ohlcv_data\.get\(['\"]\w+['\"]\))\s*\n(?!\s*if\s+df\s+is)"
    replacement7 = r"\1\n        if df is None or df.empty:\n            return self.get_default_result('Missing timeframe data')\n"
    
    content, count7 = re.subn(pattern7, replacement7, content)
    fixes_applied += count7
    if count7 > 0:
        print(f"  ✓ Added {count7} null checks after df assignments")
    
    # Write the fixed content only if changes were made
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"\n✅ Applied {fixes_applied} fixes to {file_path}")
    else:
        print(f"\n✅ No unsafe patterns found in {file_path} - file is already safe!")
    
    return fixes_applied

def verify_fixes():
    """Verify that common crash patterns no longer exist"""
    
    file_path = Path("src/indicators/volume_indicators.py")
    if not file_path.exists():
        print(f"❌ Error: {file_path} not found!")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for dangerous patterns
    dangerous_patterns = [
        (r"market_data\['ohlcv'\]\['base'\]", "Direct base access"),
        (r"list\(market_data\['ohlcv'\]\.keys\(\)\)\[0\]", "Unsafe primary timeframe"),
        (r"market_data\['ohlcv'\]\[primary_tf\](?!.*get_primary_timeframe)", "Unsafe dynamic timeframe access"),
    ]
    
    print("\n🔍 Verifying fixes...")
    issues_found = False
    
    for pattern, description in dangerous_patterns:
        matches = list(re.finditer(pattern, content))
        if matches:
            print(f"  ❌ Found {len(matches)} instances of: {description}")
            for i, match in enumerate(matches[:3]):  # Show first 3
                line_num = content[:match.start()].count('\n') + 1
                print(f"     Line {line_num}: {match.group(0)}")
            if len(matches) > 3:
                print(f"     ... and {len(matches) - 3} more")
            issues_found = True
        else:
            print(f"  ✓ No instances of: {description}")
    
    return not issues_found

if __name__ == "__main__":
    print("🚨 Emergency Fix for Volume Indicators Crashes")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("src/indicators/volume_indicators.py").exists():
        print("❌ Error: Must run from project root directory!")
        print("   Current directory:", Path.cwd())
        sys.exit(1)
    
    # Apply fixes
    fixes = fix_volume_indicators()
    
    # Verify fixes
    if fixes > 0:
        success = verify_fixes()
        if success:
            print(f"\n🎉 Emergency fix complete! Fixed {fixes} unsafe access patterns.")
            print("   Volume indicators are now crash-resistant!")
        else:
            print(f"\n⚠️  Some dangerous patterns may still exist. Manual review recommended.")
    else:
        print(f"\n✅ No fixes needed - volume indicators are already safe!")