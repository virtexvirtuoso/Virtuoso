#!/usr/bin/env python3
"""Fix syntax errors in bybit.py"""

def fix_syntax_errors(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    fixes_made = []
    
    # Fix 1: Move import statements to top of file
    import_lines = []
    for i, line in enumerate(lines):
        if i > 100 and 'import traceback' in line and line.strip() == 'import traceback':
            import_lines.append(i)
            fixes_made.append(f"Line {i+1}: Removed inline 'import traceback'")
    
    # Remove these import lines (in reverse order to maintain indices)
    for i in reversed(import_lines):
        del lines[i]
    
    # Add traceback import at the top with other imports
    if import_lines:
        # Find where other imports are
        for i, line in enumerate(lines[:50]):
            if 'import time' in line:
                lines.insert(i+1, 'import traceback\n')
                fixes_made.append("Added 'import traceback' to imports section")
                break
    
    # Fix 2: Fix any indentation issues with debug logging
    for i, line in enumerate(lines):
        # Fix the intelligence adapter logging that's misplaced
        if 'self.logger.debug("📡 Using Intelligence Adapter for request")' in line:
            # Check if it's properly indented
            if line.startswith('            self.logger.debug'):
                # It's at wrong position, should be after the if statement
                continue
            else:
                # Fix indentation - should be 16 spaces (4 levels of indent)
                lines[i] = '                ' + line.lstrip()
                fixes_made.append(f"Line {i+1}: Fixed indentation for intelligence adapter logging")
        
        # Fix debug logging that references request_id without proper indentation
        if 'request_id = f"{endpoint}_{time.time()}"' in line:
            # This should be indented at the same level as surrounding code
            # Check the line before to match indentation
            if i > 0:
                prev_indent = len(lines[i-1]) - len(lines[i-1].lstrip())
                current_indent = len(line) - len(line.lstrip())
                if current_indent != prev_indent and lines[i-1].strip():
                    lines[i] = ' ' * prev_indent + line.lstrip()
                    fixes_made.append(f"Line {i+1}: Fixed indentation for request_id")
    
    # Fix 3: Ensure debug code blocks are properly indented
    in_debug_block = False
    debug_block_indent = 0
    for i, line in enumerate(lines):
        if '# DETAILED DEBUG LOGGING' in line:
            in_debug_block = True
            # Get the indentation level from previous non-empty line
            for j in range(i-1, max(0, i-10), -1):
                if lines[j].strip() and not lines[j].strip().startswith('#'):
                    debug_block_indent = len(lines[j]) - len(lines[j].lstrip())
                    break
            lines[i] = ' ' * debug_block_indent + line.lstrip()
            fixes_made.append(f"Line {i+1}: Fixed debug block comment indentation")
        elif in_debug_block:
            # Apply same indentation to the debug block
            if line.strip() and not line.strip().startswith('#'):
                if 'request_id' in line or 'self.logger.debug' in line:
                    lines[i] = ' ' * debug_block_indent + line.lstrip()
            # End of debug block
            if line.strip() and not ('self.logger.debug' in line or 'request_id' in line or 'request_start' in line):
                in_debug_block = False
    
    # Write the fixed file
    with open(file_path, 'w') as f:
        f.writelines(lines)
    
    print("✅ Fixed syntax errors:")
    for fix in fixes_made:
        print(f"   - {fix}")
    
    return len(fixes_made) > 0

if __name__ == "__main__":
    import sys
    file_path = sys.argv[1] if len(sys.argv) > 1 else 'src/core/exchanges/bybit.py'
    if fix_syntax_errors(file_path):
        print("\n✅ All syntax errors fixed")
    else:
        print("\nℹ️ No syntax errors found")