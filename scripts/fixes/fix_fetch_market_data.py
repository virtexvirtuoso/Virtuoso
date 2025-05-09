"""
Fix script to add the missing fetch_market_data method to the MarketMonitor class.

This script addresses the error: 'MarketMonitor' object has no attribute 'fetch_market_data'
by adding the fetch_market_data method to the MarketMonitor class.
"""

import re
import os
import sys
import traceback

def add_fetch_market_data_method():
    """
    Add the fetch_market_data method to the MarketMonitor class.
    """
    # Determine the file path based on the current directory
    monitor_path = 'src/monitoring/monitor.py'
    
    # Check if the file exists
    if not os.path.isfile(monitor_path):
        print(f"Error: {monitor_path} not found")
        return False
    
    # Read the current file content
    with open(monitor_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Make a backup of the original file
    import datetime
    backup_path = f"{monitor_path}.bak_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created backup at {backup_path}")
    
    # Define the fetch_market_data method to add (with proper indentation)
    fetch_market_data_method = """
    async def fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        \"\"\"Fetch market data for a symbol from the market data manager.
        
        Args:
            symbol: The symbol to fetch market data for
            
        Returns:
            Dict[str, Any]: Market data dictionary with various components
        \"\"\"
        try:
            if not self.market_data_manager:
                self.logger.error("Market data manager not initialized")
                return None
                
            # Fetch market data through the manager
            market_data = await self.market_data_manager.get_market_data(symbol)
            
            if not market_data:
                self.logger.warning(f"No market data returned for {symbol}")
                return None
                
            return market_data
        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol}: {{str(e)}}")
            self.logger.debug(traceback.format_exc())
            return None
"""
    
    # Find MarketMonitor classes in the file
    class_positions = []
    for match in re.finditer(r'class MarketMonitor:', content):
        class_positions.append(match.start())
    
    # If no MarketMonitor class found, exit
    if not class_positions:
        print("Error: No MarketMonitor class found in the file")
        return False
    
    # Create a new file with the method added to each MarketMonitor class
    new_content = content
    
    for pos in class_positions:
        # Find a good location to insert the method
        # Look for methods like start, stop, or _process_symbol
        insert_methods = ["async def _process_symbol", "async def start", "async def stop", "def __init__"]
        
        # Search from the class definition to find the first of these methods
        class_text = content[pos:]
        insert_pos = None
        
        for method in insert_methods:
            method_match = re.search(f"(\\n[ \\t]+{method})", class_text)
            if method_match:
                # Find the corresponding indentation level
                whitespace_match = re.match(r"(\n[ \t]+)", method_match.group(1))
                if whitespace_match:
                    indent = whitespace_match.group(1)
                    # Add the method at the position with proper indentation
                    indented_method = fetch_market_data_method.replace("\n    ", indent)
                    # Find insertion point - after the first method definition
                    method_end = class_text.find("\n", method_match.start() + 1)
                    next_def = class_text.find("    def", method_end)
                    next_async_def = class_text.find("    async def", method_end)
                    
                    # Use the nearest next method or other logical break
                    if next_def != -1 and next_async_def != -1:
                        insert_method_end = min(next_def, next_async_def)
                    elif next_def != -1:
                        insert_method_end = next_def
                    elif next_async_def != -1:
                        insert_method_end = next_async_def
                    else:
                        # If no next method, insert at the end of the class
                        insert_method_end = len(class_text)
                    
                    # Find the method body end (looking for consistent indentation)
                    while insert_method_end < len(class_text):
                        if class_text[insert_method_end:].startswith(indent + "def") or \
                           class_text[insert_method_end:].startswith(indent + "async def"):
                            break
                        insert_method_end += 1
                    
                    insert_pos = pos + insert_method_end
                    break
        
        # If we found an insertion point, add the method there
        if insert_pos is not None:
            # Check if the method already exists
            if "def fetch_market_data" in new_content[pos:insert_pos]:
                print("The fetch_market_data method already exists in this class, skipping...")
                continue
            
            # Insert our method before the next method
            new_content = new_content[:insert_pos] + indented_method + new_content[insert_pos:]
            print(f"Added fetch_market_data method to MarketMonitor class at position {insert_pos}")
    
    # Write the updated content back to the file
    with open(monitor_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"Successfully added fetch_market_data method to {monitor_path}")
    return True

if __name__ == "__main__":
    try:
        # Restore from backup if needed
        import datetime
        monitor_path = 'src/monitoring/monitor.py'
        backup_files = [f for f in os.listdir('src/monitoring') if f.startswith('monitor.py.bak_')]
        
        if backup_files and len(sys.argv) > 1 and sys.argv[1] == "--restore":
            # Sort by timestamp (most recent first)
            backup_files.sort(reverse=True)
            latest_backup = os.path.join('src/monitoring', backup_files[0])
            print(f"Restoring from backup: {latest_backup}")
            
            with open(latest_backup, 'r', encoding='utf-8') as f:
                backup_content = f.read()
            
            with open(monitor_path, 'w', encoding='utf-8') as f:
                f.write(backup_content)
            
            print("Restore completed")
            sys.exit(0)
        
        # Apply the fix
        success = add_fetch_market_data_method()
        if success:
            print("Fix applied successfully")
            sys.exit(0)
        else:
            print("Failed to apply fix")
            sys.exit(1)
    except Exception as e:
        print(f"Error applying fix: {str(e)}")
        traceback.print_exc()
        sys.exit(1) 