#!/bin/bash
set -e

echo "Deploying cache warmer service..."

# Copy cache warmer to VPS
scp src/monitoring/cache_warmer.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/

# Copy systemd service
scp scripts/systemd/virtuoso-cache-warmer.service vps:/tmp/

# Install and start service
ssh vps "sudo mv /tmp/virtuoso-cache-warmer.service /etc/systemd/system/ &&          sudo systemctl daemon-reload &&          sudo systemctl enable virtuoso-cache-warmer.service &&          sudo systemctl restart virtuoso-cache-warmer.service"

# Check status
ssh vps "sudo systemctl status virtuoso-cache-warmer.service | head -15"

echo "Cache warmer deployed and running!"
