#!/bin/bash

# Deploy async cleanup fixes to VPS
# Usage: ./deploy_async_fixes.sh

VPS_HOST="45.77.40.77"
VPS_USER="linuxuser"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo "🚀 Deploying async cleanup fixes to VPS..."

# Function to upload a file
upload_file() {
    local_file="$1"
    remote_path="$2"
    
    echo "📤 Uploading $local_file..."
    scp "$local_file" "$VPS_USER@$VPS_HOST:$remote_path"
    
    if [ $? -eq 0 ]; then
        echo "✅ Successfully uploaded $local_file"
    else
        echo "❌ Failed to upload $local_file"
        exit 1
    fi
}

# Create backup directory on VPS
echo "📁 Creating backup directory on VPS..."
ssh "$VPS_USER@$VPS_HOST" "mkdir -p $VPS_PATH/backups/pre_async_fix_$(date +%Y%m%d_%H%M%S)"

# Backup original files on VPS
echo "💾 Creating backups of original files..."
ssh "$VPS_USER@$VPS_HOST" "
    cd $VPS_PATH
    cp src/main.py backups/pre_async_fix_$(date +%Y%m%d_%H%M%S)/main.py.backup
    cp src/dashboard/dashboard_integration.py backups/pre_async_fix_$(date +%Y%m%d_%H%M%S)/dashboard_integration.py.backup
    cp src/core/exchanges/bybit.py backups/pre_async_fix_$(date +%Y%m%d_%H%M%S)/bybit.py.backup
    echo 'Backup completed'
"

# Upload the fixed files
echo "🔧 Uploading fixed files..."

# Upload main.py with async cleanup fixes
upload_file "src/main.py" "$VPS_PATH/src/main.py"

# Upload dashboard_integration.py with cancellation handling
upload_file "src/dashboard/dashboard_integration.py" "$VPS_PATH/src/dashboard/dashboard_integration.py"

# Upload bybit.py with GeneratorExit handling
upload_file "src/core/exchanges/bybit.py" "$VPS_PATH/src/core/exchanges/bybit.py"

# Upload the fix documentation
echo "📋 Uploading fix documentation..."
ssh "$VPS_USER@$VPS_HOST" "mkdir -p $VPS_PATH/docs/fixes"
upload_file "docs/fixes/async_shutdown_cleanup_fix.md" "$VPS_PATH/docs/fixes/async_shutdown_cleanup_fix.md"

# Set proper permissions
echo "🔑 Setting proper permissions..."
ssh "$VPS_USER@$VPS_HOST" "
    cd $VPS_PATH
    chmod 644 src/main.py
    chmod 644 src/dashboard/dashboard_integration.py
    chmod 644 src/core/exchanges/bybit.py
    chmod 644 docs/fixes/async_shutdown_cleanup_fix.md
    echo 'Permissions set'
"

# Restart the service
echo "🔄 Restarting Virtuoso trading service..."
ssh "$VPS_USER@$VPS_HOST" "
    sudo systemctl stop virtuoso
    sleep 2
    sudo systemctl start virtuoso
    echo 'Service restarted'
"

# Check service status
echo "🔍 Checking service status..."
ssh "$VPS_USER@$VPS_HOST" "
    sudo systemctl status virtuoso --no-pager -l
    echo ''
    echo 'Recent logs:'
    sudo journalctl -u virtuoso --since '1 minute ago' --no-pager | tail -10
"

echo ""
echo "✅ Deployment completed!"
echo ""
echo "📊 To monitor the service:"
echo "   ssh $VPS_USER@$VPS_HOST"
echo "   sudo journalctl -u virtuoso -f"
echo ""
echo "🛠️  To verify the fixes:"
echo "   sudo systemctl stop virtuoso"
echo "   sudo systemctl start virtuoso"
echo "   # Should show no 'Task was destroyed' or 'GeneratorExit' errors"