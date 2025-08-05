#!/usr/bin/env python3
"""
Script to add the call to the trade enhancements method in the correct location
"""

import re

def fix_monitor_call():
    """Add the enhancement method call in the correct location"""
    
    print("🔧 **FIXING MONITOR.PY ENHANCEMENT CALL**")
    print("=" * 50)
    
    # Read the file
    with open("src/monitoring/monitor.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Pattern to find the end of the _monitor_whale_activity method
    # We want to add the call after the distribution alert logic but before the except clause
    pattern = r"(self\.logger\.info\(f\"Sent whale distribution alert for \{symbol\}: \$\{abs\(net_usd_value\):\,\.2f\}\"\)\s+)(except Exception as e:)"
    
    # Replacement to add the else clause and enhancement call
    replacement = r'''\1
        else:
            # ENHANCEMENT: When no traditional whale alerts are triggered,
            # check for trade-based patterns that might be missed
            await self._check_trade_enhancements(
                symbol, current_activity, current_price,
                accumulation_threshold, min_order_count, market_percentage
            )
            
        \2'''
    
    # Make the replacement
    new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        # Write back to file
        with open("src/monitoring/monitor.py", "w", encoding="utf-8") as f:
            f.write(new_content)
        
        print("✅ Enhancement call added successfully!")
        print("📍 Location: After whale distribution alert logic")
        print("🎯 Purpose: Run when no traditional whale alerts are triggered")
        
        return True
    else:
        print("❌ Could not find the correct location to add the enhancement call")
        print("🔍 Searching for alternative patterns...")
        
        # Try a simpler pattern
        pattern2 = r"(self\.logger\.info\(f\"Sent whale distribution alert.*?\"\))\s+(except Exception as e:)"
        new_content = re.sub(pattern2, replacement, content, flags=re.DOTALL)
        
        if new_content != content:
            with open("src/monitoring/monitor.py", "w", encoding="utf-8") as f:
                f.write(new_content)
            print("✅ Enhancement call added with alternative pattern!")
            return True
        else:
            print("❌ Could not add enhancement call automatically")
            return False

if __name__ == "__main__":
    success = fix_monitor_call()
    if success:
        print("\n🎉 **ENHANCEMENT INTEGRATION COMPLETED!**")
        print("💡 The trade enhancements will now run when traditional whale alerts don't trigger")
    else:
        print("\n⚠️ **MANUAL INTERVENTION REQUIRED**")
        print("Please add the enhancement call manually in the _monitor_whale_activity method") 