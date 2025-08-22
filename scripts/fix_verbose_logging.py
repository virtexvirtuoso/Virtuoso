#!/usr/bin/env python3
"""
Fix verbose config dumps in logs by:
1. Commenting out or reducing config debug logs
2. Changing log levels for config-related messages
"""

import os
import re

def fix_file(filepath, changes_made):
    """Fix verbose logging in a single file"""
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern 1: Comment out full config dumps
    patterns = [
        # base_indicator.py - full config dump
        (r'(\s+)self\.logger\.debug\(f"Config: \{config\}"\)',
         r'\1# self.logger.debug(f"Config: {config}")  # Disabled verbose config dump'),
        
        # signal_generator.py - full config dump
        (r'(\s+)self\.logger\.debug\(f"Initializing SignalGenerator with config: \{config\}"\)',
         r'\1self.logger.debug("Initializing SignalGenerator")  # Removed verbose config dump'),
        
        # top_symbols.py - config in error context  
        (r'logger\.debug\(f"Error context - Market data count: \{len\(market_data\)\}, Config: \{config\}"\)',
         r'logger.debug(f"Error context - Market data count: {len(market_data)}")  # Removed config dump'),
         
        # Any other debug logs with full config objects
        (r'logger\.debug\(.*[Cc]onfig:\s*\{[^}]+\}.*\)',
         r'# \g<0>  # Disabled verbose config dump'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # Pattern 2: Replace DEBUG with INFO for initialization messages that dump configs
    content = re.sub(
        r'logger\.debug\(.*[Ii]nitializing.*config.*\)',
        lambda m: m.group(0).replace('logger.debug', 'logger.info').replace('config: {config}', 'config: <truncated>'),
        content
    )
    
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        changes_made.append(filepath)
        return True
    return False

def main():
    """Main function to fix verbose logging"""
    
    print("Fixing verbose config dumps in logs...")
    
    # Files to fix
    files_to_fix = [
        'src/indicators/base_indicator.py',
        'src/signal_generation/signal_generator.py',
        'src/core/market/top_symbols.py',
    ]
    
    # Also search for other files with verbose config logging
    print("Searching for additional files with config dumps...")
    import subprocess
    result = subprocess.run(
        ['grep', '-r', '-l', 'logger.*[Cc]onfig.*{', 'src/', '--include=*.py'],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        additional_files = result.stdout.strip().split('\n')
        for f in additional_files:
            if f and f not in files_to_fix:
                files_to_fix.append(f)
    
    changes_made = []
    
    for filepath in files_to_fix:
        if os.path.exists(filepath):
            print(f"Checking {filepath}...")
            if fix_file(filepath, changes_made):
                print(f"  ✓ Fixed verbose logging in {filepath}")
        else:
            print(f"  ⚠️ File not found: {filepath}")
    
    if changes_made:
        print(f"\n✅ Fixed verbose logging in {len(changes_made)} files:")
        for f in changes_made:
            print(f"  - {f}")
    else:
        print("\n✅ No verbose config dumps found to fix")
    
    return 0

if __name__ == "__main__":
    exit(main())