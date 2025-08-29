#!/bin/bash

echo "🔧 Fixing web server startup on VPS..."

# Create a patched version of main.py
cat << 'EOF' > /tmp/main_startup_fix.py
# This patch fixes the web server not starting issue
# The problem is that monitoring_main() runs forever in a loop,
# preventing the code from reaching the part where both tasks are created

# Find the line with "monitoring_task = asyncio.create_task(monitoring_main(), name="monitoring_main")"
# And move the web server and monitoring task creation BEFORE the monitoring loop

import sys
import re

# Read the file
with open('src/main.py', 'r') as f:
    content = f.read()

# Find and fix the issue
# The problem is the monitoring_main function runs forever
# We need to restructure so both tasks start immediately

# Replace the problematic section
old_pattern = r'(\s+# Simplified monitoring main function\n\s+async def monitoring_main\(\):.*?)(# Create tasks for both the monitoring system and web server.*?web_server_task = asyncio\.create_task\(start_web_server\(\), name="web_server"\).*?)'
new_content = content

# Simple fix: Start the web server BEFORE entering the monitoring loop
# Find where we call monitoring_main and web server tasks
lines = content.split('\n')
new_lines = []
inside_run_application = False
fixed = False

for i, line in enumerate(lines):
    if 'async def run_application():' in line:
        inside_run_application = True
    
    # Look for where monitoring_main is defined inside run_application
    if inside_run_application and not fixed and 'async def monitoring_main():' in line:
        # We found the nested function definition
        # We need to start the web server task BEFORE entering the monitoring loop
        # Insert web server start before monitoring_main definition
        new_lines.append('        # Start web server task immediately')
        new_lines.append('        logger.info("🌐 Starting web server on port 8003...")')
        new_lines.append('        web_server_task = asyncio.create_task(start_web_server(), name="web_server")')
        new_lines.append('        logger.info("✅ Web server task created!")')
        new_lines.append('')
        fixed = True
    
    new_lines.append(line)

# Write the fixed content
with open('src/main.py', 'w') as f:
    f.write('\n'.join(new_lines))

print("✅ Fixed web server startup issue")
EOF

# Copy fix script to VPS
echo "📤 Copying fix script to VPS..."
scp /tmp/main_startup_fix.py linuxuser@45.77.40.77:/tmp/

# Apply the fix on VPS
echo "🔨 Applying fix on VPS..."
ssh linuxuser@45.77.40.77 << 'REMOTE_EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Backup current main.py
cp src/main.py src/main.py.backup.$(date +%Y%m%d_%H%M%S)

# Apply the fix
python3 /tmp/main_startup_fix.py

# Restart the service
echo "🔄 Restarting virtuoso service..."
sudo systemctl restart virtuoso.service

# Wait for service to start
sleep 5

# Check if ports are now listening
echo "🔍 Checking if web servers are now running..."
echo "Port 8003 (Main API):"
curl -s -o /dev/null -w "Status: %{http_code}, Time: %{time_total}s\n" http://localhost:8003/health || echo "Still not responding"

echo "Port 8001 (Monitoring):"
curl -s -o /dev/null -w "Status: %{http_code}, Time: %{time_total}s\n" http://localhost:8001/api/monitoring/status || echo "Still not responding"

# Check if processes are listening
echo ""
echo "🔍 Checking listening ports:"
sudo netstat -tlnp | grep -E "8003|8001" || echo "Ports not listening yet"

# Show recent logs
echo ""
echo "📋 Recent service logs:"
sudo journalctl -u virtuoso.service --no-pager -n 10 | grep -E "Web server|web_server|8003|Starting|ERROR"
REMOTE_EOF

echo "✅ Fix applied! Check output above for results."