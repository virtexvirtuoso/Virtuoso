#!/bin/bash

# Quick deployment script - updates only dashboard files

REMOTE_USER="linuxuser"
REMOTE_HOST="45.77.40.77"
REMOTE_PATH="/home/linuxuser/trading/virtuoso_ccxt"

echo "🚀 Quick Deploy - Dashboard Update"
echo "Updating dashboard files on ${REMOTE_HOST}..."

# Copy the updated dashboard templates
scp src/dashboard/templates/dashboard_desktop_v1.html ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/src/dashboard/templates/
scp src/dashboard/templates/dashboard_mobile_v1.html ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/src/dashboard/templates/

# Copy the updated web server
scp src/web_server.py ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/src/

# Copy manifest.json
scp src/static/manifest.json ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/src/static/

echo "✅ Files copied successfully"
echo ""
echo "To restart the web server, run:"
echo "ssh ${REMOTE_USER}@${REMOTE_HOST} 'pkill -f web_server.py; cd ${REMOTE_PATH} && source venv/bin/activate && nohup python src/web_server.py > web_server.log 2>&1 &'"