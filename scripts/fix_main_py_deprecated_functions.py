#!/usr/bin/env python3
"""Fix main.py by properly commenting out deprecated functions."""

import re
from pathlib import Path

def fix_main_py():
    """Fix main.py by commenting out deprecated function sections."""
    main_file = Path(__file__).parent.parent / "src" / "main.py"
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Find the deprecated cleanup function and comment it out properly
    lines = content.split('\n')
    new_lines = []
    in_deprecated_cleanup = False
    in_deprecated_init = False
    
    for i, line in enumerate(lines):
        # Check if we're starting a deprecated section
        if "# DEPRECATED: Replaced by Container.cleanup()" in line:
            in_deprecated_cleanup = True
            new_lines.append(line)
            continue
        elif "# DEPRECATED: Replaced by Container.initialize()" in line:
            in_deprecated_init = True
            new_lines.append(line)
            continue
        
        # Check if we're ending a deprecated section
        if in_deprecated_cleanup and line.startswith("# DEPRECATED:"):
            in_deprecated_cleanup = False
        elif in_deprecated_init and line.startswith("@asynccontextmanager"):
            in_deprecated_init = False
        
        # If we're in a deprecated section, comment out non-commented lines
        if (in_deprecated_cleanup or in_deprecated_init) and line.strip():
            if not line.strip().startswith('#'):
                new_lines.append(f"# {line}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Write the fixed content back
    fixed_content = '\n'.join(new_lines)
    
    with open(main_file, 'w') as f:
        f.write(fixed_content)
    
    print("✅ Fixed deprecated functions in main.py")

if __name__ == "__main__":
    fix_main_py()