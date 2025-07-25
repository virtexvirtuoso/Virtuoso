#!/usr/bin/env python3
"""Update all SimpleErrorHandler imports to use the canonical version."""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Define the import mappings
IMPORT_MAPPINGS = [
    # SimpleErrorHandler imports
    (
        r'from src\.data_processing\.error_handler import SimpleErrorHandler',
        'from src.core.error.handlers import SimpleErrorHandler'
    ),
    (
        r'from src\.data_acquisition\.error_handler import SimpleErrorHandler',
        'from src.core.error.handlers import SimpleErrorHandler'
    ),
    (
        r'from \.error_handler import SimpleErrorHandler',  # Relative imports
        'from src.core.error.handlers import SimpleErrorHandler'
    ),
    (
        r'from \.\.error_handler import SimpleErrorHandler',  # Parent relative
        'from src.core.error.handlers import SimpleErrorHandler'
    ),
    # Also update ErrorHandler imports to use SimpleErrorHandler
    (
        r'from src\.core\.error\.handlers import ErrorHandler',
        'from src.core.error.handlers import SimpleErrorHandler as ErrorHandler'
    ),
]

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
    
    # Apply each mapping
    for old_pattern, new_import in IMPORT_MAPPINGS:
        if re.search(old_pattern, content):
            content = re.sub(old_pattern, new_import, content)
            changes.append(f"Updated: {old_pattern} -> {new_import}")
    
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

def main():
    """Main function to update all imports."""
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    
    print("🔍 Finding Python files...")
    python_files = find_python_files(project_root)
    print(f"Found {len(python_files)} Python files")
    
    # First, do a dry run to see what would change
    print("\n🔍 Analyzing files (dry run)...")
    total_changes = 0
    files_to_update = []
    
    for file_path in python_files:
        changes = update_imports_in_file(file_path, dry_run=True)
        if changes:
            files_to_update.append((file_path, changes))
            total_changes += len(changes)
    
    if not files_to_update:
        print("✅ No files need updating!")
        return
    
    print(f"\n📊 Found {total_changes} imports to update in {len(files_to_update)} files")
    
    # Show what will be changed
    print("\nFiles that will be updated:")
    for file_path, changes in files_to_update[:10]:  # Show first 10
        print(f"  {file_path.relative_to(project_root)}")
        for change in changes:
            print(f"    - {change}")
    
    if len(files_to_update) > 10:
        print(f"  ... and {len(files_to_update) - 10} more files")
    
    # Automatically apply changes (remove for interactive mode)
    print("\n🔧 Automatically applying changes...")
    
    # Apply the changes
    print("\n🔧 Applying changes...")
    for file_path, _ in files_to_update:
        update_imports_in_file(file_path, dry_run=False)
    
    print(f"\n✅ Successfully updated {len(files_to_update)} files!")
    
    # Now check for files to delete
    print("\n🗑️  Files that can be deleted:")
    files_to_delete = [
        project_root / 'src' / 'data_processing' / 'error_handler.py',
        project_root / 'src' / 'data_acquisition' / 'error_handler.py',
    ]
    
    for file_path in files_to_delete:
        if file_path.exists():
            print(f"  - {file_path.relative_to(project_root)}")
    
    print("\n⚠️  Please manually delete these files after verifying everything works!")

if __name__ == "__main__":
    main()