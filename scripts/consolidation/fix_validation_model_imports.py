#!/usr/bin/env python3
"""Fix imports after renaming ValidationError to ValidationErrorData in models.py"""

import re
from pathlib import Path

def fix_file(file_path: Path):
    """Fix imports in a single file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original = content
    
    # Fix the import line
    content = re.sub(
        r'from \.models import(.*)ValidationError(.*)',
        lambda m: f'from .models import{m.group(1)}ValidationErrorData{m.group(2)}\nfrom src.core.error.unified_exceptions import ValidationError',
        content
    )
    
    if content != original:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"✅ Fixed {file_path}")
        return True
    return False

def main():
    """Fix all validation model imports."""
    files_to_fix = [
        'src/core/validation/service.py',
        'src/core/validation/rules.py',
        'src/core/validation/__init__.py',
        'src/core/validation/validators.py',
        'src/core/validation/manager.py'
    ]
    
    project_root = Path(__file__).parent.parent.parent
    
    for file_path in files_to_fix:
        full_path = project_root / file_path
        if full_path.exists():
            fix_file(full_path)
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print("\n✅ All files updated!")

if __name__ == "__main__":
    main()