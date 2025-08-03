#!/usr/bin/env python3
"""
Add confluence table display in dashboard integration after getting confluence score
"""

import sys

def add_confluence_table_display():
    """Add confluence table display after getting confluence score"""
    
    # Read the file
    try:
        with open('/home/linuxuser/trading/Virtuoso_ccxt/src/dashboard/dashboard_integration.py', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("Error: dashboard_integration.py file not found")
        return False
    
    # Find the line to insert after
    insert_after = None
    for i, line in enumerate(lines):
        if 'self.logger.info(f"Got confluence score {score} for {symbol} from analyzer")' in line:
            insert_after = i + 1
            break
    
    if insert_after is None:
        print("Error: Could not find the target line")
        return False
    
    # Code to insert
    insert_code = """                        
                        # Display comprehensive confluence score table
                        try:
                            from src.core.formatting.formatter import LogFormatter
                            components = result.get('components', {})
                            results = result.get('results', {})
                            weights = result.get('weights', result.get('metadata', {}).get('weights', {}))
                            reliability = result.get('reliability', 0.0)
                            
                            formatted_table = LogFormatter.format_enhanced_confluence_score_table(
                                symbol=symbol,
                                confluence_score=score,
                                components=components,
                                results=results,
                                weights=weights,
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
        with open('/home/linuxuser/trading/Virtuoso_ccxt/src/dashboard/dashboard_integration.py', 'w') as f:
            f.writelines(lines)
        print("Successfully added confluence table display to dashboard_integration.py")
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