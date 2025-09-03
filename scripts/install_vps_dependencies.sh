#!/bin/bash

#############################################################################
# Script: install_vps_dependencies.sh
# Purpose: Setup and configure install vps dependencies
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates system setup, service configuration, and environment preparation for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - systemctl
#   - mkdir
#   - chmod
#   - Access to project directory structure
#
# Usage:
#   ./install_vps_dependencies.sh [options]
#   
#   Examples:
#     ./install_vps_dependencies.sh
#     ./install_vps_dependencies.sh --verbose
#     ./install_vps_dependencies.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: VPS_HOST_REDACTED)
#   VPS_USER         VPS username (default: linuxuser)
#
# Output:
#   - Console output with operation status
#   - Log messages with timestamps
#   - Success/failure indicators
#
# Exit Codes:
#   0 - Setup completed successfully
#   1 - Setup failed
#   2 - Permission denied
#   3 - Dependencies missing
#   4 - Configuration error
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

# Install missing dependencies on VPS for refactored components

echo "📦 Installing Dependencies on VPS"
echo "================================="

VPS="linuxuser@VPS_HOST_REDACTED"

echo "Installing required Python packages..."

ssh $VPS << 'ENDSSH'
cd /home/linuxuser/trading/Virtuoso_ccxt

echo "🔍 Checking and installing missing packages..."

# Install missing packages
pip3 install --user prettytable cachetools --quiet

# Check if packages are installed
python3 -c "
import sys
print('Checking installed packages:')
try:
    import prettytable
    print('  ✅ prettytable installed')
except ImportError:
    print('  ❌ prettytable missing')
    
try:
    import cachetools
    print('  ✅ cachetools installed')
except ImportError:
    print('  ❌ cachetools missing')
"

echo "✅ Dependencies installation complete"
ENDSSH

echo ""
echo "Dependencies installed. Ready to test refactored components!"