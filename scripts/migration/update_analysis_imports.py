#!/usr/bin/env python3
"""
Update Analysis Imports Migration Script

This script updates all analysis imports to use the new consolidated package structure.
"""

import os
import re
import sys
from typing import List, Dict, Tuple

def get_python_files(directory: str) -> List[str]:
    """Get all Python files in directory and subdirectories."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip certain directories
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', 'venv', 'env', 'backups'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def update_imports_in_file(file_path: str) -> Tuple[int, List[str]]:
    """Update analysis imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        # Import mappings for the new consolidated structure
        import_mappings = {
            # Core analysis imports  
            'from src.analysis.core.confluence import': 'from src.analysis.core.confluence import',
            'from src.analysis.core.alpha_scanner import': 'from src.analysis.core.alpha_scanner import',
            'from src.analysis.core.liquidation_detector import': 'from src.analysis.core.liquidation_detector import',
            'from src.analysis.core.portfolio import': 'from src.analysis.core.portfolio import',
            'from src.analysis.core.position_calculator import': 'from src.analysis.core.position_calculator import',
            'from src.analysis.data.validator import': 'from src.analysis.data.validator import',
            'from src.analysis.core.integrated_analysis import': 'from src.analysis.core.integrated_analysis import',
            'from src.analysis.core.interpretation_generator import': 'from src.analysis.core.interpretation_generator import',
            
            # Market analysis imports
            'from src.analysis.market.market_analyzer import': 'from src.analysis.market.market_analyzer import',
            'from src.analysis.market.session_analyzer import': 'from src.analysis.market.session_analyzer import',
            'from src.analysis.data.dataframe_utils import': 'from src.analysis.data.dataframe_utils import',
            
            # Import statements with module references
            'import src.analysis.core.confluence': 'import src.analysis.core.confluence',
            'import src.analysis.core.alpha_scanner': 'import src.analysis.core.alpha_scanner',
            'import src.analysis.core.liquidation_detector': 'import src.analysis.core.liquidation_detector',
            'import src.analysis.core.portfolio': 'import src.analysis.core.portfolio',
            'import src.analysis.data.validator': 'import src.analysis.data.validator',
            'import src.analysis.market.market_analyzer': 'import src.analysis.market.market_analyzer',
            'import src.analysis.market.session_analyzer': 'import src.analysis.market.session_analyzer',
            'import src.analysis.data.dataframe_utils': 'import src.analysis.data.dataframe_utils',
        }
        
        # Apply import mappings
        for old_import, new_import in import_mappings.items():
            if old_import in content:
                content = content.replace(old_import, new_import)
                changes.append(f"Updated: {old_import} → {new_import}")
        
        # Handle string references that might be used in configuration or dynamic imports
        string_mappings = {
            'src.analysis.core.confluence': 'src.analysis.core.confluence',
            'src.analysis.core.alpha_scanner': 'src.analysis.core.alpha_scanner', 
            'src.analysis.core.liquidation_detector': 'src.analysis.core.liquidation_detector',
            'src.analysis.core.portfolio': 'src.analysis.core.portfolio',
            'src.analysis.data.validator': 'src.analysis.data.validator',
            'src.analysis.market.market_analyzer': 'src.analysis.market.market_analyzer',
            'src.analysis.market.session_analyzer': 'src.analysis.market.session_analyzer',
            'src.analysis.data.dataframe_utils': 'src.analysis.data.dataframe_utils',
        }
        
        # Apply string mappings with caution (only in quotes)
        for old_ref, new_ref in string_mappings.items():
            # Match quoted strings
            patterns = [
                f'"{old_ref}"',
                f"'{old_ref}'"
            ]
            for pattern in patterns:
                if pattern in content:
                    new_pattern = pattern.replace(old_ref, new_ref)
                    content = content.replace(pattern, new_pattern)
                    changes.append(f"Updated string reference: {pattern} → {new_pattern}")
        
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
    print("=== Analysis Package Import Migration ===")
    print("Updating imports to use consolidated analysis package...")
    
    # Get all Python files in src directory
    src_files = get_python_files('src')
    
    # Also check scripts and tests if they exist
    all_files = src_files.copy()
    if os.path.exists('scripts'):
        all_files.extend(get_python_files('scripts'))
    if os.path.exists('tests'):
        all_files.extend(get_python_files('tests'))
    
    print(f"Found {len(all_files)} Python files to check")
    
    total_changes = 0
    files_updated = 0
    detailed_changes = []
    
    for file_path in all_files:
        changes_count, changes = update_imports_in_file(file_path)
        if changes_count > 0:
            files_updated += 1
            total_changes += changes_count
            detailed_changes.append((file_path, changes))
            print(f"✓ Updated {file_path} ({changes_count} changes)")
    
    print(f"\n=== Migration Complete ===")
    print(f"Files updated: {files_updated}")
    print(f"Total changes: {total_changes}")
    
    if detailed_changes:
        print(f"\n=== Detailed Changes ===")
        for file_path, changes in detailed_changes:
            print(f"\n{file_path}:")
            for change in changes:
                print(f"  - {change}")

if __name__ == "__main__":
    main()