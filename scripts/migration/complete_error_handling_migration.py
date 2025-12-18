#!/usr/bin/env python3
"""
Complete the migration of error_handling from src.utils to src.core.error
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
        
        # Update error_handling imports
        # Map old imports to new ones
        replacements = [
            # Basic error_handling import
            (r'from src\.utils\.error_handling import', 'from src.core.error.utils import'),
            
            # Handle specific ValidationError import - it moved to unified_exceptions
            (r'from src\.core\.error\.utils import ([^,\n]*,\s*)?ValidationError',
             r'from src.core.error.unified_exceptions import ValidationError\nfrom src.core.error.utils import \1'),
        ]
        
        for old_pattern, new_pattern in replacements:
            content = re.sub(old_pattern, new_pattern, content)
        
        # Clean up any double imports or trailing commas
        content = re.sub(r'from src\.core\.error\.utils import \s*\n', '', content)
        content = re.sub(r'from src\.core\.error\.utils import ,', 'from src.core.error.utils import', content)
        content = re.sub(r',\s*,', ',', content)
        content = re.sub(r',\s*\)', ')', content)
        
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
        'src/indicators/volume_indicators.py',
        'src/indicators/technical_indicators.py',
        'src/indicators/sentiment_indicators.py',
        'src/indicators/price_structure_indicators.py',
        'src/indicators/orderflow_indicators.py',
        'src/indicators/orderbook_indicators.py',
        'src/core/market/data_manager.py',
        'src/analysis/session_analyzer.py',
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
    
    # Now let's check what functions are being imported
    print("\nChecking what's imported from error_handling...")
    for file_path in files_to_update:
        full_path = project_root / file_path
        if full_path.exists():
            with open(full_path, 'r') as f:
                content = f.read()
            
            # Find imports from error utils
            imports = re.findall(r'from src\.core\.error\.utils import ([^\n]+)', content)
            if imports:
                print(f"\n{file_path}:")
                for imp in imports:
                    print(f"  - {imp.strip()}")

if __name__ == "__main__":
    main()