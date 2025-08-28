#!/usr/bin/env python3
"""Fix indentation issues in bybit.py properly"""

def fix_indentation(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Find the _make_request method and fix indentation
    in_make_request = False
    base_indent = 0
    
    for i, line in enumerate(lines):
        if 'async def _make_request' in line:
            in_make_request = True
            base_indent = 8  # Standard method body indent (2 levels)
            continue
        
        if in_make_request and line.strip() and not line.startswith(' ' * base_indent) and not line.strip().startswith('#'):
            # Check if this is the start of another method
            if 'async def ' in line or 'def ' in line:
                in_make_request = False
                continue
        
        if in_make_request:
            # Fix lines that are part of the debug logging but have wrong indentation
            if '# DETAILED DEBUG LOGGING' in line:
                lines[i] = ' ' * base_indent + line.lstrip()
                print(f"Fixed line {i+1}: {line.strip()[:50]}")
            elif 'request_id = f' in line:
                lines[i] = ' ' * base_indent + line.lstrip()
                print(f"Fixed line {i+1}: {line.strip()[:50]}")
            elif '# Log session state' in line:
                lines[i] = ' ' * base_indent + line.lstrip()
                print(f"Fixed line {i+1}: {line.strip()[:50]}")
            elif '# Log intelligence adapter state' in line:
                lines[i] = ' ' * base_indent + line.lstrip()
                print(f"Fixed line {i+1}: {line.strip()[:50]}")
            elif '# Track request timing' in line:
                lines[i] = ' ' * base_indent + line.lstrip()
                print(f"Fixed line {i+1}: {line.strip()[:50]}")
            elif 'request_start = time.time()' in line:
                lines[i] = ' ' * base_indent + line.lstrip()
                print(f"Fixed line {i+1}: {line.strip()[:50]}")
            
            # Fix the session/connector logging that has wrong indentation
            elif 'if hasattr(self, \'session\')' in line or 'if hasattr(self, "session")' in line:
                if not line.startswith(' ' * base_indent):
                    lines[i] = ' ' * base_indent + line.lstrip()
                    print(f"Fixed line {i+1}: {line.strip()[:50]}")
            elif 'self.logger.debug(f"  Session' in line:
                lines[i] = ' ' * (base_indent + 4) + line.lstrip()
                print(f"Fixed line {i+1}: {line.strip()[:50]}")
            elif 'if hasattr(self.session, \'connector\')' in line or 'if hasattr(self.session, "connector")' in line:
                lines[i] = ' ' * (base_indent + 4) + line.lstrip()
                print(f"Fixed line {i+1}: {line.strip()[:50]}")
            elif 'connector = self.session.connector' in line:
                lines[i] = ' ' * (base_indent + 8) + line.lstrip()
                print(f"Fixed line {i+1}: {line.strip()[:50]}")
            elif 'self.logger.debug(f"  Connector' in line:
                lines[i] = ' ' * (base_indent + 8) + line.lstrip()
                print(f"Fixed line {i+1}: {line.strip()[:50]}")
            elif line.strip() == 'else:' and i > 0 and 'session' in lines[i-2]:
                lines[i] = ' ' * base_indent + line.lstrip()
                print(f"Fixed line {i+1}: {line.strip()[:50]}")
            elif 'self.logger.debug("  No session available!")' in line:
                lines[i] = ' ' * (base_indent + 4) + line.lstrip()
                print(f"Fixed line {i+1}: {line.strip()[:50]}")
            elif 'if hasattr(self, \'intelligence_enabled\')' in line or 'if hasattr(self, "intelligence_enabled")' in line:
                lines[i] = ' ' * base_indent + line.lstrip()
                print(f"Fixed line {i+1}: {line.strip()[:50]}")
            elif 'self.logger.debug(f"  Intelligence Adapter' in line:
                lines[i] = ' ' * (base_indent + 4) + line.lstrip()
                print(f"Fixed line {i+1}: {line.strip()[:50]}")
    
    with open(file_path, 'w') as f:
        f.writelines(lines)
    
    print("\n✅ Fixed indentation issues")

if __name__ == "__main__":
    fix_indentation('src/core/exchanges/bybit.py')