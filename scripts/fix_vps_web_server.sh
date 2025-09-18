#!/bin/bash

echo "🔧 Fixing web server on Hetzner VPS (${VPS_HOST})..."

# Create a standalone web server script
cat << 'PYEOF' > /tmp/start_web_server_standalone.py
#!/usr/bin/env python3
"""
Standalone web server for Virtuoso CCXT
Runs independently of the main monitoring system
"""
import asyncio
import sys
import os
import logging

# Setup paths
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')
os.chdir('/home/linuxuser/trading/Virtuoso_ccxt')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Import FastAPI app from main
try:
    from src.main import app
    import uvicorn
    logger.info("Successfully imported FastAPI app")
except Exception as e:
    logger.error(f"Failed to import app: {e}")
    sys.exit(1)

async def main():
    """Start the web server"""
    logger.info("🌐 Starting Virtuoso Web Server on port 8003...")
    
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8003,
        log_level="info",
        access_log=True,
        reload=False
    )
    
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Shutting down web server...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWeb server stopped.")
PYEOF

# Deploy to VPS
echo "📤 Deploying to VPS..."
scp /tmp/start_web_server_standalone.py linuxuser@${VPS_HOST}:/tmp/

# Execute on VPS
ssh linuxuser@${VPS_HOST} << 'REMOTE_EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Install the standalone web server
cp /tmp/start_web_server_standalone.py scripts/
chmod +x scripts/start_web_server_standalone.py

# Stop any existing web server
echo "🛑 Stopping existing web servers..."
sudo fuser -k 8003/tcp 2>/dev/null || true
sudo systemctl stop virtuoso-web.service 2>/dev/null || true
sleep 2

# Create systemd service for the web server
echo "📦 Creating systemd service..."
sudo tee /etc/systemd/system/virtuoso-web.service > /dev/null << 'SERVICE'
[Unit]
Description=Virtuoso CCXT Web Server
After=network.target memcached.service redis.service virtuoso.service
Wants=virtuoso.service

[Service]
Type=simple
User=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
Environment="PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt"
ExecStart=/usr/bin/python3 /home/linuxuser/trading/Virtuoso_ccxt/scripts/start_web_server_standalone.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

# Reload systemd and start the service
echo "🚀 Starting web server service..."
sudo systemctl daemon-reload
sudo systemctl enable virtuoso-web.service
sudo systemctl start virtuoso-web.service

# Wait for startup
sleep 5

# Check status
echo ""
echo "📊 Service Status:"
sudo systemctl status virtuoso-web.service --no-pager | head -15

# Test endpoints
echo ""
echo "🧪 Testing Endpoints:"
echo "1. Health check:"
curl -s -o /dev/null -w "   Status: %{http_code}, Time: %{time_total}s\n" http://localhost:8003/health || echo "   Failed"

echo "2. Main dashboard:"
curl -s -o /dev/null -w "   Status: %{http_code}, Time: %{time_total}s\n" http://localhost:8003/ || echo "   Failed"

echo "3. Dashboard data:"
curl -s http://localhost:8003/api/dashboard/data 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(f'   Success! Keys: {list(d.keys())[:5]}')
except:
    print('   Failed to get data')
" || echo "   Failed"

echo "4. Mobile dashboard:"
curl -s -o /dev/null -w "   Status: %{http_code}, Time: %{time_total}s\n" http://localhost:8003/mobile || echo "   Failed"

# Check listening ports
echo ""
echo "🔍 Listening Ports:"
sudo netstat -tlnp | grep -E "8003|8001" || echo "No web ports listening"

# Show recent logs
echo ""
echo "📋 Recent Web Server Logs:"
sudo journalctl -u virtuoso-web.service --no-pager -n 20 | tail -15
REMOTE_EOF

echo ""
echo "✅ Fix deployed! Testing external access..."
echo ""
echo "🌐 Dashboard URLs:"
echo "   Desktop: http://${VPS_HOST}:8003/"
echo "   Mobile:  http://${VPS_HOST}:8003/mobile"
echo ""
echo "Testing external health check..."
curl -s -o /dev/null -w "External Status: %{http_code}\n" http://${VPS_HOST}:8003/health
