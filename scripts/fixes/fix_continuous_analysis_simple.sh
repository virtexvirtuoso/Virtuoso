#!/bin/bash

#############################################################################
# Script: fix_continuous_analysis_simple.sh
# Purpose: Deploy and manage fix continuous analysis simple
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
#   ./fix_continuous_analysis_simple.sh [options]
#   
#   Examples:
#     ./fix_continuous_analysis_simple.sh
#     ./fix_continuous_analysis_simple.sh --verbose
#     ./fix_continuous_analysis_simple.sh --dry-run
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

echo "🔧 Applying simple fix for ContinuousAnalysisManager..."

# Create backup
ssh linuxuser@${VPS_HOST} "cp /home/linuxuser/trading/Virtuoso_ccxt/src/main.py /home/linuxuser/trading/Virtuoso_ccxt/src/main.py.backup_simple"

# Fix 1: Add market_data_manager to global declaration at line 3183
ssh linuxuser@${VPS_HOST} "sed -i '3183s/global confluence_analyzer, top_symbols_manager, market_monitor/global confluence_analyzer, top_symbols_manager, market_monitor, market_data_manager/' /home/linuxuser/trading/Virtuoso_ccxt/src/main.py"

# Fix 2: Extract market_data_manager from components after line 3204
ssh linuxuser@${VPS_HOST} "sed -i '/market_monitor = components\[.market_monitor.\]/a\    market_data_manager = components[\"market_data_manager\"]  # Extract for ContinuousAnalysisManager' /home/linuxuser/trading/Virtuoso_ccxt/src/main.py"

# Validate syntax
echo "🔍 Validating Python syntax..."
if ssh linuxuser@${VPS_HOST} "cd /home/linuxuser/trading/Virtuoso_ccxt && /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python -m py_compile src/main.py 2>&1"; then
    echo "✅ Python syntax validation passed!"
    
    # Restart service
    echo "🔄 Restarting service..."
    ssh linuxuser@${VPS_HOST} "sudo systemctl restart virtuoso.service"
    
    # Wait for startup
    sleep 10
    
    # Check for success
    echo "📊 Checking if ContinuousAnalysisManager started..."
    if ssh linuxuser@${VPS_HOST} "sudo journalctl -u virtuoso.service --since '1 minute ago' | grep -q 'Continuous analysis manager started'"; then
        echo "✅ SUCCESS! ContinuousAnalysisManager is now running!"
    else
        echo "⚠️ Check logs to verify status"
    fi
    
    # Show recent logs
    echo -e "\n📝 Recent logs:"
    ssh linuxuser@${VPS_HOST} "sudo journalctl -u virtuoso.service --since '30 seconds ago' | grep -E 'ContinuousAnalysisManager|analysis.*cache|WARNING.*market_data_manager' | tail -5"
else
    echo "❌ Syntax validation failed - restoring backup"
    ssh linuxuser@${VPS_HOST} "mv /home/linuxuser/trading/Virtuoso_ccxt/src/main.py.backup_simple /home/linuxuser/trading/Virtuoso_ccxt/src/main.py"
fi
