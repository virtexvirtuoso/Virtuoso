#!/usr/bin/env python3
"""
Script to update the MarketMonitor._process_analysis_result method
to use the enhanced formatter.
"""

import os
import re
import fileinput
import sys
import shutil

def update_formatter_call(file_path):
    """
    Update the call to LogFormatter.format_confluence_score_table
    to LogFormatter.format_enhanced_confluence_score_table in the
    _process_analysis_result method.
    """
    # Create a backup of the original file
    backup_path = file_path + '.bak'
    shutil.copy2(file_path, backup_path)
    print(f"Created backup of original file at {backup_path}")
    
    # Read the file content
    with open(file_path, 'r') as file:
        content = file.read()
    
    # Replace the method call
    pattern = r'formatted_table = LogFormatter\.format_confluence_score_table\('
    replacement = 'formatted_table = LogFormatter.format_enhanced_confluence_score_table('
    
    new_content = re.sub(pattern, replacement, content)
    
    # Check if any changes were made
    if content == new_content:
        print("No changes were made to the file. The pattern was not found.")
        return False
    
    # Write the updated content
    with open(file_path, 'w') as file:
        file.write(new_content)
    
    print(f"Successfully updated {file_path} to use format_enhanced_confluence_score_table")
    return True

def manually_edit_instructions():
    """Provide instructions for manually editing the file if the script fails."""
    print("\nIf the automatic update failed, you can manually edit the file:")
    print("1. Open src/monitoring/monitor.py in your text editor")
    print("2. Find the line: formatted_table = LogFormatter.format_confluence_score_table(")
    print("3. Change it to: formatted_table = LogFormatter.format_enhanced_confluence_score_table(")
    print("4. Save the file\n")

if __name__ == "__main__":
    monitor_file = 'src/monitoring/monitor.py'
    
    if not os.path.exists(monitor_file):
        print(f"Error: File {monitor_file} not found")
        sys.exit(1)
    
    success = update_formatter_call(monitor_file)
    
    if not success:
        manually_edit_instructions()
    else:
        print("\nMonitor.py has been updated successfully to use the enhanced formatter.")
        print("You can now run your application and see the enhanced market interpretations.")
        print("To revert the changes if needed, use the backup file created at src/monitoring/monitor.py.bak\n") 