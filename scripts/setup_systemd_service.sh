#!/bin/bash

echo "🔧 Setting up Virtuoso Trading Bot as systemd service"
echo "===================================================="

cd ~/trading/Virtuoso_ccxt

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${YELLOW}1. Creating systemd service file...${NC}"

# Create the service file
sudo tee /etc/systemd/system/virtuoso.service > /dev/null << EOF
[Unit]
Description=Virtuoso Trading Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=linuxuser
Group=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
Environment=PATH=/home/linuxuser/trading/Virtuoso_ccxt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv/bin/python src/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=virtuoso

# Resource limits
MemoryMax=2G
CPUQuota=80%

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/linuxuser/trading/Virtuoso_ccxt

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created"

echo -e "\n${YELLOW}2. Reloading systemd and enabling service...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable virtuoso.service

echo -e "\n${YELLOW}3. Stopping any running instances...${NC}"
# Kill any existing python processes
pkill -f "python src/main.py" || true
sleep 5

echo -e "\n${YELLOW}4. Starting the service...${NC}"
sudo systemctl start virtuoso.service

echo -e "\n${YELLOW}5. Checking service status...${NC}"
sudo systemctl status virtuoso.service --no-pager

echo -e "\n${GREEN}=============================================="
echo "✅ Systemd service setup complete!"
echo "===============================================${NC}"
echo ""
echo "Service management commands:"
echo "  sudo systemctl start virtuoso    # Start service"
echo "  sudo systemctl stop virtuoso     # Stop service"
echo "  sudo systemctl restart virtuoso  # Restart service"
echo "  sudo systemctl status virtuoso   # Check status"
echo "  sudo journalctl -u virtuoso -f   # View logs"
echo ""
echo "Dashboard accessible at: http://45.77.40.77:8003/dashboard"
echo ""
echo "🎉 Your trading bot is now running 24/7!"