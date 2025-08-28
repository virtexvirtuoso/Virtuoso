#!/usr/bin/env python3
"""Final comprehensive indentation fix"""

def fix_all_indentation():
    with open('src/core/exchanges/bybit.py', 'r') as f:
        lines = f.readlines()
    
    # Find the problematic debug logging section around line 1295
    for i in range(1290, min(1320, len(lines))):
        if '# DETAILED DEBUG LOGGING' in lines[i]:
            # This should be at the same indent as the code before it
            # Look at the line before to get proper indent
            prev_line_indent = len(lines[i-1]) - len(lines[i-1].lstrip())
            lines[i] = ' ' * prev_line_indent + lines[i].lstrip()
            
            # Now fix all the following debug lines to have same indent
            base_indent = prev_line_indent
            
            # Fix request_id line
            if i+1 < len(lines) and 'request_id = f' in lines[i+1]:
                lines[i+1] = ' ' * base_indent + lines[i+1].lstrip()
            
            # Fix all self.logger.debug lines that follow
            for j in range(i+2, min(i+10, len(lines))):
                if 'self.logger.debug(f"🔍' in lines[j] or 'self.logger.debug(f"  ' in lines[j]:
                    lines[j] = ' ' * base_indent + lines[j].lstrip()
                elif lines[j].strip() and not lines[j].strip().startswith('#'):
                    # Stop when we hit non-debug code
                    break
            
            print(f"Fixed debug logging block starting at line {i+1}")
            break
    
    # Fix the session state logging section
    for i in range(1300, min(1320, len(lines))):
        if '# Log session state' in lines[i]:
            # This should be at same indent as the debug block above
            base_indent = 12  # 3 levels of indent for code inside _make_request
            lines[i] = ' ' * base_indent + lines[i].lstrip()
            
            # Fix the if statement
            if i+1 < len(lines) and 'if hasattr(self' in lines[i+1]:
                lines[i+1] = ' ' * base_indent + lines[i+1].lstrip()
            
            # Fix the nested code
            for j in range(i+2, min(i+10, len(lines))):
                if 'self.logger.debug(f"  Session' in lines[j]:
                    lines[j] = ' ' * (base_indent + 4) + lines[j].lstrip()
                elif 'if hasattr(self.session' in lines[j]:
                    lines[j] = ' ' * (base_indent + 4) + lines[j].lstrip()
                elif 'connector = self.session.connector' in lines[j]:
                    lines[j] = ' ' * (base_indent + 8) + lines[j].lstrip()
                elif 'self.logger.debug(f"  Connector' in lines[j]:
                    lines[j] = ' ' * (base_indent + 8) + lines[j].lstrip()
                elif lines[j].strip() == 'else:':
                    lines[j] = ' ' * base_indent + lines[j].lstrip()
                elif 'self.logger.debug("  No session' in lines[j]:
                    lines[j] = ' ' * (base_indent + 4) + lines[j].lstrip()
                elif lines[j].strip() and not lines[j].strip().startswith('#'):
                    # Stop at next section
                    break
            
            print(f"Fixed session state logging block starting at line {i+1}")
            break
    
    # Fix intelligence adapter logging
    for i in range(1310, min(1325, len(lines))):
        if '# Log intelligence adapter state' in lines[i]:
            base_indent = 12
            lines[i] = ' ' * base_indent + lines[i].lstrip()
            
            if i+1 < len(lines) and 'if hasattr(self' in lines[i+1]:
                lines[i+1] = ' ' * base_indent + lines[i+1].lstrip()
            
            if i+2 < len(lines) and 'self.logger.debug(f"  Intelligence' in lines[i+2]:
                lines[i+2] = ' ' * (base_indent + 4) + lines[i+2].lstrip()
            
            print(f"Fixed intelligence adapter logging block at line {i+1}")
            break
    
    # Fix request timing tracking
    for i in range(1314, min(1320, len(lines))):
        if '# Track request timing' in lines[i]:
            base_indent = 12
            lines[i] = ' ' * base_indent + lines[i].lstrip()
            
            if i+1 < len(lines) and 'request_start = time.time()' in lines[i+1]:
                lines[i+1] = ' ' * base_indent + lines[i+1].lstrip()
            
            print(f"Fixed request timing block at line {i+1}")
            break
    
    with open('src/core/exchanges/bybit.py', 'w') as f:
        f.writelines(lines)
    
    print("\n✅ Fixed all indentation issues")

if __name__ == "__main__":
    fix_all_indentation()