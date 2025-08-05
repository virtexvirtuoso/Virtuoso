#!/usr/bin/env python3
"""Fix indentation issues in bybit.py"""

import re

# Read the file
with open('src/core/exchanges/bybit.py', 'r') as f:
    content = f.read()

# Fix the specific indentation issue
# The _get_auth_headers at line 768 should be indented 8 spaces (method inside class)
lines = content.split('\n')

# Find and fix the problematic line
for i, line in enumerate(lines):
    if i == 767 and line.strip().startswith('def _get_auth_headers'):
        # Check current indentation
        current_indent = len(line) - len(line.lstrip())
        print(f"Line {i+1}: Current indentation: {current_indent} spaces")
        
        # Fix to 8 spaces (method inside class)
        if current_indent != 8:
            lines[i] = '        ' + line.strip()
            print(f"Fixed indentation to 8 spaces")

# Write back
with open('src/core/exchanges/bybit.py', 'w') as f:
    f.write('\n'.join(lines))

print("Fixed indentation issues")