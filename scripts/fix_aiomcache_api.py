#!/usr/bin/env python3
"""
Fix aiomcache API usage - change expire to exptime
"""
import os
import re

files_to_fix = [
    'src/services/market_service.py',
    'src/services/analysis_service.py',
    'scripts/test_phase2_services.py'
]

for filepath in files_to_fix:
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Replace expire= with exptime=
        updated = re.sub(r'\bexpire=', 'exptime=', content)
        
        if updated != content:
            with open(filepath, 'w') as f:
                f.write(updated)
            print(f"✅ Fixed {filepath}")
        else:
            print(f"No changes needed in {filepath}")
    else:
        print(f"File not found: {filepath}")

print("\nDone! Files updated to use exptime instead of expire")