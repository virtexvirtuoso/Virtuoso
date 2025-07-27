#!/bin/bash

echo "📱 Updating Alert Persistence on VPS"
echo "==================================="

# VPS connection details
VPS_IP="45.77.40.77"
VPS_USER="linuxuser"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Files to transfer
FILES=(
    "src/database/alert_storage.py"
    "src/database/__init__.py"
    "src/monitoring/alert_manager.py"
    "src/dashboard/templates/dashboard_mobile_v1.html"
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
echo "📝 Next steps on VPS:"
echo "1. SSH to VPS: ssh $VPS_USER@$VPS_IP"
echo "2. cd ~/trading/Virtuoso_ccxt"
echo "3. Create data directory if needed:"
echo "   mkdir -p data"
echo "4. Restart the application:"
echo "   screen -r virtuoso"
echo "   Ctrl+C to stop"
echo "   python src/integrated_server.py"
echo ""
echo "5. The alert database will be created automatically at:"
echo "   ~/trading/Virtuoso_ccxt/data/virtuoso.db"
echo ""
echo "6. Access the mobile dashboard to see historical alerts:"
echo "   http://$VPS_IP:8080/dashboard"
echo ""
echo "✅ Alert persistence system deployed!"
echo ""
echo "Features added:"
echo "- All Discord alerts are now stored in SQLite database"
echo "- Mobile dashboard Alerts tab shows historical alerts"
echo "- Alerts persist across application restarts"
echo "- 7-day retention policy (configurable)"