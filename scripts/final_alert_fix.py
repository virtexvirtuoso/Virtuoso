#!/usr/bin/env python3
"""
Final fix for the persistent 'Virtuoso Signals APP' issue and $0.00 price
"""

import re

def fix_vps_alerts():
    """Create SSH commands to fix the VPS directly"""
    
    print("=" * 60)
    print("Final Alert Fix Commands for VPS")
    print("=" * 60)
    print()
    
    # Commands to run on VPS
    commands = [
        # 1. Clear all Python cache
        "find /home/linuxuser/trading/Virtuoso_ccxt -name '*.pyc' -delete",
        "find /home/linuxuser/trading/Virtuoso_ccxt -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null",
        
        # 2. Check and remove any "Virtuoso Signals APP" text
        """sed -i 's/"Virtuoso Signals APP"/""/g' /home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/alert_manager.py""",
        """sed -i "s/'Virtuoso Signals APP'/''/g" /home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/alert_manager.py""",
        
        # 3. Fix the webhook username if it's set
        """sed -i 's/username="Virtuoso Signals APP"/username=""/g' /home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/alert_manager.py""",
        
        # 4. Ensure formatter shows price even when 0
        """sed -i 's/if current_price > 0:/if current_price >= 0:/g' /home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/alert_formatter.py""",
        
        # 5. Fix early detection data to include price
        """python3 -c "
import sys
file_path = '/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py'
with open(file_path, 'r') as f:
    content = f.read()

# Fix early detection to ensure it passes current_price
content = content.replace(
    \\"'data': current_activity\\",
    \\"'data': {**current_activity, 'current_price': current_price} if 'current_activity' in locals() else {'current_price': current_price}\\"
)

with open(file_path, 'w') as f:
    f.write(content)
print('Fixed early detection data')
" """,
        
        # 6. Restart service
        "sudo systemctl restart virtuoso.service",
        
        # 7. Check status
        "sleep 3 && sudo systemctl status virtuoso.service --no-pager | head -10"
    ]
    
    print("Run these commands on the VPS:")
    print()
    for i, cmd in enumerate(commands, 1):
        if len(cmd) > 100:
            # For long commands, show a shortened version
            print(f"{i}. {cmd[:80]}...")
        else:
            print(f"{i}. {cmd}")
    print()
    
    # Create a single command to run all
    all_commands = " && ".join(commands[:6])  # Exclude status check
    
    print("Or run all at once with:")
    print()
    print(f'ssh linuxuser@VPS_HOST_REDACTED "{all_commands}"')
    print()
    
    print("Then check status with:")
    print('ssh linuxuser@VPS_HOST_REDACTED "sudo systemctl status virtuoso.service"')

if __name__ == "__main__":
    fix_vps_alerts()