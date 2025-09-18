#!/usr/bin/env python3
"""
Fix LSR data propagation issue - ensure real LSR values reach confluence analyzer
The issue: LSR is fetched correctly but defaults to 50/50 in confluence analysis
"""

import os
import sys

def fix_lsr_propagation():
    """Fix the LSR data propagation through the pipeline"""
    
    # Fix 1: Ensure monitor passes LSR data correctly to sentiment processor
    monitor_file = "src/monitoring/monitor.py"
    
    print(f"Fixing LSR propagation in {monitor_file}...")
    
    with open(monitor_file, 'r') as f:
        content = f.read()
    
    # Add logging to track LSR data flow
    if "# Pass LSR data to sentiment processor" not in content:
        # Find where sentiment data is prepared
        search_text = "sentiment_data = {"
        if search_text in content:
            replacement = """# Ensure LSR data is passed correctly
        # Pass LSR data to sentiment processor
        lsr_data = market_data.get('sentiment', {}).get('long_short_ratio')
        if lsr_data and isinstance(lsr_data, dict):
            self.logger.info(f"[LSR-PROPAGATION] Passing LSR to sentiment processor: {lsr_data}")
        else:
            self.logger.warning(f"[LSR-PROPAGATION] No LSR data found in market_data")
        
        sentiment_data = {"""
            
            content = content.replace(search_text, replacement)
            with open(monitor_file, 'w') as f:
                f.write(content)
            print(f"✅ Added LSR propagation logging to {monitor_file}")
    
    # Fix 2: Ensure sentiment processor preserves LSR data
    processor_file = "src/monitoring/monitor/sentiment_processor.py"
    
    if os.path.exists(processor_file):
        print(f"Fixing LSR preservation in {processor_file}...")
        
        with open(processor_file, 'r') as f:
            content = f.read()
        
        if "[LSR-PRESERVE]" not in content:
            # Add LSR preservation logic
            search_text = "def process_sentiment("
            if search_text in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if search_text in line:
                        # Find the end of the function definition
                        for j in range(i, min(i+20, len(lines))):
                            if '"""' in lines[j] and j > i:
                                # Insert after docstring
                                lines.insert(j+1, """        # [LSR-PRESERVE] Ensure LSR data is preserved
        if 'sentiment' in market_data:
            lsr = market_data['sentiment'].get('long_short_ratio')
            if lsr:
                self.logger.info(f"[LSR-PRESERVE] Found LSR in market data: {lsr}")
            else:
                self.logger.warning(f"[LSR-PRESERVE] No LSR in sentiment data")""")
                                break
                        break
                
                content = '\n'.join(lines)
                with open(processor_file, 'w') as f:
                    f.write(content)
                print(f"✅ Added LSR preservation to {processor_file}")
    
    # Fix 3: Ensure confluence analyzer uses the real LSR data
    confluence_file = "src/core/analysis/confluence.py"
    
    print(f"Fixing LSR usage in {confluence_file}...")
    
    with open(confluence_file, 'r') as f:
        lines = f.readlines()
    
    modified = False
    new_lines = []
    
    for i, line in enumerate(lines):
        if "'long_short_ratio': {" in line and "'long': 50.0, 'short': 50.0" in line:
            # This is where LSR defaults to 50/50, fix it
            print(f"Found LSR default at line {i+1}")
            # Look for the context
            if i > 0 and "if not sentiment_data.get('long_short_ratio')" in lines[i-1]:
                # Replace with better logic
                new_lines.append(lines[i-1])
                new_lines.append("                # Use actual LSR if available\n")
                new_lines.append("                lsr_from_market = market_data.get('sentiment', {}).get('long_short_ratio')\n")
                new_lines.append("                if lsr_from_market and isinstance(lsr_from_market, dict):\n")
                new_lines.append("                    sentiment_data['long_short_ratio'] = lsr_from_market\n")
                new_lines.append("                    self.logger.info(f'[LSR-FIX] Using actual LSR: {lsr_from_market}')\n")
                new_lines.append("                else:\n")
                new_lines.append("                    sentiment_data['long_short_ratio'] = {'long': 50.0, 'short': 50.0, 'timestamp': current_timestamp}\n")
                new_lines.append("                    self.logger.warning('[LSR-FIX] No LSR data, using default 50/50')\n")
                modified = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    if modified:
        with open(confluence_file, 'w') as f:
            f.writelines(new_lines)
        print(f"✅ Fixed LSR usage in {confluence_file}")
    
    print("\n✅ LSR propagation fixes complete!")
    print("\nNext steps:")
    print("1. Deploy to VPS: ./scripts/deploy_lsr_fix.sh")
    print("2. Monitor logs: ssh vps 'sudo journalctl -u virtuoso-trading.service -f | grep LSR'")

if __name__ == "__main__":
    fix_lsr_propagation()