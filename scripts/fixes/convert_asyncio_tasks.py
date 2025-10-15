#!/usr/bin/env python3
"""Script to convert asyncio.create_task() calls to use the tracked task system."""

import os
import re
import subprocess
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent

def find_asyncio_create_task_files():
    """Find all Python files with asyncio.create_task calls."""
    result = subprocess.run([
        'grep', '-r', '--include=*.py', '-l', 'asyncio\.create_task', str(PROJECT_ROOT)
    ], capture_output=True, text=True, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        files = result.stdout.strip().split('\n')
        # Filter out test files, validation files, and this script
        filtered_files = []
        for file in files:
            if (not any(exclude in file for exclude in ['test_', 'validate_', 'fix_', 'convert_asyncio'])
                and not file.endswith('convert_asyncio_tasks.py')
                and 'src/' in file):
                filtered_files.append(file)
        return filtered_files
    return []

def add_import_if_needed(file_path):
    """Add the import for create_tracked_task if not present."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Check if import already exists
    if 'from src.utils.task_tracker import' in content or 'create_tracked_task' in content:
        return content

    # Find the best place to add the import (after other imports)
    lines = content.split('\n')
    import_line_index = 0

    for i, line in enumerate(lines):
        if line.strip().startswith('import ') or line.strip().startswith('from '):
            import_line_index = i + 1
        elif line.strip() and not line.strip().startswith('#'):
            break

    # Insert the import
    import_statement = "from src.utils.task_tracker import create_tracked_task"
    lines.insert(import_line_index, import_statement)

    return '\n'.join(lines)

def convert_asyncio_tasks(content):
    """Convert asyncio.create_task calls to create_tracked_task."""
    # Pattern to match asyncio.create_task() calls
    patterns = [
        # Standard case: asyncio.create_task(coroutine)
        (r'asyncio\.create_task\(([^)]+)\)', r'create_tracked_task(\1, name="auto_tracked_task")'),

        # Case with name parameter: asyncio.create_task(coroutine, name="name")
        (r'asyncio\.create_task\(([^,]+),\s*name=([^)]+)\)', r'create_tracked_task(\1, name=\2)'),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    return content

def process_file(file_path):
    """Process a single file to convert asyncio.create_task calls."""
    print(f"Processing {file_path}...")

    try:
        with open(file_path, 'r') as f:
            original_content = f.read()

        # Add import if needed
        content = add_import_if_needed(file_path)

        # Convert asyncio.create_task calls
        content = convert_asyncio_tasks(content)

        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"  ✅ Updated {file_path}")
            return True
        else:
            print(f"  ⏭️ No changes needed for {file_path}")
            return False

    except Exception as e:
        print(f"  ❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main conversion process."""
    print("🔍 Finding files with asyncio.create_task calls...")
    files = find_asyncio_create_task_files()

    if not files:
        print("No files found with asyncio.create_task calls.")
        return

    print(f"Found {len(files)} files to process:")
    for file in files:
        print(f"  - {file}")

    print("\n🔄 Converting asyncio.create_task calls...")
    converted_count = 0

    for file_path in files:
        if process_file(file_path):
            converted_count += 1

    print(f"\n✅ Conversion complete!")
    print(f"   Processed: {len(files)} files")
    print(f"   Updated: {converted_count} files")
    print(f"   No changes: {len(files) - converted_count} files")

if __name__ == "__main__":
    main()