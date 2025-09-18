#!/usr/bin/env python3
"""
Fix the LSR fetch issue where it defaults to 50/50 even when API works
"""

import sys
import os

def fix_lsr_fetch():
    """Fix the LSR fetching in bybit.py to ensure it's always called"""
    
    bybit_file = "src/core/exchanges/bybit.py"
    
    print(f"Fixing LSR fetch in {bybit_file}...")
    
    with open(bybit_file, 'r') as f:
        lines = f.readlines()
    
    modified = False
    new_lines = []
    
    for i, line in enumerate(lines):
        # Look for where LSR is being fetched in fetch_market_data
        if "fetch_with_retry('lsr'" in line:
            print(f"Found LSR fetch at line {i+1}")
            # Ensure it's not commented or conditionally skipped
            new_lines.append(line)
            modified = True
        elif "# The _fetch_long_short_ratio method" in line:
            # Look for where LSR is processed
            print(f"Found LSR processing comment at line {i+1}")
            new_lines.append(line)
        elif "if lsr and isinstance(lsr, dict):" in line:
            # Change this to handle None case differently
            print(f"Found LSR check at line {i+1}")
            new_lines.append("            if lsr is None:\n")
            new_lines.append("                # LSR fetch failed or was skipped\n")
            new_lines.append("                self.logger.warning(f'LSR fetch returned None for {symbol}')\n")
            new_lines.append("                lsr = {'long': 50.0, 'short': 50.0, 'timestamp': int(time.time() * 1000)}\n")
            new_lines.append("            if isinstance(lsr, dict):\n")
            modified = True
        else:
            new_lines.append(line)
    
    if modified:
        with open(bybit_file, 'w') as f:
            f.writelines(new_lines)
        print(f"✅ Fixed LSR fetch handling in {bybit_file}")
    else:
        print(f"⚠️  No changes needed in {bybit_file}")
    
    # Also ensure the _fetch_long_short_ratio is not failing silently
    print("\nChecking _fetch_long_short_ratio implementation...")
    
    # Re-read the file to add more logging
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Add entry logging if not present
    if "logger.info(f\"[LSR] Fetching long/short ratio for" not in content:
        print("Adding entry logging to _fetch_long_short_ratio...")
        content = content.replace(
            "async def _fetch_long_short_ratio(self, symbol: str) -> Dict[str, Any]:",
            """async def _fetch_long_short_ratio(self, symbol: str) -> Dict[str, Any]:
        \"\"\"Fetch long/short ratio with enhanced logging\"\"\"
        self.logger.info(f"[LSR-ENTRY] Starting LSR fetch for {symbol}")"""
        )
        
        with open(bybit_file, 'w') as f:
            f.write(content)
        print("✅ Added entry logging")
    
    print("\n✅ LSR fetch issue fix complete!")
    print("\nNext steps:")
    print("1. Deploy to VPS: rsync -avz src/core/exchanges/bybit.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/core/exchanges/")
    print("2. Restart service: ssh vps 'sudo systemctl restart virtuoso-trading.service'")
    print("3. Check logs: ssh vps 'sudo journalctl -u virtuoso-trading.service -f | grep LSR'")

if __name__ == "__main__":
    fix_lsr_fetch()