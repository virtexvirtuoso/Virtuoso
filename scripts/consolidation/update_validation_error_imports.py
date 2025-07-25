#!/usr/bin/env python3
"""Update all ValidationError imports to use the canonical version."""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict

# Define the import mappings
IMPORT_MAPPINGS = [
    # ValidationError imports from various locations
    (
        r'from src\.utils\.error_handling import ValidationError',
        'from src.core.error.unified_exceptions import ValidationError'
    ),
    (
        r'from src\.utils\.validation_types import ValidationError',
        'from src.core.error.unified_exceptions import ValidationError'
    ),
    (
        r'from \.\.utils\.error_handling import ValidationError',
        'from src.core.error.unified_exceptions import ValidationError'
    ),
    (
        r'from \.\.utils\.validation_types import ValidationError',
        'from src.core.error.unified_exceptions import ValidationError'
    ),
]

# Files that need special handling (they define their own ValidationError)
SPECIAL_FILES = {
    'src/indicators/base_indicator.py': {
        'line': 2045,
        'action': 'delete_class'
    },
    'src/core/validation/models.py': {
        'action': 'rename_class',
        'old_name': 'ValidationError',
        'new_name': 'ValidationErrorData'
    },
    'src/core/config/validators/binance_validator.py': {
        'action': 'rename_class',
        'old_name': 'ValidationError',
        'new_name': 'BinanceValidationError'
    }
}

def update_imports_in_file(file_path: Path, dry_run: bool = False) -> List[str]:
    """Update imports in a single file."""
    changes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return changes
    
    original_content = content
    
    # Apply import mappings
    for old_pattern, new_import in IMPORT_MAPPINGS:
        if re.search(old_pattern, content):
            content = re.sub(old_pattern, new_import, content)
            changes.append(f"Updated import: {old_pattern} -> {new_import}")
    
    # Handle special files
    relative_path = str(file_path.relative_to(Path(__file__).parent.parent.parent))
    if relative_path in SPECIAL_FILES:
        special = SPECIAL_FILES[relative_path]
        
        if special['action'] == 'delete_class':
            # Remove the ValidationError class definition
            pattern = r'class ValidationError\(Exception\):[^}]+?(?=\n(?:class|def|\Z))'
            if re.search(pattern, content, re.DOTALL):
                content = re.sub(pattern, '', content, flags=re.DOTALL)
                changes.append("Deleted local ValidationError class definition")
                
        elif special['action'] == 'rename_class':
            # Rename the class
            old_name = special['old_name']
            new_name = special['new_name']
            
            # Update class definition
            pattern = f'class {old_name}'
            if re.search(pattern, content):
                content = re.sub(pattern, f'class {new_name}', content)
                changes.append(f"Renamed class: {old_name} -> {new_name}")
            
            # Update all references to the class
            # This is more complex and might need manual review
            content = re.sub(f'\\b{old_name}\\b', new_name, content)
            changes.append(f"Updated all references: {old_name} -> {new_name}")
    
    # Only write if changes were made
    if content != original_content:
        if not dry_run:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ Updated {file_path}")
            except Exception as e:
                print(f"❌ Error writing {file_path}: {e}")
        else:
            print(f"Would update {file_path}")
        
        return changes
    
    return []

def find_python_files(root_dir: Path, exclude_dirs: List[str] = None) -> List[Path]:
    """Find all Python files in the project."""
    if exclude_dirs is None:
        exclude_dirs = ['venv', 'venv311', '__pycache__', '.git', 'backups', '.pytest_cache']
    
    python_files = []
    
    for path in root_dir.rglob('*.py'):
        # Skip excluded directories
        if any(excluded in path.parts for excluded in exclude_dirs):
            continue
        
        python_files.append(path)
    
    return python_files

def check_pydantic_imports(file_path: Path) -> bool:
    """Check if file imports ValidationError from pydantic."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for pydantic ValidationError import
        if re.search(r'from pydantic import.*ValidationError', content):
            return True
        if re.search(r'from pydantic\..*import.*ValidationError', content):
            return True
            
    except Exception:
        pass
    
    return False

def main():
    """Main function to update all imports."""
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    
    print("🔍 Finding Python files...")
    python_files = find_python_files(project_root)
    print(f"Found {len(python_files)} Python files")
    
    # First, check for pydantic imports
    print("\n🔍 Checking for pydantic ValidationError imports...")
    pydantic_files = []
    for file_path in python_files:
        if check_pydantic_imports(file_path):
            pydantic_files.append(file_path)
    
    if pydantic_files:
        print(f"\n⚠️  Found {len(pydantic_files)} files importing ValidationError from pydantic:")
        for file_path in pydantic_files:
            print(f"  - {file_path.relative_to(project_root)}")
        print("These files will keep their pydantic imports.")
    
    # Now do a dry run for other changes
    print("\n🔍 Analyzing files for ValidationError updates (dry run)...")
    total_changes = 0
    files_to_update = []
    
    for file_path in python_files:
        # Skip files that import from pydantic
        if file_path in pydantic_files:
            continue
            
        changes = update_imports_in_file(file_path, dry_run=True)
        if changes:
            files_to_update.append((file_path, changes))
            total_changes += len(changes)
    
    if not files_to_update:
        print("✅ No files need updating!")
        return
    
    print(f"\n📊 Found {total_changes} changes to make in {len(files_to_update)} files")
    
    # Show what will be changed
    print("\nFiles that will be updated:")
    for file_path, changes in files_to_update[:10]:  # Show first 10
        print(f"  {file_path.relative_to(project_root)}")
        for change in changes:
            print(f"    - {change}")
    
    if len(files_to_update) > 10:
        print(f"  ... and {len(files_to_update) - 10} more files")
    
    # Apply the changes
    print("\n🔧 Applying changes...")
    for file_path, _ in files_to_update:
        update_imports_in_file(file_path, dry_run=False)
    
    print(f"\n✅ Successfully updated {len(files_to_update)} files!")
    
    # List files that can be deleted
    print("\n🗑️  Files that can be deleted:")
    files_to_delete = [
        project_root / 'src' / 'utils' / 'validation_types.py',
        # Don't delete error_handling.py as it has other classes
    ]
    
    for file_path in files_to_delete:
        if file_path.exists():
            print(f"  - {file_path.relative_to(project_root)}")
    
    print("\n⚠️  Note: src/utils/error_handling.py contains other classes and should be manually reviewed")

if __name__ == "__main__":
    main()