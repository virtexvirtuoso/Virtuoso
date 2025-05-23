#!/usr/bin/env python
"""Fix indentation issues in monitor.py"""

import re

def fix_indentation():
    """Fix indentation issues in monitor.py"""
    print("Fixing indentation in monitor.py...")
    
    # Read the original file
    with open('src/monitoring/monitor.py', 'r') as f:
        content = f.read()
    
    # Fix get_monitored_symbols method
    pattern1 = r'(def get_monitored_symbols.*?try:.*?return \[.*?if symbols:.*?)except Exception as e:(.*?self\.logger\.error.*?return \[\])'
    replacement1 = r'\1        except Exception as e:\2'
    
    # Use re.DOTALL to match across multiple lines
    content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)
    
    # Fix _generate_market_report method
    pattern2 = r'(async def _generate_market_report.*?try:.*?# Get latest data for this symbol.*?)if hasattr\(self, \'market_data_manager\'\)(.*?return\n\n.*?# Generate the report data.*?)except Exception as e:(.*?self\.logger\.error.*?self\.logger\.debug.*?)else:(.*?self\.logger\.warning.*?)# Get final memory usage)'
    replacement2 = r'\1            if hasattr(self, \'market_data_manager\')\2            except Exception as e:\3        else:\4        # Get final memory usage'
    
    content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)
    
    # Check for syntax errors
    try:
        compile(content, 'monitor.py', 'exec')
        print("Syntax check passed")
    except SyntaxError as e:
        print(f"Syntax error detected: {e}")
        
    # Write the fixed file
    with open('src/monitoring/monitor.py', 'w') as f:
        f.write(content)
    
    print("Fixed indentation in monitor.py")
    
if __name__ == '__main__':
    fix_indentation() 