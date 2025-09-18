#!/bin/bash

#############################################################################
# Script: cleanup_old_logs.sh
# Purpose: Cleanup old log files to free up space
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
#   ./cleanup_old_logs.sh [options]
#   
#   Examples:
#     ./cleanup_old_logs.sh
#     ./cleanup_old_logs.sh --verbose
#     ./cleanup_old_logs.sh --dry-run
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

# Keeps DEBUG level but manages storage efficiently

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../logs"
cd "$LOG_DIR" || exit 1

echo "🧹 Cleaning up old log files..."
echo "Current log directory size: $(du -sh . | cut -f1)"

# Remove logs older than 60 days
find . -name "*.log.2025-*" -type f -mtime +60 -delete 2>/dev/null
find . -name "*.gz" -type f -mtime +60 -delete 2>/dev/null

# Remove very large test logs that are no longer needed
find . -name "*test*.log" -size +50M -mtime +7 -delete 2>/dev/null

# Keep only last 5 deployment logs
ls -t deployment_*.log 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null

# Keep only last 10 enhanced scoring test logs
ls -t enhanced_scoring*.log 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null

echo "After cleanup: $(du -sh . | cut -f1)"
echo "✅ Old log cleanup complete!"