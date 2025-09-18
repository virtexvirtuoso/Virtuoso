#!/bin/bash

# Deploy data structure fixes to VPS
# Fixes field name inconsistencies and missing fields in confluence breakdown

set -e

echo "======================================"
echo "🔧 DEPLOYING DATA STRUCTURE FIXES"
echo "======================================"
echo ""

# Configuration
VPS_HOST="linuxuser@${VPS_HOST}"
REMOTE_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_PATH="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

echo "📋 Summary of fixes being deployed:"
echo "1. Fixed field name inconsistencies (price_change_24h → change_24h)"
echo "2. Added backward compatibility for field names"
echo "3. Added missing fields to confluence breakdown (price, change_24h, volume_24h)"
echo "4. Ensured market breadth calculations work correctly"
echo ""

# Files to deploy
FILES_TO_DEPLOY=(
    "src/main.py"
    "src/dashboard/dashboard_integration.py"
    "scripts/validate_data_structure_fixes.py"
)

echo "📦 Files to deploy:"
for file in "${FILES_TO_DEPLOY[@]}"; do
    echo "  - $file"
done
echo ""

# Copy files to VPS
echo "📤 Copying files to VPS..."
for file in "${FILES_TO_DEPLOY[@]}"; do
    echo "  Copying $file..."
    scp "$LOCAL_PATH/$file" "$VPS_HOST:$REMOTE_PATH/$file"
done

echo ""
echo "🔄 Restarting services on VPS..."

# Restart the service
ssh $VPS_HOST << 'EOF'
    cd /home/linuxuser/trading/Virtuoso_ccxt
    
    # Stop the service
    echo "Stopping virtuoso service..."
    sudo systemctl stop virtuoso.service || true
    
    # Clear cache to ensure fresh data with new structure
    echo "Clearing cache..."
    echo 'flush_all' | nc localhost 11211 || true
    
    # Start the service
    echo "Starting virtuoso service..."
    sudo systemctl start virtuoso.service
    
    # Wait for service to initialize
    sleep 5
    
    # Check service status
    echo ""
    echo "Service status:"
    sudo systemctl status virtuoso.service --no-pager | head -20
    
    echo ""
    echo "Waiting for cache to populate..."
    sleep 10
EOF

echo ""
echo "🧪 Running validation on VPS..."

# Run validation script on VPS
ssh $VPS_HOST << 'EOF'
    cd /home/linuxuser/trading/Virtuoso_ccxt
    
    # Make validation script executable
    chmod +x scripts/validate_data_structure_fixes.py
    
    # Run validation
    python3 scripts/validate_data_structure_fixes.py
EOF

echo ""
echo "======================================"
echo "✅ DEPLOYMENT COMPLETE"
echo "======================================"
echo ""
echo "📊 Next steps:"
echo "1. Monitor the dashboard at http://${VPS_HOST}:8003/"
echo "2. Check mobile dashboard at http://${VPS_HOST}:8003/mobile"
echo "3. Verify market breadth calculations are working"
echo "4. Check confluence scores include price data"
echo ""
echo "🔍 To check logs:"
echo "  ssh $VPS_HOST"
echo "  sudo journalctl -u virtuoso.service -f"
echo ""
echo "📈 To verify API responses:"
echo "  curl http://${VPS_HOST}:8003/api/dashboard/mobile | jq '.confluence_scores[0]'"
echo ""