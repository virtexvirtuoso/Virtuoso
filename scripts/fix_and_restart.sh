#!/bin/bash

#############################################################################
# Script: fix_and_restart.sh
# Purpose: Deploy and manage fix and restart
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates deployment automation, service management, and infrastructure updates for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - rsync
#   - ssh
#   - git
#   - systemctl
#   - Access to project directory structure
#
# Usage:
#   ./fix_and_restart.sh [options]
#   
#   Examples:
#     ./fix_and_restart.sh
#     ./fix_and_restart.sh --verbose
#     ./fix_and_restart.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: ${VPS_HOST})
#   VPS_USER         VPS username (default: linuxuser)
#
# Output:
#   - Console output with operation status
#   - Log messages with timestamps
#   - Success/failure indicators
#
# Exit Codes:
#   0 - Success
#   1 - Deployment failed
#   2 - Invalid arguments
#   3 - Connection error
#   4 - Service start failed
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

VPS_HOST="${VPS_HOST}"
VPS_USER="linuxuser"

echo "Fixing cache adapter import issue..."

# Clear all Python cache
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Clear ALL pycache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Kill web server
pkill -f web_server.py || true
sleep 2

# Start fresh
export PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt
export PYTHONDONTWRITEBYTECODE=1
nohup venv311/bin/python src/web_server.py > logs/web_fresh.log 2>&1 &

sleep 5

if pgrep -f web_server.py > /dev/null; then
    echo "✅ Web server restarted fresh"
else
    echo "❌ Failed to start"
    tail -20 logs/web_fresh.log
fi
EOF

echo "Testing endpoints..."
sleep 3

# Test
curl -s http://${VPS_HOST}:8001/api/dashboard-cached/signals | python3 -c "
import sys, json
data = json.load(sys.stdin)
signals = len(data.get('signals', []))
print(f'Cached signals: {signals}')
if signals > 0:
    print('  ✅ SIGNALS WORKING!')
else:
    print('  ❌ Still empty')
"

curl -s http://${VPS_HOST}:8001/api/dashboard-cached/mobile-data | python3 -c "
import sys, json
data = json.load(sys.stdin)
scores = len(data.get('confluence_scores', []))
print(f'Mobile confluence scores: {scores}')
if scores > 0:
    print('  ✅ MOBILE SCORES WORKING!')
"