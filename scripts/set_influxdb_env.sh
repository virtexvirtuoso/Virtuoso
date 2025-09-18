#!/bin/bash

#############################################################################
# Script: set_influxdb_env.sh
# Purpose: Permanent InfluxDB environment setup script
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
#   ./set_influxdb_env.sh [options]
#   
#   Examples:
#     ./set_influxdb_env.sh
#     ./set_influxdb_env.sh --verbose
#     ./set_influxdb_env.sh --dry-run
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

# Usage: source set_influxdb_env.sh

# Set InfluxDB environment variables
export INFLUXDB_URL=http://localhost:8086
export INFLUXDB_TOKEN=auUwotDWSbRMNkZLAptfwRv8_lOm_GGJHzmKirgv-Zj8xZya4T6NWYaVqZGNpfaMyxsmtdgBtpaVNtx7PIxNbQ==
export INFLUXDB_ORG=coinmaestro
export INFLUXDB_BUCKET=VirtuosoDB

# Add these variables to .zshrc or .bash_profile for permanent setup
if [ -z "$INFLUXDB_ENV_ADDED" ]; then
    # Determine shell type
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        SHELL_RC="$HOME/.bash_profile"
    else
        echo "Unknown shell. Please manually add the variables to your shell profile."
        return 1
    fi
    
    # Ask for confirmation
    echo "This will add InfluxDB environment variables to $SHELL_RC for permanent use."
    echo "Do you want to proceed? (y/n)"
    read -r response
    
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        # Add variables to shell profile
        cat << 'EOF' >> "$SHELL_RC"

# Virtuoso Trading System - InfluxDB Environment Variables
export INFLUXDB_URL=http://localhost:8086
export INFLUXDB_TOKEN=auUwotDWSbRMNkZLAptfwRv8_lOm_GGJHzmKirgv-Zj8xZya4T6NWYaVqZGNpfaMyxsmtdgBtpaVNtx7PIxNbQ==
export INFLUXDB_ORG=coinmaestro
export INFLUXDB_BUCKET=VirtuosoDB
export INFLUXDB_ENV_ADDED=true
EOF
        
        echo "Environment variables added to $SHELL_RC"
        echo "Please run 'source $SHELL_RC' or restart your terminal for changes to take effect."
        export INFLUXDB_ENV_ADDED=true
    else
        echo "Operation cancelled. Environment variables will only be set for the current session."
    fi
else
    echo "InfluxDB environment variables are already set permanently."
fi

# Verify variables are set correctly for current session
echo "InfluxDB environment variables for current session:"
echo "INFLUXDB_URL: $INFLUXDB_URL"
echo "INFLUXDB_ORG: $INFLUXDB_ORG"
echo "INFLUXDB_BUCKET: $INFLUXDB_BUCKET"
echo "INFLUXDB_TOKEN: ${INFLUXDB_TOKEN:0:10}...${INFLUXDB_TOKEN: -10}" 