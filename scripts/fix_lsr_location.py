#!/usr/bin/env python3
"""
Fix LSR data location issue - confluence analyzer looking in wrong place
Problem: LSR is in market_data['long_short_ratio'] but analyzer expects market_data['sentiment']['long_short_ratio']
"""

import sys
import os

def fix_lsr_location():
    """Fix the LSR data location issue in confluence analyzer"""
    
    confluence_file = "src/core/analysis/confluence.py"
    
    print(f"Fixing LSR location issue in {confluence_file}...")
    
    with open(confluence_file, 'r') as f:
        content = f.read()
    
    # Find and fix the section where enhanced_sentiment is created
    search_text = """                'long_short_ratio': {
                    'long': 50.0,  # Default values for long/short positions
                    'short': 50.0,
                    'timestamp': int(time.time() * 1000)
                },"""
    
    replacement_text = """                'long_short_ratio': {
                    'long': 50.0,  # Default values for long/short positions
                    'short': 50.0,
                    'timestamp': int(time.time() * 1000)
                },"""
    
    if search_text in content:
        # Add code to check for LSR in the right place
        insert_after = "# Get existing sentiment data"
        if insert_after in content:
            lines = content.split('\n')
            new_lines = []
            for i, line in enumerate(lines):
                new_lines.append(line)
                if insert_after in line:
                    # Add LSR extraction logic right after getting sentiment data
                    new_lines.append("            ")
                    new_lines.append("            # [LSR-LOCATION-FIX] Check for LSR in both possible locations")
                    new_lines.append("            lsr_data = None")
                    new_lines.append("            if 'long_short_ratio' in market_data:")
                    new_lines.append("                lsr_data = market_data['long_short_ratio']")
                    new_lines.append("                self.logger.info(f'[LSR-FIX] Found LSR at market_data level: {lsr_data}')")
                    new_lines.append("            elif sentiment_data and 'long_short_ratio' in sentiment_data:")
                    new_lines.append("                lsr_data = sentiment_data['long_short_ratio']")
                    new_lines.append("                self.logger.info(f'[LSR-FIX] Found LSR in sentiment_data: {lsr_data}')")
                    new_lines.append("            else:")
                    new_lines.append("                self.logger.warning('[LSR-FIX] No LSR data found in either location')")
            
            content = '\n'.join(new_lines)
    
    # Now fix where the default LSR is set to use the actual data if available
    search_default = "'long_short_ratio': {"
    if search_default in content:
        lines = content.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            if search_default in line and i > 0 and 'enhanced_sentiment = {' in '\n'.join(lines[max(0,i-10):i]):
                # This is the default setting in enhanced_sentiment
                new_lines.append(line)
                # Check if next lines are the default values
                if i+3 < len(lines) and "'long': 50.0" in lines[i+1]:
                    # Replace the default with actual data if available
                    new_lines.append("                    'long': lsr_data['long'] if lsr_data and 'long' in lsr_data else 50.0,")
                    new_lines.append("                    'short': lsr_data['short'] if lsr_data and 'short' in lsr_data else 50.0,")
                    new_lines.append("                    'timestamp': lsr_data.get('timestamp', int(time.time() * 1000)) if lsr_data else int(time.time() * 1000)")
                    # Skip the original default lines
                    i += 3
                    while i < len(lines) and 'timestamp' not in lines[i]:
                        i += 1
                    continue
            else:
                new_lines.append(line)
        
        content = '\n'.join(new_lines)
    
    # Write the fixed content
    with open(confluence_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed LSR location issue in {confluence_file}")
    
    # Also ensure monitor passes LSR correctly
    monitor_file = "src/monitoring/monitor.py"
    if os.path.exists(monitor_file):
        print(f"\nChecking LSR passing in {monitor_file}...")
        
        with open(monitor_file, 'r') as f:
            content = f.read()
        
        # Add logging to see how data is passed
        if "confluence_analyzer.analyze(market_data)" in content and "[LSR-MONITOR]" not in content:
            lines = content.split('\n')
            new_lines = []
            for i, line in enumerate(lines):
                if "confluence_analyzer.analyze(market_data)" in line:
                    # Add logging before the call
                    indent = len(line) - len(line.lstrip())
                    new_lines.append(' ' * indent + "# [LSR-MONITOR] Log what we're passing to confluence")
                    new_lines.append(' ' * indent + "if 'long_short_ratio' in market_data:")
                    new_lines.append(' ' * indent + "    self.logger.info(f'[LSR-MONITOR] Passing LSR to confluence: {market_data[\"long_short_ratio\"]}')")
                    new_lines.append(' ' * indent + "else:")
                    new_lines.append(' ' * indent + "    self.logger.warning('[LSR-MONITOR] No LSR in market_data being passed to confluence')")
                new_lines.append(line)
            
            content = '\n'.join(new_lines)
            with open(monitor_file, 'w') as f:
                f.write(content)
            print(f"✅ Added LSR monitoring to {monitor_file}")
    
    print("\n✅ LSR location fix complete!")
    print("\nNext steps:")
    print("1. Deploy to VPS:")
    print("   rsync -avz src/core/analysis/confluence.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/core/analysis/")
    print("   rsync -avz src/monitoring/monitor.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/")
    print("2. Restart service: ssh vps 'sudo systemctl restart virtuoso-trading.service'")
    print("3. Check logs: ssh vps 'sudo journalctl -u virtuoso-trading.service -f | grep LSR'")

if __name__ == "__main__":
    fix_lsr_location()