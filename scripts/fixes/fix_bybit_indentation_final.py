#!/usr/bin/env python3
"""Fix all indentation issues in bybit.py"""

# Read the file
with open('src/core/exchanges/bybit.py', 'r') as f:
    lines = f.readlines()

# Fix line 767 - should be empty line (no spaces)
if len(lines) > 766 and lines[766].strip() == '':
    lines[766] = '\n'
    print("Fixed line 767 - removed extra spaces")

# Write back
with open('src/core/exchanges/bybit.py', 'w') as f:
    f.writelines(lines)

print("Fixed indentation issues")

# Verify
try:
    import ast
    with open('src/core/exchanges/bybit.py', 'r') as f:
        code = f.read()
    ast.parse(code)
    print("✓ File syntax is valid!")
except SyntaxError as e:
    print(f"✗ Syntax error remains: {e}")
    print(f"  Line {e.lineno}: {e.text}")
    print(f"  Error at position {e.offset}")