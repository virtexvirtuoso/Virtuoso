#!/bin/bash
###############################################################################
# Start Main Trading System with Environment Variables Loaded
# This ensures Discord webhooks and alerts work correctly
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

# Stop any existing main.py processes
echo "Stopping existing main.py processes..."
pkill -f "src/main.py" || true
sleep 3

# Start main trading system with environment variables
echo "Starting main trading system..."
nohup ./venv311/bin/python -u src/main.py > logs/main_$(date +%Y%m%d_%H%M%S).log 2>&1 &

sleep 5

# Check if main started
if pgrep -f "src/main.py" > /dev/null; then
    echo "✅ Main trading system started successfully"
    ps aux | grep "src/main.py" | grep -v grep
else
    echo "❌ Main trading system failed to start"
    exit 1
fi

echo ""
echo "📊 Trading system with Discord alerts is now running"
echo "Check logs: tail -f logs/main_*.log | grep -i discord"