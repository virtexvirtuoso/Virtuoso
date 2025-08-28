#!/bin/bash

#############################################################################
# Script: setup_cache_service.sh
# Purpose: Set up Market Data Cache Service as systemd service
# Author: Virtuoso CCXT Development Team
# Version: 1.1.0
# Created: 2024-08-20
# Modified: 2024-08-28
#############################################################################
#
# Description:
#   Creates and configures a systemd service for the Market Data Cache Service
#   which provides high-performance caching for trading system data. The service
#   runs continuously in the background and depends on Memcached.
#
# Service Configuration:
#   - Service Name: market-data-cache.service
#   - User: linuxuser
#   - Working Directory: /home/linuxuser/trading/Virtuoso_ccxt
#   - Dependencies: network.target, memcached.service
#   - Auto-restart on failure (10 second delay)
#
# Usage:
#   ./setup_cache_service.sh
#
# Requirements:
#   - sudo privileges for systemctl operations
#   - Memcached service installed and configured
#   - Python virtual environment (venv311) set up
#   - market_data_cache_service.py script present
#
# Exit Codes:
#   0 - Service setup successful
#   1 - Permission denied (need sudo)
#   2 - Service creation failed
#
# Notes:
#   - Service is automatically enabled and started
#   - Logs are available via journalctl
#   - Restart policy ensures high availability
#
#############################################################################

# Setup script for Market Data Cache Service

cat > /tmp/market-data-cache.service << 'EOF'
[Unit]
Description=Market Data Cache Service for Virtuoso Trading System
After=network.target memcached.service
Wants=memcached.service

[Service]
Type=simple
User=linuxuser
Group=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
Environment="PATH=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python scripts/market_data_cache_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "Installing Market Data Cache Service..."
sudo mv /tmp/market-data-cache.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable market-data-cache.service
sudo systemctl start market-data-cache.service

echo "Service installed and started!"
echo "Check status with: sudo systemctl status market-data-cache.service"
echo "View logs with: sudo journalctl -u market-data-cache.service -f"