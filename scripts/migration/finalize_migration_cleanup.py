#!/usr/bin/env python3
"""
Finalize the migration by removing old duplicate modules and updating __init__.py files
"""

import os
import re
from pathlib import Path

def update_utils_init(project_root: Path):
    """Update src/utils/__init__.py to remove migrated imports."""
    init_file = project_root / 'src' / 'utils' / '__init__.py'
    
    try:
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove the liquidation_cache import line
        content = re.sub(r'^from \.liquidation_cache import.*$\n', '', content, flags=re.MULTILINE)
        
        if content != original_content:
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Updated: src/utils/__init__.py")
            return True
    except Exception as e:
        print(f"Error updating utils init: {e}")
    return False

def rename_old_modules(project_root: Path):
    """Rename old modules to .old to preserve them but prevent imports."""
    modules_to_rename = [
        'src/utils/error_handling.py',
        'src/utils/validation.py', 
        'src/utils/liquidation_cache.py',
    ]
    
    renamed_count = 0
    for module_path in modules_to_rename:
        full_path = project_root / module_path
        if full_path.exists():
            new_path = full_path.with_suffix('.py.old')
            try:
                full_path.rename(new_path)
                print(f"✓ Renamed: {module_path} -> {module_path}.old")
                renamed_count += 1
            except Exception as e:
                print(f"✗ Error renaming {module_path}: {e}")
        else:
            print(f"✗ Not found: {module_path}")
    
    return renamed_count

def main():
    """Main cleanup function."""
    project_root = Path('/Users/ffv_macmini/Desktop/Virtuoso_ccxt')
    
    print("=== Finalizing Migration Cleanup ===\n")
    
    # Step 1: Update utils __init__.py
    print("Step 1: Updating utils __init__.py...")
    update_utils_init(project_root)
    
    # Step 2: Rename old modules
    print("\nStep 2: Renaming old modules to .old...")
    renamed_count = rename_old_modules(project_root)
    
    print(f"\n=== Migration Complete ===")
    print(f"Total modules renamed: {renamed_count}")
    
    # Summary of new locations
    print("\n=== New Module Locations ===")
    print("error_handling -> src.core.error.utils")
    print("validation.DataValidator -> src.validation.data.analysis_validator.DataValidator")
    print("liquidation_cache -> src.core.cache.liquidation_cache")

if __name__ == "__main__":
    main()