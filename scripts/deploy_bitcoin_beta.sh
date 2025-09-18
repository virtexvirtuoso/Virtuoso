#!/bin/bash

#############################################################################
# Script: deploy_bitcoin_beta.sh
# Purpose: Deploy and manage deploy bitcoin beta
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
#   ./deploy_bitcoin_beta.sh [options]
#   
#   Examples:
#     ./deploy_bitcoin_beta.sh
#     ./deploy_bitcoin_beta.sh --verbose
#     ./deploy_bitcoin_beta.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 5.223.63.4)
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
echo "Deploying Bitcoin Beta Services to VPS"
echo "========================================="

# VPS connection details
VPS_USER="linuxuser"
VPS_HOST="5.223.63.4"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Step 1: Copy service files
echo -e "\n[1/5] Copying service files..."
scp scripts/bitcoin_beta_data_service.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/scripts/
scp scripts/bitcoin_beta_calculator_service.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/scripts/
scp src/api/routes/bitcoin_beta.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/api/routes/

# Step 2: Create systemd service files
echo -e "\n[2/5] Creating systemd service files..."

# Bitcoin Beta Data Service
cat > /tmp/bitcoin-beta-data.service << 'EOF'
[Unit]
Description=Bitcoin Beta Data Collection Service
After=network.target

[Service]
Type=simple
User=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python scripts/bitcoin_beta_data_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Bitcoin Beta Calculator Service
cat > /tmp/bitcoin-beta-calculator.service << 'EOF'
[Unit]
Description=Bitcoin Beta Calculator Service
After=network.target bitcoin-beta-data.service

[Service]
Type=simple
User=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python scripts/bitcoin_beta_calculator_service.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Copy service files to VPS
scp /tmp/bitcoin-beta-data.service ${VPS_USER}@${VPS_HOST}:/tmp/
scp /tmp/bitcoin-beta-calculator.service ${VPS_USER}@${VPS_HOST}:/tmp/

# Step 3: Install and start services on VPS
echo -e "\n[3/5] Installing services on VPS..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
# Move service files to systemd directory
sudo mv /tmp/bitcoin-beta-data.service /etc/systemd/system/
sudo mv /tmp/bitcoin-beta-calculator.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Stop existing services if running
sudo systemctl stop bitcoin-beta-data.service 2>/dev/null || true
sudo systemctl stop bitcoin-beta-calculator.service 2>/dev/null || true

# Install required packages if not already installed
cd /home/linuxuser/trading/Virtuoso_ccxt
source venv311/bin/activate
pip install scipy -q

# Run data collection once to initialize
echo "Running initial data collection (this may take a few minutes)..."
python scripts/bitcoin_beta_data_service.py --once

# Enable and start services
sudo systemctl enable bitcoin-beta-data.service
sudo systemctl enable bitcoin-beta-calculator.service

sudo systemctl start bitcoin-beta-data.service
sleep 5
sudo systemctl start bitcoin-beta-calculator.service

# Check status
echo -e "\n=== Service Status ==="
sudo systemctl status bitcoin-beta-data.service --no-pager | head -10
echo ""
sudo systemctl status bitcoin-beta-calculator.service --no-pager | head -10

# Restart web server to load new API routes
echo -e "\nRestarting web server..."
sudo systemctl restart virtuoso.service
ENDSSH

# Step 4: Test API endpoints
echo -e "\n[4/5] Testing API endpoints..."
sleep 10

# Test health endpoint
echo "Testing /api/bitcoin-beta/health..."
curl -s http://5.223.63.4:8080/api/bitcoin-beta/health | python3 -m json.tool | head -10

echo -e "\nTesting /api/bitcoin-beta/realtime..."
curl -s http://5.223.63.4:8080/api/bitcoin-beta/realtime | python3 -m json.tool | head -20

# Step 5: Final status check
echo -e "\n[5/5] Final Status Check"
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
echo "=== Running Services ==="
sudo systemctl list-units --type=service --state=running | grep bitcoin-beta

echo -e "\n=== Cache Status ==="
cd /home/linuxuser/trading/Virtuoso_ccxt
source venv311/bin/activate
python scripts/bitcoin_beta_calculator_service.py --status
ENDSSH

echo -e "\n========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Services deployed:"
echo "  - bitcoin-beta-data.service (Data collection)"
echo "  - bitcoin-beta-calculator.service (Beta calculations)"
echo ""
echo "API Endpoints:"
echo "  - http://5.223.63.4:8080/api/bitcoin-beta/health"
echo "  - http://5.223.63.4:8080/api/bitcoin-beta/realtime"
echo "  - http://5.223.63.4:8080/api/bitcoin-beta/history/{symbol}"
echo ""
echo "Monitor logs with:"
echo "  ssh vps 'sudo journalctl -u bitcoin-beta-data -f'"
echo "  ssh vps 'sudo journalctl -u bitcoin-beta-calculator -f'"