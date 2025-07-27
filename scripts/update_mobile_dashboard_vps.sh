#!/bin/bash

echo "📱 Updating Mobile Dashboard on VPS"
echo "=================================="

# VPS connection details
VPS_IP="45.77.40.77"
VPS_USER="linuxuser"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_FILE="$SCRIPT_DIR/../src/dashboard/templates/dashboard_mobile_v1.html"
REMOTE_PATH="~/trading/Virtuoso_ccxt/src/dashboard/templates/"

# Check if the file exists
if [ ! -f "$LOCAL_FILE" ]; then
    echo "❌ Error: dashboard_mobile_v1.html not found!"
    echo "Expected at: $LOCAL_FILE"
    exit 1
fi

echo "✅ Found dashboard_mobile_v1.html"
echo ""

# Method 1: Direct file copy (fastest for single file)
echo "📤 Transferring updated mobile dashboard to VPS..."
echo ""
echo "Using SCP to copy the file:"
echo "scp $LOCAL_FILE $VPS_USER@$VPS_IP:$REMOTE_PATH"
echo ""

# Execute the transfer
scp "$LOCAL_FILE" "$VPS_USER@$VPS_IP:$REMOTE_PATH"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully updated mobile dashboard on VPS!"
    echo ""
    echo "📝 Next steps:"
    echo "1. SSH to VPS: ssh $VPS_USER@$VPS_IP"
    echo "2. Restart the application (if needed):"
    echo "   cd ~/trading/Virtuoso_ccxt"
    echo "   sudo systemctl restart virtuoso"
    echo ""
    echo "3. Or if using screen:"
    echo "   screen -r virtuoso"
    echo "   Ctrl+C to stop"
    echo "   python src/integrated_server.py"
    echo ""
    echo "4. Access the mobile dashboard:"
    echo "   http://$VPS_IP:8080/dashboard"
else
    echo ""
    echo "❌ Failed to transfer file to VPS"
    echo "Please check your SSH connection and try again"
    exit 1
fi

# Optional: Also update via rsync (preserves permissions)
echo "Alternative method using rsync:"
echo "rsync -avzP $LOCAL_FILE $VPS_USER@$VPS_IP:$REMOTE_PATH"