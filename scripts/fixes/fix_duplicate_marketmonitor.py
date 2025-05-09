#!/usr/bin/env python3
"""
Fix script to resolve duplicate MarketMonitor class issue in monitor.py.

This script:
1. Identifies all MarketMonitor class declarations
2. Keeps only the most complete implementation
3. Ensures the implementation has all required methods
4. Removes duplicate definitions

Usage:
    python scripts/fixes/fix_duplicate_marketmonitor.py
"""

import os
import re
import sys
import shutil
from datetime import datetime

def fix_duplicate_marketmonitor():
    """Fix duplicate MarketMonitor class definitions in monitor.py."""
    
    # Define paths
    monitor_path = 'src/monitoring/monitor.py'
    
    # Check if file exists
    if not os.path.isfile(monitor_path):
        print(f"Error: {monitor_path} not found")
        return False
    
    # Create backup of original file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{monitor_path}.bak_{timestamp}"
    shutil.copy2(monitor_path, backup_path)
    print(f"Created backup at {backup_path}")
    
    # Read the current file content
    with open(monitor_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all MarketMonitor class definitions
    class_matches = list(re.finditer(r'class MarketMonitor:', content))
    
    if len(class_matches) <= 1:
        print("No duplicate MarketMonitor classes found.")
        return True
    
    print(f"Found {len(class_matches)} instances of MarketMonitor class at positions: {[m.start() for m in class_matches]}")
    
    # Extract each class definition
    class_definitions = []
    
    for i, match in enumerate(class_matches):
        start_pos = match.start()
        
        # Find the end of this class (start of next class or end of file)
        if i < len(class_matches) - 1:
            end_pos = class_matches[i+1].start()
        else:
            end_pos = len(content)
        
        # Extract the class text
        class_text = content[start_pos:end_pos]
        
        # Count methods to determine completeness
        method_count = len(re.findall(r'def\s+[a-zA-Z_]', class_text))
        async_method_count = len(re.findall(r'async\s+def\s+[a-zA-Z_]', class_text))
        
        class_definitions.append({
            'index': i,
            'start': start_pos,
            'end': end_pos,
            'text': class_text,
            'method_count': method_count + async_method_count,
        })
    
    # Find the most complete class definition (one with most methods)
    primary_class = max(class_definitions, key=lambda x: x['method_count'])
    print(f"Primary class is definition #{primary_class['index']} with {primary_class['method_count']} methods")
    
    # Check if the primary class contains required methods
    required_methods = ['get_monitored_symbols', '_is_report_time', '_calculate_report_times']
    missing_methods = []
    
    for method in required_methods:
        if not re.search(rf'def\s+{method}', primary_class['text']):
            missing_methods.append(method)
    
    # If methods are missing, add them
    if missing_methods:
        print(f"Adding missing methods to primary class: {missing_methods}")
        
        # Find appropriate position to insert methods (before the _cleanup or another method)
        insert_match = re.search(r'    async def _cleanup\(', primary_class['text'])
        if not insert_match:
            # Fallback to another common method if _cleanup isn't found
            insert_match = re.search(r'    async def _check_thresholds\(', primary_class['text'])
            
        if insert_match:
            insert_pos = insert_match.start()
            prefix = primary_class['text'][:insert_pos]
            suffix = primary_class['text'][insert_pos:]
            
            # Create method implementations - using single strings to avoid nesting issues
            method_impls = []
            
            if 'get_monitored_symbols' in missing_methods:
                method_impls.append('''
    def get_monitored_symbols(self) -> List[str]:
        """Get the list of symbols currently being monitored.
        
        Returns:
            List of symbol strings being monitored
        """
        if hasattr(self, 'symbols') and self.symbols:
            return [s['symbol'] if isinstance(s, dict) and 'symbol' in s else s for s in self.symbols]
        elif self.top_symbols_manager:
            # Get symbols from top symbols manager if available
            try:
                symbols = self.top_symbols_manager.get_current_symbols()
                if symbols:
                    return [s['symbol'] if isinstance(s, dict) and 'symbol' in s else s for s in symbols]
            except Exception as e:
                self.logger.error(f"Error getting symbols from top symbols manager: {str(e)}")
        
        # Fallback to a single symbol if set
        if self.symbol:
            return [self.symbol]
            
        # Last resort - return empty list
        return []
''')
            
            if '_is_report_time' in missing_methods:
                method_impls.append('''
    def _is_report_time(self) -> bool:
        """Check if current time is a scheduled report time.
        
        Returns:
            bool: True if it's time to generate a report
        """
        # If report_times is not defined, initialize it
        if not hasattr(self, 'report_times') or not self.report_times:
            self.report_times = self._calculate_report_times()
            
        # Check if current time matches any scheduled time (with 5 min tolerance)
        current_time = datetime.now(timezone.utc)
        for report_time in self.report_times:
            # Convert both to minutes of day for comparison
            current_minutes = current_time.hour * 60 + current_time.minute
            report_minutes = report_time.hour * 60 + report_time.minute
            
            # Check if we're within 5 minutes of a scheduled time
            if abs(current_minutes - report_minutes) <= 5:
                return True
                
        return False
''')
            
            if '_calculate_report_times' in missing_methods:
                method_impls.append('''
    def _calculate_report_times(self) -> List[datetime]:
        """Calculate scheduled report times based on configuration.
        
        Returns:
            List of datetime objects representing report times
        """
        # Default to 4 reports per day (00:00, 06:00, 12:00, 18:00 UTC)
        default_hours = [0, 6, 12, 18]
        
        # Get report schedule from config
        config_schedule = self.config.get('reporting', {}).get('schedule', {})
        report_hours = config_schedule.get('hours', default_hours)
        
        # Create datetime objects for each hour
        current_time = datetime.now(timezone.utc)
        report_times = []
        
        for hour in report_hours:
            report_time = current_time.replace(hour=hour, minute=0, second=0, microsecond=0)
            report_times.append(report_time)
            
        return report_times
''')
            
            # Insert the missing methods
            primary_class['text'] = prefix + ''.join(method_impls) + suffix
        else:
            print("Warning: Could not find appropriate insertion point for missing methods")
    
    # Remove duplicate class definitions and keep only the primary
    new_content = ''
    last_end = 0
    
    for cls in sorted(class_definitions, key=lambda x: x['start']):
        # Add text before this class
        new_content += content[last_end:cls['start']]
        
        # Add the class text only if it's the primary class
        if cls['index'] == primary_class['index']:
            new_content += primary_class['text']
        else:
            print(f"Removing duplicate class definition #{cls['index']}")
        
        last_end = cls['end']
    
    # Add remaining text after the last class
    new_content += content[last_end:]
    
    # Write the updated content back to the file
    with open(monitor_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"Successfully fixed duplicate MarketMonitor classes in {monitor_path}")
    return True

if __name__ == "__main__":
    try:
        success = fix_duplicate_marketmonitor()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 