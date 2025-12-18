#!/usr/bin/env python3
"""
Complete the migration of validation from src.utils to src.validation
"""

import os
import re
from pathlib import Path

def update_imports_in_file(file_path: Path) -> bool:
    """Update imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Update validation imports
        # DataValidator is in src.validation.data.analysis_validator
        replacements = [
            (r'from src\.utils\.validation import DataValidator',
             'from src.validation.data.analysis_validator import DataValidator'),
        ]
        
        for old_pattern, new_pattern in replacements:
            content = re.sub(old_pattern, new_pattern, content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main migration function."""
    # Define the files to update
    files_to_update = [
        'src/analysis/session_analyzer.py',
        'src/indicators/technical_indicators.py',
    ]
    
    # Use relative path from script location
    project_root = Path(__file__).parent.parent.parent
    
    updated_files = []
    for file_path in files_to_update:
        full_path = project_root / file_path
        if full_path.exists():
            if update_imports_in_file(full_path):
                updated_files.append(file_path)
                print(f"✓ Updated: {file_path}")
        else:
            print(f"✗ Not found: {file_path}")
    
    print(f"\nTotal files updated: {len(updated_files)}")

if __name__ == "__main__":
    main()