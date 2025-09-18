#!/bin/bash

echo "🔧 Simple fix for web server startup..."

# Create a simple Python script to start the web server separately
cat << 'EOF' > /tmp/start_web_server.py
#!/usr/bin/env python3
"""
Simple script to start the web server on port 8003
This runs independently of the main monitoring system
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')
os.chdir('/home/linuxuser/trading/Virtuoso_ccxt')

# Import required modules
from src.web_server import app
import uvicorn

async def main():
    print("🌐 Starting web server on port 8003...")
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8003,
        log_level="info",
        access_log=True
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
EOF

# Deploy to VPS
echo "📤 Deploying to VPS..."
scp /tmp/start_web_server.py linuxuser@5.223.63.4:/tmp/

ssh linuxuser@5.223.63.4 << 'REMOTE_EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Kill any existing process on port 8003
sudo fuser -k 8003/tcp 2>/dev/null || true

# Copy the web server starter
cp /tmp/start_web_server.py scripts/start_web_server.py
chmod +x scripts/start_web_server.py

# Start web server in background with nohup
echo "🚀 Starting web server..."
nohup python3 scripts/start_web_server.py > /tmp/web_server.log 2>&1 &
WEB_PID=$!

echo "Web server started with PID: $WEB_PID"

# Wait a moment
sleep 3

# Test if it's working
echo ""
echo "🧪 Testing web server..."
echo "Health check:"
curl -s http://localhost:8003/health | head -20 || echo "Failed"

echo ""
echo "Dashboard data:"
curl -s http://localhost:8003/api/dashboard/data | python3 -m json.tool | head -10 || echo "Failed"

echo ""
echo "📋 Web server logs:"
tail -20 /tmp/web_server.log

echo ""
echo "🔍 Listening ports:"
sudo netstat -tlnp | grep 8003
REMOTE_EOF

echo "✅ Done!"