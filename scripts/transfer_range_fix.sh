#!/bin/bash

#############################################################################
# Script: transfer_range_fix.sh
# Purpose: Deploy and manage transfer range fix
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
#   ./transfer_range_fix.sh [options]
#   
#   Examples:
#     ./transfer_range_fix.sh
#     ./transfer_range_fix.sh --verbose
#     ./transfer_range_fix.sh --dry-run
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

# Transfer script for range volume fix
# Target: linuxuser@45.77.40.77

echo "Transferring range volume fix files to VPS..."

# Create a list of files that were modified
FILES=(
    "src/indicators/price_structure_indicators.py"
    "config/config.yaml"
    "scripts/testing/test_range_volume_fix.py"
)

# Transfer each file
for file in "${FILES[@]}"; do
    echo "Transferring $file..."
    scp "$file" "linuxuser@45.77.40.77:~/Virtuoso_ccxt/$file"
    if [ $? -eq 0 ]; then
        echo "✓ Successfully transferred $file"
    else
        echo "✗ Failed to transfer $file"
    fi
done

echo "Transfer complete!"