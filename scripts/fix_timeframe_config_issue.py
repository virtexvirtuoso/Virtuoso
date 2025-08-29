#!/usr/bin/env python3
"""
Fix for timeframe configuration issue where dict objects are passed instead of strings.

The error: "Invalid timeframe type: <class 'dict'>, value: {'interval': 1, 'required': 1000, ...}"
indicates that the timeframe configuration is passing complex objects instead of simple strings.
"""

import os
import shutil
from datetime import datetime

def fix_data_collector_timeframes():
    """Fix the DataCollector timeframe configuration."""
    
    data_collector_file = "src/monitoring/data_collector.py"
    backup_file = f"{data_collector_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"🔧 Fixing DataCollector timeframe configuration in {data_collector_file}")
    
    # Create backup
    shutil.copy2(data_collector_file, backup_file)
    print(f"✅ Created backup: {backup_file}")
    
    # Read the file
    with open(data_collector_file, 'r') as f:
        content = f.read()
    
    # Find and replace the timeframe configuration
    old_code = """        # Configuration for data fetching
        self.timeframes = self.config.get('timeframes', {
            'ltf': '5m',   # Low timeframe
            'mtf': '30m',  # Medium timeframe
            'htf': '4h'    # High timeframe
        })"""
    
    new_code = """        # Configuration for data fetching
        # Handle complex timeframe config or fallback to simple strings
        raw_timeframes = self.config.get('timeframes', {
            'ltf': '5m',   # Low timeframe
            'mtf': '30m',  # Medium timeframe
            'htf': '4h'    # High timeframe
        })
        
        # Extract interval strings from complex config if needed
        self.timeframes = {}
        for tf_name, tf_config in raw_timeframes.items():
            if isinstance(tf_config, dict) and 'interval' in tf_config:
                # Convert interval minutes to timeframe string
                interval_minutes = tf_config['interval']
                if interval_minutes == 1:
                    self.timeframes[tf_name] = '1m'
                elif interval_minutes == 5:
                    self.timeframes[tf_name] = '5m'
                elif interval_minutes == 30:
                    self.timeframes[tf_name] = '30m'
                elif interval_minutes == 240:
                    self.timeframes[tf_name] = '4h'
                elif interval_minutes == 60:
                    self.timeframes[tf_name] = '1h'
                elif interval_minutes == 15:
                    self.timeframes[tf_name] = '15m'
                else:
                    self.timeframes[tf_name] = f'{interval_minutes}m'
            elif isinstance(tf_config, str):
                # Already a string, use as-is
                self.timeframes[tf_name] = tf_config
            else:
                # Fallback to default
                default_map = {'ltf': '5m', 'mtf': '30m', 'htf': '4h', 'base': '1m'}
                self.timeframes[tf_name] = default_map.get(tf_name, '1m')"""
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        print("✅ Applied timeframe configuration fix")
    else:
        print("⚠️  Could not find exact timeframe config, trying line-by-line approach...")
        
        # Alternative approach - find and replace just the assignment
        alt_old = "self.timeframes = self.config.get('timeframes',"
        if alt_old in content:
            lines = content.split('\n')
            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                if alt_old in line:
                    # Replace the entire timeframe configuration section
                    new_lines.append("        # Handle complex timeframe config or fallback to simple strings")
                    new_lines.append("        raw_timeframes = self.config.get('timeframes', {")
                    new_lines.append("            'ltf': '5m',   # Low timeframe")
                    new_lines.append("            'mtf': '30m',  # Medium timeframe")
                    new_lines.append("            'htf': '4h'    # High timeframe")
                    new_lines.append("        })")
                    new_lines.append("")
                    new_lines.append("        # Extract interval strings from complex config if needed")
                    new_lines.append("        self.timeframes = {}")
                    new_lines.append("        for tf_name, tf_config in raw_timeframes.items():")
                    new_lines.append("            if isinstance(tf_config, dict) and 'interval' in tf_config:")
                    new_lines.append("                # Convert interval minutes to timeframe string")
                    new_lines.append("                interval_minutes = tf_config['interval']")
                    new_lines.append("                if interval_minutes == 1:")
                    new_lines.append("                    self.timeframes[tf_name] = '1m'")
                    new_lines.append("                elif interval_minutes == 5:")
                    new_lines.append("                    self.timeframes[tf_name] = '5m'")
                    new_lines.append("                elif interval_minutes == 30:")
                    new_lines.append("                    self.timeframes[tf_name] = '30m'")
                    new_lines.append("                elif interval_minutes == 240:")
                    new_lines.append("                    self.timeframes[tf_name] = '4h'")
                    new_lines.append("                elif interval_minutes == 60:")
                    new_lines.append("                    self.timeframes[tf_name] = '1h'")
                    new_lines.append("                elif interval_minutes == 15:")
                    new_lines.append("                    self.timeframes[tf_name] = '15m'")
                    new_lines.append("                else:")
                    new_lines.append("                    self.timeframes[tf_name] = f'{interval_minutes}m'")
                    new_lines.append("            elif isinstance(tf_config, str):")
                    new_lines.append("                # Already a string, use as-is")
                    new_lines.append("                self.timeframes[tf_name] = tf_config")
                    new_lines.append("            else:")
                    new_lines.append("                # Fallback to default")
                    new_lines.append("                default_map = {'ltf': '5m', 'mtf': '30m', 'htf': '4h', 'base': '1m'}")
                    new_lines.append("                self.timeframes[tf_name] = default_map.get(tf_name, '1m')")
                    
                    # Skip the original lines (find the closing brace)
                    while i < len(lines) and not lines[i].strip().endswith('}'):
                        i += 1
                    # Skip the closing brace line too
                    i += 1
                    continue
                else:
                    new_lines.append(line)
                i += 1
            
            content = '\n'.join(new_lines)
            print("✅ Applied alternative timeframe configuration fix")
        else:
            print("❌ ERROR: Could not find timeframe configuration to fix")
            return False
    
    # Write the fixed content back
    with open(data_collector_file, 'w') as f:
        f.write(content)
    
    print("✅ Fixed DataCollector timeframe configuration")
    return True

def main():
    """Apply the timeframe configuration fix."""
    print("VIRTUOSO CCXT - TIMEFRAME CONFIGURATION FIX")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("src/monitoring/data_collector.py"):
        print("❌ ERROR: Must run from Virtuoso_ccxt root directory")
        return 1
    
    # Apply the fix
    if fix_data_collector_timeframes():
        print("\n✅ Timeframe configuration fix applied successfully!")
        print("This should resolve the 'Invalid timeframe type: <class 'dict'>' error.")
        print("The fix extracts simple string timeframes from complex config objects.")
        return 0
    else:
        print("\n❌ Failed to apply timeframe configuration fix")
        return 1

if __name__ == "__main__":
    exit(main())