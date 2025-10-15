#!/bin/bash
###############################################################################
# Start Web Server with Environment Variables Loaded
# This script ensures Discord webhooks and other env vars are properly loaded
###############################################################################

set -e  # Exit on error

# Change to project root
cd /home/linuxuser/trading/Virtuoso_ccxt

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(grep -v '^#' .env | xargs)
    echo "✅ Environment variables loaded"
else
    echo "⚠️  No .env file found"
fi

# Verify critical variables are set
echo "Checking environment variables..."
if [ -z "$DISCORD_WEBHOOK_URL" ]; then
    echo "⚠️  DISCORD_WEBHOOK_URL not set"
else
    echo "✅ DISCORD_WEBHOOK_URL is set"
fi

if [ -z "$SYSTEM_ALERTS_WEBHOOK_URL" ]; then
    echo "⚠️  SYSTEM_ALERTS_WEBHOOK_URL not set"
else
    echo "✅ SYSTEM_ALERTS_WEBHOOK_URL is set"
fi

# Stop any existing web server processes
echo "Stopping existing web server processes..."
pkill -f "web_server.py" || true
sleep 3

# Start web server with environment variables
echo "Starting web server..."
nohup ./venv311/bin/python src/web_server.py > logs/web_$(date +%Y%m%d_%H%M%S).log 2>&1 &

sleep 5

# Check if server started
if pgrep -f "web_server.py" > /dev/null; then
    echo "✅ Web server started successfully"
    ps aux | grep "web_server.py" | grep -v grep
else
    echo "❌ Web server failed to start"
    exit 1
fi

echo ""
echo "Check logs: tail -f logs/web_*.log"