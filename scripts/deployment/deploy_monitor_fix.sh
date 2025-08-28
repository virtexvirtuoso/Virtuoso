#!/bin/bash
# Deploy monitor.py fix to VPS

echo "🚀 Deploying monitor.py AttributeError fix to VPS..."

# Copy to pi first as staging area
echo "📤 Copying monitor.py to pi staging area..."
scp /Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/monitoring/monitor.py pi:/tmp/monitor_fixed.py

# Create deployment commands
echo "📋 Creating deployment commands..."
cat > /tmp/vps_deploy_commands.sh << 'EOF'
#!/bin/bash
# VPS deployment commands
echo "🔄 Stopping Virtuoso service..."
sudo systemctl stop virtuoso.service

echo "📥 Installing fixed monitor.py..."
cp /tmp/monitor_fixed.py /home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py

echo "✅ Setting correct permissions..."
chown linuxuser:linuxuser /home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py
chmod 644 /home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py

echo "🚀 Starting Virtuoso service..."
sudo systemctl start virtuoso.service

echo "📊 Checking service status..."
sleep 5
sudo systemctl status virtuoso.service --no-pager

echo "📝 Showing recent logs..."
sudo journalctl -u virtuoso.service -n 20 --no-pager
EOF

# Copy deployment script to pi
scp /tmp/vps_deploy_commands.sh pi:/tmp/vps_deploy_commands.sh

# Execute deployment through pi
echo "🎯 Executing deployment on VPS through pi..."
ssh pi "chmod +x /tmp/vps_deploy_commands.sh && scp /tmp/monitor_fixed.py linuxuser@45.77.40.77:/tmp/ && scp /tmp/vps_deploy_commands.sh linuxuser@45.77.40.77:/tmp/ && ssh linuxuser@45.77.40.77 'chmod +x /tmp/vps_deploy_commands.sh && /tmp/vps_deploy_commands.sh'"

echo "✅ Deployment complete!"