#!/usr/bin/env python3
"""
Update Indicator Logging Imports Script

This script updates all imports from src.analysis.utils.indicator_utils
to src.utils.logging.indicator_logging to break circular dependencies.
"""

import os
import re
from typing import List, Tuple

def get_python_files(directory: str) -> List[str]:
    """Get all Python files in directory and subdirectories."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip backups and certain directories
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'backups'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def update_indicator_imports_in_file(file_path: str) -> Tuple[int, List[str]]:
    """Update indicator logging imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        # Import mappings for indicator logging utilities
        import_mappings = {
            'from src.analysis.utils.indicator_utils import': 'from src.utils.logging.indicator_logging import',
            'from src.analysis.utils.indicator_utils': 'from src.utils.logging.indicator_logging',
        }
        
        # Apply import mappings
        for old_import, new_import in import_mappings.items():
            if old_import in content:
                content = content.replace(old_import, new_import)
                changes.append(f"Updated: {old_import} → {new_import}")
        
        # Handle any remaining references to the module
        module_references = {
            'src.analysis.utils.indicator_utils': 'src.utils.logging.indicator_logging',
            'analysis.utils.indicator_utils': 'utils.logging.indicator_logging',
        }
        
        for old_ref, new_ref in module_references.items():
            if old_ref in content:
                content = content.replace(old_ref, new_ref)
                changes.append(f"Module reference: {old_ref} → {new_ref}")
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return len(changes), changes
        else:
            return 0, []
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0, []

def main():
    """Main migration function."""
    print("=== Indicator Logging Import Migration ===")
    print("Moving imports from analysis/utils to utils/logging...")
    
    # Get all Python files in src
    python_files = get_python_files('src')
    
    print(f"Found {len(python_files)} Python files to check")
    
    total_changes = 0
    files_updated = 0
    detailed_changes = []
    
    for file_path in python_files:
        changes_count, changes = update_indicator_imports_in_file(file_path)
        if changes_count > 0:
            files_updated += 1
            total_changes += changes_count
            detailed_changes.append((file_path, changes))
            print(f"✓ Updated {file_path} ({changes_count} changes)")
    
    print(f"\\n=== Migration Complete ===")
    print(f"Files updated: {files_updated}")
    print(f"Total changes: {total_changes}")
    
    if detailed_changes:
        print(f"\\n=== Detailed Changes ===")
        for file_path, changes in detailed_changes:
            print(f"\\n{file_path}:")
            for change in changes:
                print(f"  - {change}")

if __name__ == "__main__":
    main()