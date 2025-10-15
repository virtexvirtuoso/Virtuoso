#!/usr/bin/env python3
"""
Fix syntax errors from asyncio task tracking conversion
"""

import os
import re
import glob

def fix_syntax_errors():
    """Fix syntax errors from automated task tracking conversion"""

    # Pattern to find the syntax errors
    patterns = [
        # Pattern: ...name="auto_tracked_task"))) - extra parentheses
        (r'name="auto_tracked_task"\)\)\)', 'name="auto_tracked_task")'),

        # Pattern: ...name="auto_tracked_task")) - one extra parenthesis
        (r'name="auto_tracked_task"\)\)', 'name="auto_tracked_task")'),

        # Pattern: ), name="...") - duplicate name parameters
        (r', name="auto_tracked_task"\), name="([^"]+)"\)', r', name="\1")'),
    ]

    files_fixed = []

    # Find all Python files
    for py_file in glob.glob('src/**/*.py', recursive=True):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # Apply all patterns
            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content)

            # If content changed, write back
            if content != original_content:
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                files_fixed.append(py_file)
                print(f"✅ Fixed syntax errors in: {py_file}")

        except Exception as e:
            print(f"❌ Error processing {py_file}: {e}")

    print(f"\n🎯 Summary: Fixed syntax errors in {len(files_fixed)} files")
    return files_fixed

if __name__ == "__main__":
    print("🔧 Fixing asyncio task tracking conversion syntax errors...")
    fixed_files = fix_syntax_errors()

    if fixed_files:
        print("\n📝 Files fixed:")
        for file in fixed_files:
            print(f"  - {file}")
    else:
        print("\n✅ No syntax errors found!")