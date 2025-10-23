#!/bin/bash

# Deploy critical WebSocket connection fix to VPS
# This fixes the bug where _handle_messages() was receiving an unexpected 'name' parameter

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VPS_USER="linuxuser"
VPS_HOST="${VPS_HOST:-5.223.63.4}"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo "================================================================"
echo "🚀 Deploying Critical WebSocket Fix to VPS"
echo "================================================================"
echo ""
echo "This fixes: WebSocketManager._handle_messages() got an unexpected keyword argument 'name'"
echo ""

# Step 1: Verify local fix
echo "Step 1: Verifying local fix..."
cd "$PROJECT_ROOT"

if ! grep -q 'self._handle_messages(ws, topics, connection_id, session),' src/core/exchanges/websocket_manager.py; then
    echo "❌ ERROR: Local fix not found in websocket_manager.py"
    echo "Expected: self._handle_messages(ws, topics, connection_id, session),"
    exit 1
fi

if grep -q 'self._handle_messages(ws, topics, connection_id, session, name=' src/core/exchanges/websocket_manager.py; then
    echo "❌ ERROR: Bug still present in websocket_manager.py"
    echo "Found: name= parameter incorrectly passed to _handle_messages()"
    exit 1
fi

echo "✅ Local fix verified"
echo ""

# Step 2: Create backup on VPS
echo "Step 2: Creating backup on VPS..."
ssh ${VPS_USER}@${VPS_HOST} "cd ${VPS_PATH} && \
    mkdir -p backups && \
    cp src/core/exchanges/websocket_manager.py backups/websocket_manager.py.backup_$(date +%Y%m%d_%H%M%S) && \
    echo '✅ Backup created'"
echo ""

# Step 3: Deploy fix to VPS
echo "Step 3: Deploying fix to VPS..."
rsync -avz --progress \
    src/core/exchanges/websocket_manager.py \
    ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/core/exchanges/

echo "✅ Fix deployed to VPS"
echo ""

# Step 4: Verify deployment
echo "Step 4: Verifying deployment on VPS..."
ssh ${VPS_USER}@${VPS_HOST} "cd ${VPS_PATH} && \
    if grep -q 'self._handle_messages(ws, topics, connection_id, session, name=' src/core/exchanges/websocket_manager.py; then \
        echo '❌ ERROR: Bug still present on VPS'; \
        exit 1; \
    else \
        echo '✅ Fix verified on VPS'; \
    fi"
echo ""

# Step 5: Restart service
echo "Step 5: Restarting Virtuoso service..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl restart virtuoso"
echo "✅ Service restarted"
echo ""

# Step 6: Monitor service startup
echo "Step 6: Monitoring service startup (20 seconds)..."
sleep 5
echo "Checking service status..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl status virtuoso --no-pager -l | head -20"
echo ""

echo "Checking for WebSocket connection success in logs..."
sleep 10
ssh ${VPS_USER}@${VPS_HOST} "sudo journalctl -u virtuoso -n 50 --no-pager | grep -i 'websocket' | tail -10"
echo ""

# Step 7: Final verification
echo "Step 7: Final verification..."
echo "Checking for WebSocket errors in the last 30 seconds..."
ssh ${VPS_USER}@${VPS_HOST} "sudo journalctl -u virtuoso --since '30 seconds ago' --no-pager | grep -i 'unexpected keyword argument' || echo '✅ No WebSocket parameter errors found'"
echo ""

echo "================================================================"
echo "✅ Deployment Complete!"
echo "================================================================"
echo ""
echo "What was fixed:"
echo "  - Removed incorrect 'name' parameter from _handle_messages() call"
echo "  - WebSocket connections should now establish successfully"
echo "  - All 10 connections should be active"
echo ""
echo "Next steps:"
echo "  1. Monitor logs: ssh vps 'sudo journalctl -u virtuoso -f'"
echo "  2. Verify connections: Check for 'Successfully connected to X WebSocket endpoints'"
echo "  3. Check for errors: Look for any 'unexpected keyword argument' messages"
echo ""
