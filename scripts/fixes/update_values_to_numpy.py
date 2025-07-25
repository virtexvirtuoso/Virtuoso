#!/usr/bin/env python3
"""
Update .values usage to .to_numpy() for better pandas compatibility.
"""

import os
import re

def update_values_to_numpy(file_path):
    """Update .values to .to_numpy() in a file."""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to match .values at end of line or followed by non-dot
    pattern = r'\.values(?![.])'
    replacement = '.to_numpy()'
    
    # Count replacements
    count = len(re.findall(pattern, content))
    
    if count > 0:
        # Make replacements
        updated_content = re.sub(pattern, replacement, content)
        
        # Write back
        with open(file_path, 'w') as f:
            f.write(updated_content)
        
        print(f"Updated {file_path}: {count} replacements")
        return count
    
    return 0

def main():
    """Update specific files mentioned in the review."""
    
    files_to_update = [
        'src/indicators/base_indicator.py',
    ]
    
    total_updates = 0
    
    for file_path in files_to_update:
        if os.path.exists(file_path):
            count = update_values_to_numpy(file_path)
            total_updates += count
        else:
            print(f"File not found: {file_path}")
    
    print(f"\nTotal replacements: {total_updates}")

if __name__ == "__main__":
    main()