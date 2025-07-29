#!/usr/bin/env python3
"""
Patch to add confluence table display to monitor.py
"""

import sys

def add_confluence_table_display():
    """Add confluence table display after component scores logging"""
    
    # The code to insert after line 3312
    insert_code = """            
            # Display comprehensive confluence score table with enhanced interpretations
            try:
                from src.core.formatting.formatter import LogFormatter
                formatted_table = LogFormatter.format_enhanced_confluence_score_table(
                    symbol=symbol,
                    confluence_score=confluence_score,
                    components=components,
                    results=formatter_results,
                    weights=result.get('weights', result.get('metadata', {}).get('weights', {})),
                    reliability=reliability
                )
                # Log the formatted table
                self.logger.info("\\n" + formatted_table)
            except Exception as e:
                self.logger.error(f"Error displaying confluence table: {str(e)}")
                self.logger.debug(traceback.format_exc())
"""
    
    # Read the file
    try:
        with open('/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("Error: monitor.py file not found")
        return False
    
    # Find the line after which to insert
    insert_after = None
    for i, line in enumerate(lines):
        if 'self.logger.debug(f"{component}: {score}")' in line:
            insert_after = i + 1
            break
    
    if insert_after is None:
        print("Error: Could not find the component scores logging line")
        return False
    
    # Insert the new code
    # Split the insert_code by lines and add proper indentation
    code_lines = insert_code.split('\n')
    for j, code_line in enumerate(code_lines):
        lines.insert(insert_after + j, code_line + '\n')
    
    # Write the file back
    try:
        with open('/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py', 'w') as f:
            f.writelines(lines)
        print("Successfully added confluence table display to monitor.py")
        return True
    except Exception as e:
        print(f"Error writing file: {e}")
        return False

if __name__ == "__main__":
    if add_confluence_table_display():
        print("Patch applied successfully!")
        sys.exit(0)
    else:
        print("Patch failed!")
        sys.exit(1)