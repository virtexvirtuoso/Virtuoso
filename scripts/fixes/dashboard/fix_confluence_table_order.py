#!/usr/bin/env python3
"""
Fix the order of operations in the confluence table display
"""

import sys

def fix_confluence_table_order():
    """Fix the order of getting formatter_results and displaying the table"""
    
    # Read the file
    try:
        with open('/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print("Error: monitor.py file not found")
        return False
    
    # Find the section to fix
    # The formatter_results line needs to be BEFORE the confluence table display
    old_pattern = """            # Display comprehensive confluence score table with enhanced interpretations
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

            
            # Get formatter results directly from the ConfluenceAnalyzer output
            formatter_results = result.get('results', {})"""
    
    new_pattern = """            # Get formatter results directly from the ConfluenceAnalyzer output
            formatter_results = result.get('results', {})
            
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
                self.logger.debug(traceback.format_exc())"""
    
    # Replace the content
    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
        
        # Write the file back
        try:
            with open('/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py', 'w') as f:
                f.write(content)
            print("Successfully fixed the confluence table order")
            return True
        except Exception as e:
            print(f"Error writing file: {e}")
            return False
    else:
        print("Error: Could not find the pattern to replace")
        return False

if __name__ == "__main__":
    if fix_confluence_table_order():
        print("Fix applied successfully!")
        sys.exit(0)
    else:
        print("Fix failed!")
        sys.exit(1)