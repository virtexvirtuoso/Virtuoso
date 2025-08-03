#!/usr/bin/env python3
"""Simple test to check confluence breakdown logging."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Check if component breakdown is in the code
with open('src/core/analysis/confluence.py', 'r') as f:
    content = f.read()
    if 'Component scores:' in content:
        print("✅ Component scores logging code is present!")
        
        # Find the specific section
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'Component scores:' in line:
                print(f"\nFound at line {i+1}:")
                # Show surrounding lines
                start = max(0, i-5)
                end = min(len(lines), i+10)
                for j in range(start, end):
                    prefix = ">>> " if j == i else "    "
                    print(f"{prefix}{j+1}: {lines[j]}")
                break
    else:
        print("❌ Component scores logging code NOT found!")