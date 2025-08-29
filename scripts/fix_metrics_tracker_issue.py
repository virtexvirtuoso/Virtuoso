#!/usr/bin/env python3
"""
Fix for the metrics_tracker NoneType error in monitor_refactored.py.

This script patches the monitor to add proper null checks and error handling.
"""

import os
import shutil
from datetime import datetime

def fix_metrics_tracker_issue():
    """Fix the metrics_tracker None issue in monitor_refactored.py."""
    
    monitor_file = "src/monitoring/monitor_refactored.py"
    backup_file = f"{monitor_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"🔧 Fixing metrics_tracker issue in {monitor_file}")
    
    # Create backup
    shutil.copy2(monitor_file, backup_file)
    print(f"✅ Created backup: {backup_file}")
    
    # Read the file
    with open(monitor_file, 'r') as f:
        content = f.read()
    
    # Find and replace the problematic line
    old_code = """            # Step 6: Update metrics
            await self.metrics_tracker.update_symbol_metrics(symbol_str, market_data)"""
    
    new_code = """            # Step 6: Update metrics (with null check)
            if self.metrics_tracker is not None:
                await self.metrics_tracker.update_symbol_metrics(symbol_str, market_data)
            else:
                self.logger.warning(f"⚠️  Metrics tracker not initialized, skipping metrics update for {symbol_str}")"""
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        print("✅ Applied metrics_tracker null check patch")
    else:
        print("⚠️  Could not find exact match, trying alternative approach...")
        
        # Try alternative pattern
        alt_old_code = "await self.metrics_tracker.update_symbol_metrics(symbol_str, market_data)"
        alt_new_code = """# Check if metrics_tracker is initialized
            if self.metrics_tracker is not None:
                await self.metrics_tracker.update_symbol_metrics(symbol_str, market_data)
            else:
                self.logger.warning(f"⚠️  Metrics tracker not initialized, skipping metrics update for {symbol_str}")"""
        
        if alt_old_code in content:
            content = content.replace(alt_old_code, alt_new_code)
            print("✅ Applied alternative metrics_tracker null check patch")
        else:
            print("❌ ERROR: Could not find metrics_tracker update line to patch")
            return False
    
    # Write the fixed content back
    with open(monitor_file, 'w') as f:
        f.write(content)
    
    print("✅ Patched monitor_refactored.py with metrics_tracker null checks")
    return True

def main():
    """Apply the metrics_tracker fix."""
    print("VIRTUOSO CCXT - METRICS TRACKER FIX")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("src/monitoring/monitor_refactored.py"):
        print("❌ ERROR: Must run from Virtuoso_ccxt root directory")
        return 1
    
    # Apply the fix
    if fix_metrics_tracker_issue():
        print("\n✅ Metrics tracker fix applied successfully!")
        print("This should resolve the 'NoneType' object has no attribute 'update_symbol_metrics' error.")
        print("The fix adds proper null checking for metrics_tracker.")
        return 0
    else:
        print("\n❌ Failed to apply metrics tracker fix")
        return 1

if __name__ == "__main__":
    exit(main())