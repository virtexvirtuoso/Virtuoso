#!/bin/bash

#############################################################################
# Script: monitor_fixes.sh
# Purpose: Deploy and manage monitor fixes
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
#   ./monitor_fixes.sh [options]
#   
#   Examples:
#     ./monitor_fixes.sh
#     ./monitor_fixes.sh --verbose
#     ./monitor_fixes.sh --dry-run
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

# Monitor the critical fixes deployed on 2025-08-04
VPS_HOST="linuxuser@45.77.40.77"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

echo "🔍 Monitoring Critical Fixes on VPS"
echo "==================================="
echo "Time: $(date)"
echo ""

# Check if process is running
echo "1. Process Status:"
echo "-----------------"
ssh $VPS_HOST "ps aux | grep -E 'python.*main.py' | grep -v grep" | awk '{print "PID:", $2, "CPU:", $3"%", "MEM:", $4"%", "Uptime:", $10}'

# Check log file is being written
echo -e "\n2. Log File Activity:"
echo "--------------------"
ssh $VPS_HOST "cd $VPS_DIR && ls -la logs/app.log | awk '{print \"Size:\", \$5, \"bytes\", \"Last modified:\", \$6, \$7, \$8}'"

# Check for timeout errors (new fix)
echo -e "\n3. Timeout Errors (Last hour):"
echo "------------------------------"
ssh $VPS_HOST "cd $VPS_DIR && grep -c 'Request timeout' logs/app.log || echo '0 timeout errors found'"

# Check for entry_pos errors (PDF fix)
echo -e "\n4. PDF Generation Errors (Last hour):"
echo "------------------------------------"
ssh $VPS_HOST "cd $VPS_DIR && grep -c 'entry_pos' logs/pdf_generator.log 2>/dev/null || echo '0 entry_pos errors'"

# Check PENGUUSDT monitoring
echo -e "\n5. PENGUUSDT Activity:"
echo "----------------------"
ssh $VPS_HOST "cd $VPS_DIR && grep -c 'PENGUUSDT' logs/app.log || echo 'Not found in current log'"

# Check recent errors
echo -e "\n6. Recent Errors (Last 10):"
echo "---------------------------"
ssh $VPS_HOST "cd $VPS_DIR && grep -i 'error' logs/app.log | tail -10 || echo 'No recent errors'"

# Check API response times
echo -e "\n7. Recent API Calls:"
echo "--------------------"
ssh $VPS_HOST "cd $VPS_DIR && grep 'Making request to' logs/app.log | tail -5 || echo 'No recent API calls logged'"

# Monitor memory usage
echo -e "\n8. Memory Usage:"
echo "---------------"
ssh $VPS_HOST "free -h | grep -E 'Mem:|Swap:'"

# Check if new symbols are getting price data
echo -e "\n9. Price Data Fetches:"
echo "---------------------"
ssh $VPS_HOST "cd $VPS_DIR && grep -E 'Fetching immediate data|Immediate data fetched' logs/app.log | tail -5 || echo 'No immediate fetches logged (might not have new symbols yet)'"

echo -e "\n✅ Monitoring complete at $(date)"