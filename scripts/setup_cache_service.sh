#!/bin/bash
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