#!/usr/bin/env python3
"""
Quick fix to properly initialize the dashboard updater in main.py
"""

import sys
import re

def fix_main_py():
    """Fix the main.py file to properly start the dashboard updater."""
    
    main_file = "/home/linuxuser/trading/Virtuoso_ccxt/src/main.py"
    
    # Read the file
    with open(main_file, 'r') as f:
        lines = f.readlines()
    
    # Find where to add the dashboard updater initialization
    # Look for where we start the background cache update
    insert_index = None
    for i, line in enumerate(lines):
        if 'Background cache update started' in line:
            insert_index = i
            break
    
    if insert_index is None:
        # Find alternative location - after API server starts
        for i, line in enumerate(lines):
            if 'API server started on port' in line:
                insert_index = i + 1
                break
    
    if insert_index:
        # Insert the dashboard updater initialization
        updater_code = """            # Initialize and start dashboard updater
            try:
                from src.core.dashboard_updater import DashboardUpdater
                from src.core.api_cache import api_cache
                self.dashboard_updater = DashboardUpdater(self, api_cache, update_interval=30)
                self.dashboard_updater.start()
                logger.info("✅ Dashboard updater started successfully")
            except Exception as e:
                logger.error(f"Failed to start dashboard updater: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
"""
        
        # Check if already added
        full_text = ''.join(lines)
        if 'Dashboard updater started successfully' not in full_text:
            lines.insert(insert_index + 1, updater_code)
            
            # Write back
            with open(main_file, 'w') as f:
                f.writelines(lines)
            
            print("✅ Dashboard updater initialization added to main.py")
        else:
            print("✅ Dashboard updater already initialized in main.py")
    else:
        print("❌ Could not find insertion point in main.py")
        print("Adding at the end of run() method...")
        
        # Find the run method and add at the end
        in_run_method = False
        indent_level = 0
        for i, line in enumerate(lines):
            if 'async def run(self):' in line:
                in_run_method = True
                continue
            
            if in_run_method:
                # Check if we're still in the method
                if line.strip() and not line[0].isspace():
                    # We've left the method
                    # Insert before this line
                    updater_code = """        # Initialize and start dashboard updater
        try:
            from src.core.dashboard_updater import DashboardUpdater
            from src.core.api_cache import api_cache
            self.dashboard_updater = DashboardUpdater(self, api_cache, update_interval=30)
            self.dashboard_updater.start()
            logger.info("✅ Dashboard updater started successfully")
        except Exception as e:
            logger.error(f"Failed to start dashboard updater: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
"""
                    lines.insert(i, updater_code)
                    
                    with open(main_file, 'w') as f:
                        f.writelines(lines)
                    
                    print("✅ Dashboard updater initialization added to main.py")
                    break

if __name__ == "__main__":
    try:
        print("🔧 Fixing dashboard updater initialization...")
        fix_main_py()
        print("✅ Fix applied successfully")
        print("\nNow restart the service:")
        print("  sudo systemctl restart virtuoso")
    except Exception as e:
        print(f"❌ Error applying fix: {e}")
        sys.exit(1)