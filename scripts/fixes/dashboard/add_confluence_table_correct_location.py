#!/usr/bin/env python3
"""
Add confluence table display at the correct location (after Component scores in process_symbol)
"""

import sys

def add_confluence_table_display():
    """Add confluence table display after Component scores logging"""
    
    # Read the file
    try:
        with open('/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("Error: monitor.py file not found")
        return False
    
    # Find the line with Component scores logging
    insert_after = None
    for i, line in enumerate(lines):
        if 'self.logger.info(f"Component scores: {\', \'.join(component_scores)}")' in line:
            insert_after = i + 1
            break
    
    if insert_after is None:
        print("Error: Could not find the Component scores logging line")
        return False
    
    # Code to insert
    insert_code = """                    
                    # Display comprehensive confluence score table
                    try:
                        from src.core.formatting.formatter import LogFormatter
                        formatted_table = LogFormatter.format_enhanced_confluence_score_table(
                            symbol=symbol_str,
                            confluence_score=score,
                            components=components,
                            results=analysis_result.get('results', {}),
                            weights=analysis_result.get('weights', analysis_result.get('metadata', {}).get('weights', {})),
                            reliability=reliability
                        )
                        # Log the formatted table
                        self.logger.info("\\n" + formatted_table)
                    except Exception as e:
                        self.logger.error(f"Error displaying confluence table: {str(e)}")
                        import traceback
                        self.logger.debug(traceback.format_exc())
"""
    
    # Insert the new code
    code_lines = insert_code.split('\n')
    for j, code_line in enumerate(code_lines):
        lines.insert(insert_after + j, code_line + '\n')
    
    # Write the file back
    try:
        with open('/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py', 'w') as f:
            f.writelines(lines)
        print("Successfully added confluence table display after Component scores")
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