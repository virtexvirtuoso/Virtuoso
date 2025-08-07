#!/bin/bash
# Setup web server as a systemd service

echo "🚀 Setting up Virtuoso Web Server as systemd service..."

# Create the service file
cat > /tmp/virtuoso-web.service << 'EOF'
[Unit]
Description=Virtuoso Trading Web Dashboard
After=network.target virtuoso.service
Wants=virtuoso.service

[Service]
Type=simple
User=linuxuser
Group=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
Environment="PATH=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt"
ExecStartPre=/bin/sleep 10
ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/uvicorn src.web_server:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10
StandardOutput=append:/home/linuxuser/trading/Virtuoso_ccxt/logs/web_server.log
StandardError=append:/home/linuxuser/trading/Virtuoso_ccxt/logs/web_server_error.log

[Install]
WantedBy=multi-user.target
EOF

# Deploy to VPS
echo "📤 Deploying to VPS..."
scp /tmp/virtuoso-web.service linuxuser@45.77.40.77:/tmp/

# Install and enable the service
echo "📦 Installing service on VPS..."
ssh linuxuser@45.77.40.77 << 'REMOTE_COMMANDS'
# Stop any existing web server
pkill -f 'uvicorn.*web_server' || true

# Install the service
sudo cp /tmp/virtuoso-web.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable virtuoso-web.service
sudo systemctl start virtuoso-web.service

# Check status
sleep 3
sudo systemctl status virtuoso-web.service

# Verify it's listening
sudo ss -tlnp | grep :8001
REMOTE_COMMANDS

echo "✅ Web server service setup complete!"
echo ""
echo "Useful commands:"
echo "  Check status:  sudo systemctl status virtuoso-web"
echo "  View logs:     sudo journalctl -u virtuoso-web -f"
echo "  Restart:       sudo systemctl restart virtuoso-web"
echo "  Stop:          sudo systemctl stop virtuoso-web"
echo "  Start:         sudo systemctl start virtuoso-web"