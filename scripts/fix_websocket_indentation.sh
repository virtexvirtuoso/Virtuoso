#!/bin/bash
# Fix duplicate function definition in websocket_manager.py

echo "Fixing WebSocket manager indentation issue..."

# Create a Python script to fix the issue
cat > /tmp/fix_websocket.py << 'EOF'
#!/usr/bin/env python3
import sys

# Read the file
with open('/home/linuxuser/trading/Virtuoso_ccxt/src/core/exchanges/websocket_manager.py', 'r') as f:
    lines = f.readlines()

# Find and remove the duplicate line
fixed_lines = []
prev_line = ""
for i, line in enumerate(lines):
    # Skip duplicate function definition
    if i == 150 and "async def _create_connection" in line and "async def _create_connection" in prev_line:
        print(f"Removing duplicate line {i+1}: {line.strip()}")
        continue
    fixed_lines.append(line)
    prev_line = line

# Write the fixed content
with open('/home/linuxuser/trading/Virtuoso_ccxt/src/core/exchanges/websocket_manager.py', 'w') as f:
    f.writelines(fixed_lines)

print("File fixed successfully!")
EOF

# Run the fix
python3 /tmp/fix_websocket.py

# Verify the fix
echo -e "\nVerifying fix..."
sed -n '149,155p' /home/linuxuser/trading/Virtuoso_ccxt/src/core/exchanges/websocket_manager.py

# Restart the service
echo -e "\nRestarting virtuoso service..."
sudo systemctl restart virtuoso.service

# Check status
sleep 3
echo -e "\nService status:"
sudo systemctl status virtuoso.service --no-pager | head -20