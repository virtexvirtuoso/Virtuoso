#!/bin/bash

echo "========================================="
echo "Deploying Bitcoin Beta Services to VPS"
echo "========================================="

# VPS connection details
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
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
curl -s http://45.77.40.77:8080/api/bitcoin-beta/health | python3 -m json.tool | head -10

echo -e "\nTesting /api/bitcoin-beta/realtime..."
curl -s http://45.77.40.77:8080/api/bitcoin-beta/realtime | python3 -m json.tool | head -20

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
echo "  - http://45.77.40.77:8080/api/bitcoin-beta/health"
echo "  - http://45.77.40.77:8080/api/bitcoin-beta/realtime"
echo "  - http://45.77.40.77:8080/api/bitcoin-beta/history/{symbol}"
echo ""
echo "Monitor logs with:"
echo "  ssh vps 'sudo journalctl -u bitcoin-beta-data -f'"
echo "  ssh vps 'sudo journalctl -u bitcoin-beta-calculator -f'"