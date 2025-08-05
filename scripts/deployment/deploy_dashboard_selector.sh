#!/bin/bash

echo "📱 Deploying Dashboard Selector to VPS"
echo "====================================="

# VPS connection details
VPS_IP="45.77.40.77"
VPS_USER="linuxuser"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Files to transfer
FILES=(
    "src/dashboard/templates/dashboard_selector.html"
    "src/web_server.py"
)

echo "📤 Transferring updated files to VPS..."
echo ""

# Transfer each file
for FILE in "${FILES[@]}"; do
    LOCAL_FILE="$PROJECT_ROOT/$FILE"
    REMOTE_PATH="~/trading/Virtuoso_ccxt/$FILE"
    
    if [ -f "$LOCAL_FILE" ]; then
        echo "Copying $FILE..."
        # Create directory if needed
        REMOTE_DIR=$(dirname "$REMOTE_PATH")
        ssh "$VPS_USER@$VPS_IP" "mkdir -p $REMOTE_DIR"
        
        # Copy file
        scp "$LOCAL_FILE" "$VPS_USER@$VPS_IP:$REMOTE_PATH"
        
        if [ $? -eq 0 ]; then
            echo "✅ $FILE transferred successfully"
        else
            echo "❌ Failed to transfer $FILE"
        fi
    else
        echo "❌ File not found: $FILE"
    fi
    echo ""
done

echo ""
echo "🔄 Restarting application..."
ssh "$VPS_USER@$VPS_IP" "screen -S virtuoso -X quit; sleep 2; cd ~/trading/Virtuoso_ccxt && screen -dmS virtuoso python src/integrated_server.py && echo 'Application restarted'"

echo ""
echo "✅ Dashboard selector deployed!"
echo ""
echo "📱 Access Options:"
echo "1. Main selector: http://$VPS_IP:8003/dashboard"
echo "2. Direct mobile: http://$VPS_IP:8003/dashboard/mobile (with ₿ Beta tab)"
echo "3. Direct desktop: http://$VPS_IP:8003/dashboard/desktop"
echo ""
echo "Features:"
echo "- Auto-detects mobile devices"
echo "- Remembers user preference"
echo "- Clear descriptions of each dashboard"
echo "- Clean, intuitive interface"