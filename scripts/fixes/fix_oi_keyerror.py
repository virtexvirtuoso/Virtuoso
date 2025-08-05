#!/usr/bin/env python3
"""Fix KeyError: 'current' in market_data_manager.py"""

import re
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def fix_oi_structure():
    """Fix the open interest data structure inconsistency."""
    
    file_path = PROJECT_ROOT / "src/core/market/market_data_manager.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Update _update_open_interest_history to handle both structures
    old_update_code = """            # Update current and previous values
            if oi_data['current'] != value:
                oi_data['previous'] = oi_data['current']
                oi_data['current'] = value
                oi_data['timestamp'] = timestamp"""
    
    new_update_code = """            # Update current and previous values
            # Handle both old and new structure formats
            current_value = oi_data.get('current', oi_data.get('value', 0.0))
            
            if current_value != value:
                # Ensure we have the correct structure
                if 'current' not in oi_data:
                    # Convert from sentiment structure to history structure
                    oi_data['current'] = oi_data.get('value', 0.0)
                    oi_data['previous'] = oi_data.get('current', 0.0)
                    if 'history' not in oi_data:
                        oi_data['history'] = []
                
                oi_data['previous'] = oi_data['current']
                oi_data['current'] = value
                oi_data['timestamp'] = timestamp"""
    
    content = content.replace(old_update_code, new_update_code)
    
    # Fix 2: Ensure consistent structure when setting open_interest
    # Find the problematic line where sentiment_oi is assigned
    old_assignment = """                            self.data_cache[symbol]['open_interest'] = sentiment_oi"""
    
    new_assignment = """                            # Merge sentiment OI with existing structure
                            if 'open_interest' not in self.data_cache[symbol]:
                                self.data_cache[symbol]['open_interest'] = {
                                    'current': 0.0,
                                    'previous': 0.0,
                                    'timestamp': 0,
                                    'history': []
                                }
                            
                            # Update with sentiment values while preserving structure
                            oi_data = self.data_cache[symbol]['open_interest']
                            oi_data['previous'] = oi_data.get('current', 0.0)
                            oi_data['current'] = float(current_oi)
                            oi_data['timestamp'] = sentiment_oi['timestamp']
                            oi_data['value'] = sentiment_oi['value']  # Keep for compatibility
                            oi_data['change_24h'] = sentiment_oi['change_24h']"""
    
    content = content.replace(old_assignment, new_assignment)
    
    # Write the fixed content
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✓ Fixed open interest KeyError issue")
    print("  - Updated _update_open_interest_history to handle both structures")
    print("  - Fixed sentiment OI assignment to preserve required structure")

def add_defensive_checks():
    """Add defensive checks to prevent future KeyErrors."""
    
    file_path = PROJECT_ROOT / "src/core/market/market_data_manager.py"
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Find the _update_open_interest_history method
    for i, line in enumerate(lines):
        if "def _update_open_interest_history" in line:
            # Add a defensive check at the beginning of the method
            indent = " " * 8  # 2 levels of indentation
            
            # Find where to insert (after the try: line)
            for j in range(i, min(i + 20, len(lines))):
                if "try:" in lines[j]:
                    # Insert validation after try:
                    insert_pos = j + 1
                    validation_code = f"""{indent}# Validate inputs
{indent}if not isinstance(value, (int, float)):
{indent}    self.logger.warning(f"Invalid OI value type for {{symbol}}: {{type(value)}}")
{indent}    return
{indent}
{indent}if value < 0:
{indent}    self.logger.warning(f"Negative OI value for {{symbol}}: {{value}}")
{indent}    return
{indent}
"""
                    lines.insert(insert_pos, validation_code)
                    break
            break
    
    with open(file_path, 'w') as f:
        f.writelines(lines)
    
    print("✓ Added defensive validation checks")

def main():
    """Apply all fixes."""
    print("Fixing open interest KeyError issue...")
    
    # Create backup
    import shutil
    file_path = PROJECT_ROOT / "src/core/market/market_data_manager.py"
    backup_path = file_path.with_suffix('.py.backup_oi_keyerror')
    shutil.copy2(file_path, backup_path)
    print(f"Created backup: {backup_path}")
    
    # Apply fixes
    fix_oi_structure()
    add_defensive_checks()
    
    print("\n✅ All fixes applied successfully!")

if __name__ == "__main__":
    main()