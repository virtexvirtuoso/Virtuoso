#!/usr/bin/env python3
"""
Rollback script for root directory organization.
Generated on 2025-09-02 13:43:42
"""

import subprocess
from pathlib import Path

project_root = Path(__file__).parent

# Reverse the moves
moves_to_reverse = <list_reverseiterator object at 0x7f9c8811c750>

for target, source in moves_to_reverse:
    try:
        subprocess.run(['git', 'mv', target, source], check=True, cwd=project_root)
        print(f"Reversed: {target} -> {source}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to reverse: {target} -> {source}: {e}")

print("Rollback completed!")
