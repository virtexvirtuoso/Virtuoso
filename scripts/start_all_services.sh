#!/bin/bash

#############################################################################
# Script: start_all_services.sh
# Purpose: Start all Virtuoso CCXT trading system services
# Author: Virtuoso CCXT Development Team
# Version: 1.1.0
# Created: 2024-08-15
# Modified: 2024-08-28
#############################################################################
#
# Description:
#   Starts all required services for the Virtuoso CCXT trading system:
#   - Web server (Dashboard API) on port 8001
#   - Main trading service (Market monitoring & signal generation)
#   This script ensures clean startup by killing any existing processes
#   and properly initializing the Python virtual environment.
#
# Services Started:
#   1. Web Server (uvicorn) - Port 8001 - Dashboard and API endpoints
#   2. Main Trading Service - Core trading logic and monitoring
#
# Dependencies:
#   - Python 3.11 virtual environment (venv311)
#   - uvicorn for ASGI web server
#   - All Python dependencies in requirements.txt
#
# Usage:
#   ./start_all_services.sh
#   
#   Note: Run from VPS after SSH connection
#   ssh linuxuser@${VPS_HOST}
#   cd /home/linuxuser/trading/Virtuoso_ccxt
#   ./scripts/start_all_services.sh
#
# Process Management:
#   - Kills existing processes to prevent port conflicts
#   - Starts web server in background with nohup
#   - Runs main service in foreground for monitoring
#   - Creates PID tracking for process management
#
# Log Files:
#   - Web server logs: logs/web_server.log
#   - Main service logs: Console output (can be redirected)
#
# Exit Codes:
#   0 - Services started successfully
#   1 - Virtual environment activation failed
#   2 - Web server startup failed
#   3 - Main service startup failed
#
# Notes:
#   - Always check for running processes before starting
#   - Web server starts first and runs in background
#   - Main service runs in foreground for real-time monitoring
#   - Use systemctl for production deployment instead of this script
#
# Troubleshooting:
#   - Port already in use: Check with 'lsof -i:8001' and 'lsof -i:8003'
#   - Virtual environment issues: Recreate with Python 3.11
#   - Service crashes: Check logs/web_server.log for errors
#
#############################################################################

# Start both main service and web server

# Kill any existing processes
pkill -f "python.*main.py" || true
pkill -f "uvicorn.*web_server" || true

# Wait for ports to be released
sleep 2

# Set up environment
cd /home/linuxuser/trading/Virtuoso_ccxt
source venv311/bin/activate

# Create logs directory if not exists
mkdir -p logs

# Start web server in background
echo "Starting web server on port 8001..."
nohup uvicorn src.web_server:app --host 0.0.0.0 --port 8001 > logs/web_server.log 2>&1 &
WEB_PID=$!
echo "Web server PID: $WEB_PID"

# Wait for web server to start
sleep 5

# Start main service (this will run in foreground)
echo "Starting main trading service..."
python -u src/main.py