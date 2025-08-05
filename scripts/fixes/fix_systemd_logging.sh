#!/bin/bash

echo "=========================================="
echo "Fixing Virtuoso Logging for Systemd"
echo "=========================================="

# Create a backup of main.py
echo "1. Creating backup of main.py..."
cp /home/linuxuser/trading/Virtuoso_ccxt/src/main.py /home/linuxuser/trading/Virtuoso_ccxt/src/main.py.backup_$(date +%Y%m%d_%H%M%S)

# Add logging verification to main.py
echo "2. Adding logging verification to main.py..."

# Find the line number after logging configuration
LINE_NUM=$(grep -n "logger.info(\"🚀 Starting Virtuoso" /home/linuxuser/trading/Virtuoso_ccxt/src/main.py | cut -d: -f1)

if [ -z "$LINE_NUM" ]; then
    echo "ERROR: Could not find the target line in main.py"
    exit 1
fi

# Create the patch
cat > /tmp/logging_patch.py << 'EOF'

# Ensure logging is properly configured (systemd fix)
import sys
_root_logger = logging.getLogger()
if len(_root_logger.handlers) == 0:
    _console = logging.StreamHandler(sys.stdout)
    _console.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s'))
    _console.setLevel(logging.DEBUG)
    _root_logger.addHandler(_console)
    _root_logger.setLevel(logging.DEBUG)
    logger.warning("Applied systemd logging fix - handlers were missing")

EOF

# Insert the patch
echo "3. Applying patch..."
sed -i "${LINE_NUM}r /tmp/logging_patch.py" /home/linuxuser/trading/Virtuoso_ccxt/src/main.py

# Restart the service
echo "4. Restarting virtuoso service..."
sudo systemctl restart virtuoso

# Wait for service to start
sleep 3

# Check status
echo "5. Checking service status..."
sudo systemctl status virtuoso --no-pager | head -20

# Check logs
echo ""
echo "6. Recent logs from journalctl:"
sudo journalctl -u virtuoso -n 20 --no-pager

echo ""
echo "=========================================="
echo "Fix applied. Check logs with:"
echo "  sudo journalctl -u virtuoso -f"
echo "=========================================="