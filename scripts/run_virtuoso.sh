#!/bin/bash

#############################################################################
# Script: run_virtuoso.sh
# Purpose: Deploy and manage run virtuoso
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
#   ./run_virtuoso.sh [options]
#   
#   Examples:
#     ./run_virtuoso.sh
#     ./run_virtuoso.sh --verbose
#     ./run_virtuoso.sh --dry-run
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

# Change to the project directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv311/bin/activate

# Source environment variables for InfluxDB if the script exists
if [ -f "scripts/set_influxdb_env.sh" ]; then
    echo "Sourcing InfluxDB environment variables..."
    source scripts/set_influxdb_env.sh
else
    echo "InfluxDB environment setup script not found, skipping."
fi

# Ensure templates are up-to-date
if [ -f "scripts/ensure_templates.py" ]; then
    echo "Ensuring templates are up-to-date..."
    python scripts/ensure_templates.py
else
    echo "Template ensure script not found, skipping."
fi

# Note: Matplotlib logs are now silenced automatically in src/__init__.py
# when the application starts, so we don't need the PYTHONCODE export anymore

# Run the application from the project root directory
python -m src.main "$@" 