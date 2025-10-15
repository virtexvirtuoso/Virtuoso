#!/usr/bin/env python3
"""
Fix syntax errors in create_tracked_task calls
"""
import os
import re
import subprocess

def find_files_with_syntax_errors():
    """Find all Python files with syntax errors"""
    files_with_errors = []

    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    result = subprocess.run(['python', '-m', 'py_compile', filepath],
                                          capture_output=True, text=True)
                    if result.returncode != 0 and 'SyntaxError' in result.stderr:
                        files_with_errors.append(filepath)
                except Exception as e:
                    print(f"Error checking {filepath}: {e}")

    return files_with_errors

def fix_create_tracked_task_syntax(filepath):
    """Fix syntax errors in create_tracked_task calls"""
    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content

    # Pattern 1: Fix missing closing parenthesis in create_tracked_task calls
    # e.g., create_tracked_task(self.func(arg, name="auto_tracked_task") -> create_tracked_task(self.func(arg), name="task_name")
    pattern1 = r'create_tracked_task\(([^()]+)\([^)]*,\s*name="auto_tracked_task"\)([^)]*)'

    def replace_func(match):
        func_call = match.group(1)
        remaining = match.group(2)
        # Extract function name for task naming
        func_name = func_call.split('.')[-1] if '.' in func_call else func_call
        return f'create_tracked_task({func_call.rstrip(", ")}, name="{func_name}_task"){remaining}'

    content = re.sub(pattern1, replace_func, content)

    # Pattern 2: Fix missing closing parenthesis at end of line
    # e.g., create_tracked_task(func(args, name="auto_tracked_task") without closing )
    pattern2 = r'create_tracked_task\(([^()]+),\s*name="auto_tracked_task"\)(?!\s*,)'
    content = re.sub(pattern2, r'create_tracked_task(\1, name="auto_tracked_task")', content)

    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Fixed syntax errors in {filepath}")
        return True
    return False

def main():
    print("Finding files with syntax errors...")
    error_files = find_files_with_syntax_errors()

    print(f"Found {len(error_files)} files with syntax errors:")
    for file in error_files:
        print(f"  {file}")

    print("\nAttempting to fix syntax errors...")
    fixed_count = 0
    for filepath in error_files:
        if fix_create_tracked_task_syntax(filepath):
            fixed_count += 1

    print(f"\nFixed {fixed_count} files")

    # Re-check for remaining errors
    print("\nRe-checking for remaining syntax errors...")
    remaining_errors = find_files_with_syntax_errors()

    if remaining_errors:
        print(f"Still {len(remaining_errors)} files with syntax errors:")
        for file in remaining_errors:
            print(f"  {file}")
            # Show the specific error
            try:
                result = subprocess.run(['python', '-m', 'py_compile', file],
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"    Error: {result.stderr.strip()}")
            except:
                pass
    else:
        print("All syntax errors fixed!")

if __name__ == "__main__":
    main()