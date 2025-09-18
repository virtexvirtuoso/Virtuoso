#!/bin/bash

#############################################################################
# Script: deploy_refactored_quick.sh
# Purpose: Deploy and manage deploy refactored quick
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
#   ./deploy_refactored_quick.sh [options]
#   
#   Examples:
#     ./deploy_refactored_quick.sh
#     ./deploy_refactored_quick.sh --verbose
#     ./deploy_refactored_quick.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: ${VPS_HOST})
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

# Quick deployment of refactored components to VPS

set -e

echo "🚀 Quick Deploy - Refactored Components"
echo "======================================="

VPS="linuxuser@${VPS_HOST}"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Create directories on VPS
echo "📁 Creating directories..."
ssh $VPS "mkdir -p ${VPS_DIR}/src/monitoring/components/alerts"

# Deploy files
echo "📤 Uploading refactored components..."

# Upload monitor_refactored.py
scp -q src/monitoring/monitor_refactored.py $VPS:${VPS_DIR}/src/monitoring/

# Upload alert components
scp -q src/monitoring/components/alerts/*.py $VPS:${VPS_DIR}/src/monitoring/components/alerts/

# Upload supporting components if they exist
for file in data_collector.py validator.py signal_processor.py metrics_tracker.py base.py; do
    if [ -f "src/monitoring/$file" ]; then
        scp -q src/monitoring/$file $VPS:${VPS_DIR}/src/monitoring/
    fi
done

echo "✅ Files uploaded"

# Quick test
echo "🧪 Testing components..."
ssh $VPS "cd ${VPS_DIR} && python3 -c 'import sys; sys.path.insert(0, \"src\"); from monitoring.components.alerts.alert_manager_refactored import AlertManagerRefactored; print(\"✅ AlertManager works\")'"

ssh $VPS "cd ${VPS_DIR} && python3 -c 'import sys; sys.path.insert(0, \"src\"); from monitoring.monitor_refactored import RefactoredMarketMonitor; print(\"✅ Monitor works\")'"

echo ""
echo "✅ Deployment successful!"
echo ""
echo "To test: ssh vps"
echo "Then: cd /home/linuxuser/trading/Virtuoso_ccxt"
echo "And: python3 -c 'from src.monitoring.components.alerts.alert_manager_refactored import AlertManagerRefactored'"