#!/bin/bash
# Fix indentation error in main.py

ssh linuxuser@45.77.40.77 << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Fix the indentation error
python3 << 'PYTHON'
with open('src/main.py', 'r') as f:
    lines = f.readlines()

# Fix line 907 and surrounding lines
for i in range(906, min(915, len(lines))):
    if lines[i].strip().startswith('try:'):
        # This line should have 8 spaces (2 indents) not 12
        lines[i] = '        try:\n'
    elif lines[i].strip().startswith('from src.core.dashboard_updater'):
        lines[i] = '            from src.core.dashboard_updater import DashboardUpdater\n'
    elif lines[i].strip().startswith('from src.core.api_cache'):
        lines[i] = '            from src.core.api_cache import api_cache\n'
    elif lines[i].strip().startswith('self.dashboard_updater'):
        lines[i] = '            self.dashboard_updater = DashboardUpdater(self, api_cache, update_interval=30)\n'
    elif lines[i].strip().startswith('self.dashboard_updater.start()'):
        lines[i] = '            self.dashboard_updater.start()\n'
    elif lines[i].strip().startswith('logger.info("✅ Dashboard updater'):
        lines[i] = '            logger.info("✅ Dashboard updater started successfully")\n'
    elif lines[i].strip().startswith('except Exception as e:'):
        lines[i] = '        except Exception as e:\n'
    elif lines[i].strip().startswith('logger.error(f"Failed to start dashboard'):
        lines[i] = '            logger.error(f"Failed to start dashboard updater: {e}")\n'
    elif lines[i].strip().startswith('import traceback'):
        lines[i] = '            import traceback\n'
    elif lines[i].strip().startswith('logger.error(traceback'):
        lines[i] = '            logger.error(traceback.format_exc())\n'

# Write back
with open('src/main.py', 'w') as f:
    f.writelines(lines)

print("✅ Fixed indentation")
PYTHON

# Test syntax
echo "Testing syntax..."
python3 -m py_compile src/main.py && echo "✅ Syntax OK" || echo "❌ Syntax error"

# Restart service
echo "Restarting service..."
sudo systemctl restart virtuoso

sleep 3

# Check status
systemctl is-active virtuoso && echo "✅ Service running" || echo "❌ Service failed"
EOF