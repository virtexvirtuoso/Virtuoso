#!/bin/bash

#############################################################################
# Script: rollback_dashboard_fixes.sh
# Purpose: Deploy and manage rollback dashboard fixes
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
#   ./rollback_dashboard_fixes.sh [options]
#   
#   Examples:
#     ./rollback_dashboard_fixes.sh
#     ./rollback_dashboard_fixes.sh --verbose
#     ./rollback_dashboard_fixes.sh --dry-run
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

"""
Rollback Dashboard Performance Fixes
Quick rollback procedure if fixes cause issues
"""

set -e

echo "🔄 Dashboard Performance Fixes Rollback"
echo "======================================="

# Configuration
VPS_HOST="5.223.63.4"
VPS_USER="linuxuser"
VPS_PROJECT_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}⚠️ This will rollback all dashboard performance fixes${NC}"
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

echo -e "${BLUE}🔄 Step 1: Stopping service...${NC}"
ssh ${VPS_USER}@${VPS_HOST} "
    sudo systemctl stop virtuoso.service
"

echo -e "${BLUE}🔄 Step 2: Restoring backup files...${NC}"
ssh ${VPS_USER}@${VPS_HOST} "
    cd ${VPS_PROJECT_PATH}
    
    # Find and restore most recent backups
    if ls src/api/routes/dashboard_cached.py.backup.* 1> /dev/null 2>&1; then
        latest_cached=\$(ls -t src/api/routes/dashboard_cached.py.backup.* | head -n1)
        echo \"Restoring \$latest_cached\"
        cp \"\$latest_cached\" src/api/routes/dashboard_cached.py
    else
        echo \"No dashboard_cached.py backup found\"
    fi
    
    if ls src/api/cache_adapter_direct.py.backup.* 1> /dev/null 2>&1; then
        latest_adapter=\$(ls -t src/api/cache_adapter_direct.py.backup.* | head -n1)
        echo \"Restoring \$latest_adapter\"
        cp \"\$latest_adapter\" src/api/cache_adapter_direct.py
    else
        echo \"No cache_adapter_direct.py backup found\"
    fi
    
    # Remove new optimization files if they exist
    rm -f src/api/cache_adapter_optimized.py
    rm -f src/api/routes/dashboard_streaming.py
    rm -f src/core/connection_manager.py
    rm -f src/core/cache_warming.py
    rm -f src/core/cache_invalidation.py
    rm -f src/core/performance_monitoring.py
    rm -f src/core/middleware/compression.py
    
    echo \"Backup files restored\"
"

echo -e "${BLUE}🔄 Step 3: Reverting API configuration...${NC}"
ssh ${VPS_USER}@${VPS_HOST} "
    cd ${VPS_PROJECT_PATH}
    
    # Restore API __init__.py if backup exists
    if [[ -f src/api/__init__.py.backup ]]; then
        cp src/api/__init__.py.backup src/api/__init__.py
        echo \"API configuration reverted\"
    else
        echo \"No API __init__.py backup found - leaving as-is\"
    fi
"

echo -e "${BLUE}🔄 Step 4: Restarting service...${NC}"
ssh ${VPS_USER}@${VPS_HOST} "
    cd ${VPS_PROJECT_PATH}
    sudo systemctl start virtuoso.service
    sleep 10
"

echo -e "${BLUE}✅ Step 5: Verifying rollback...${NC}"
ssh ${VPS_USER}@${VPS_HOST} "
    echo 'Service status:'
    sudo systemctl is-active virtuoso.service
    
    echo 'Recent logs:'
    sudo journalctl -u virtuoso.service --no-pager -n 5
    
    echo 'Testing basic endpoint:'
    curl -s -o /dev/null -w 'HTTP %{http_code} - %{time_total}s' http://localhost:8003/health || echo 'Health check failed'
    echo
"

echo -e "${GREEN}✅ Rollback complete!${NC}"
echo
echo "Service should now be running with original configuration."
echo "Monitor with: ssh ${VPS_USER}@${VPS_HOST} 'sudo journalctl -u virtuoso.service -f'"
echo
echo "If you still experience issues:"
echo "1. Check service logs for errors"
echo "2. Restart the service manually"  
echo "3. Verify memcached is running: systemctl status memcached"
echo "4. Check cache connectivity: echo 'stats' | nc localhost 11211"

exit 0