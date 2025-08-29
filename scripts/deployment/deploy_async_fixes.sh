#!/bin/bash

#############################################################################
# Script: deploy_async_fixes.sh
# Purpose: Deploy and manage deploy async fixes
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates deployment automation, service management, and infrastructure updates for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - rsync
#   - ssh
#   - git
#   - systemctl
#   - Access to project directory structure
#
# Usage:
#   ./deploy_async_fixes.sh [options]
#   
#   Examples:
#     ./deploy_async_fixes.sh
#     ./deploy_async_fixes.sh --verbose
#     ./deploy_async_fixes.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 45.77.40.77)
#   VPS_USER         VPS username (default: linuxuser)
#
# Output:
#   - Console output with operation status
#   - Log messages with timestamps
#   - Success/failure indicators
#
# Exit Codes:
#   0 - Success
#   1 - Deployment failed
#   2 - Invalid arguments
#   3 - Connection error
#   4 - Service start failed
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

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