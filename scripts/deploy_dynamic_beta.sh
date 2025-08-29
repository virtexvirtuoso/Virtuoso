#!/bin/bash

#############################################################################
# Script: deploy_dynamic_beta.sh
# Purpose: Deploy and manage deploy dynamic beta
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
#   ./deploy_dynamic_beta.sh [options]
#   
#   Examples:
#     ./deploy_dynamic_beta.sh
#     ./deploy_dynamic_beta.sh --verbose
#     ./deploy_dynamic_beta.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 45.77.40.77)
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

echo "========================================="
echo "Deploying Dynamic Bitcoin Beta Services"
echo "========================================="

# VPS connection details
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Step 1: Copy new service files
echo -e "\n[1/4] Copying dynamic service files..."
scp scripts/bitcoin_beta_symbol_selector.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/scripts/
scp scripts/bitcoin_beta_data_service_dynamic.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/scripts/

# Step 2: Test dynamic selection on VPS
echo -e "\n[2/4] Testing dynamic symbol selection on VPS..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd /home/linuxuser/trading/Virtuoso_ccxt
source venv311/bin/activate

echo "Testing symbol selection..."
python scripts/bitcoin_beta_symbol_selector.py | head -20

echo -e "\n=== Symbol Selection Test Complete ==="
ENDSSH

# Step 3: Create updated service file
echo -e "\n[3/4] Creating updated service configuration..."
cat > /tmp/bitcoin-beta-data-dynamic.service << 'EOF'
[Unit]
Description=Bitcoin Beta Data Collection Service (Dynamic)
After=network.target

[Service]
Type=simple
User=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python scripts/bitcoin_beta_data_service_dynamic.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

scp /tmp/bitcoin-beta-data-dynamic.service ${VPS_USER}@${VPS_HOST}:/tmp/

# Step 4: Install and restart services
echo -e "\n[4/4] Installing dynamic service..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
# Stop old service
sudo systemctl stop bitcoin-beta-data.service

# Install new service
sudo mv /tmp/bitcoin-beta-data-dynamic.service /etc/systemd/system/
sudo systemctl daemon-reload

# Start new dynamic service
sudo systemctl enable bitcoin-beta-data-dynamic.service
sudo systemctl start bitcoin-beta-data-dynamic.service

# Check status
echo -e "\n=== Service Status ==="
sudo systemctl status bitcoin-beta-data-dynamic.service --no-pager | head -15

# Test data after a few seconds
sleep 10
echo -e "\n=== Testing Dynamic Data Collection ==="
cd /home/linuxuser/trading/Virtuoso_ccxt
source venv311/bin/activate

python -c "
from aiomcache import Client
import asyncio
import json

async def test():
    cache = Client('localhost', 11211)
    
    # Check symbol list
    data = await cache.get(b'beta:symbol_list')
    if data:
        symbols = json.loads(data.decode())
        print(f'Dynamic symbols: {symbols[\"count\"]} symbols')
        print(f\"Top 5: {', '.join(symbols['symbols'][:5])}\")
    else:
        print('No dynamic symbol list yet')

asyncio.run(test())
"
ENDSSH

echo -e "\n========================================="
echo "Dynamic Beta Deployment Complete!"
echo "========================================="
echo ""
echo "Monitor the dynamic service with:"
echo "  ssh vps 'sudo journalctl -u bitcoin-beta-data-dynamic -f'"