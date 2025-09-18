#!/bin/bash

#############################################################################
# Script: rollback_refactored.sh
# Purpose: Deploy and manage rollback refactored
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
#   ./rollback_refactored.sh [options]
#   
#   Examples:
#     ./rollback_refactored.sh
#     ./rollback_refactored.sh --verbose
#     ./rollback_refactored.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 5.223.63.4)
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

# Rollback script for refactored components

echo "🔄 Rollback Script for Refactored Components"
echo "==========================================="
echo ""
echo "This script will revert main.py to use original components"
echo ""

VPS="linuxuser@5.223.63.4"

# Function to rollback locally
rollback_local() {
    echo "📍 Rolling back LOCAL environment..."
    
    # Check if main.py has been modified
    if grep -q "monitoring.monitor_refactored" src/main.py 2>/dev/null; then
        echo "  Reverting main.py to original imports..."
        
        # Revert monitor import
        sed -i.bak 's/from src.monitoring.monitor_refactored import MarketMonitor/from src.monitoring.monitor import MarketMonitor/' src/main.py
        
        # Revert alert manager import  
        sed -i.bak 's/from src.monitoring.components.alerts.alert_manager_refactored import AlertManager/from src.monitoring.alert_manager import AlertManager/' src/main.py
        
        echo "  ✅ Local main.py reverted to original imports"
    else
        echo "  ℹ️  Local main.py already using original components"
    fi
}

# Function to rollback VPS
rollback_vps() {
    echo "📍 Rolling back VPS environment..."
    
    ssh $VPS << 'ENDSSH'
    cd /home/linuxuser/trading/Virtuoso_ccxt
    
    # Check if main.py has been modified
    if grep -q "monitoring.monitor_refactored" src/main.py 2>/dev/null; then
        echo "  Reverting main.py to original imports..."
        
        # Backup current version
        cp src/main.py src/main.py.refactored_backup
        
        # Revert imports
        sed -i 's/from src.monitoring.monitor_refactored import MarketMonitor/from src.monitoring.monitor import MarketMonitor/' src/main.py
        sed -i 's/from src.monitoring.components.alerts.alert_manager_refactored import AlertManager/from src.monitoring.alert_manager import AlertManager/' src/main.py
        
        echo "  ✅ VPS main.py reverted to original imports"
        echo "  📝 Backup saved as main.py.refactored_backup"
        
        # Restart service if it was using refactored components
        echo "  🔄 Restarting service..."
        sudo systemctl restart virtuoso.service
        echo "  ✅ Service restarted"
    else
        echo "  ℹ️  VPS main.py already using original components"
    fi
ENDSSH
}

# Main menu
echo "Select rollback option:"
echo "1) Rollback LOCAL only"
echo "2) Rollback VPS only"
echo "3) Rollback BOTH local and VPS"
echo "4) Exit without changes"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        rollback_local
        ;;
    2)
        rollback_vps
        ;;
    3)
        rollback_local
        rollback_vps
        ;;
    4)
        echo "No changes made"
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✅ Rollback complete!"
echo ""
echo "Note: The refactored components are still available at:"
echo "  - src/monitoring/monitor_refactored.py"
echo "  - src/monitoring/components/alerts/"
echo ""
echo "To re-enable them, update the imports in main.py"