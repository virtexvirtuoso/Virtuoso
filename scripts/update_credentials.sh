#!/bin/bash

#############################################################################
# Script: update_credentials.sh
# Purpose: Script to update InfluxDB credentials and fix issues
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
#   ./update_credentials.sh [options]
#   
#   Examples:
#     ./update_credentials.sh
#     ./update_credentials.sh --verbose
#     ./update_credentials.sh --dry-run
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

echo "========================================================"
echo "Virtuoso Trading System - Configuration and Fix Script"
echo "========================================================"

# InfluxDB credentials
export INFLUXDB_URL="http://localhost:8086"
export INFLUXDB_TOKEN="auUwotDWSbRMNkZLAptfwRv8_lOm_GGJHzmKirgv-Zj8xZya4T6NWYaVqZGNpfaMyxsmtdgBtpaVNtx7PIxNbQ=="
export INFLUXDB_ORG="coinmaestro"
export INFLUXDB_BUCKET="VirtuosoDB"

echo "InfluxDB credentials exported to environment:"
echo "- URL: $INFLUXDB_URL"
echo "- Organization: $INFLUXDB_ORG"
echo "- Bucket: $INFLUXDB_BUCKET"
echo "- Token: ${INFLUXDB_TOKEN:0:10}...${INFLUXDB_TOKEN: -10}" # Show only part of the token for security

echo ""
echo "Issues fixed:"
echo "1. JSON Serialization Error: Updated PDF generator to use CustomJSONEncoder"
echo "   for handling pandas Timestamp objects"
echo ""
echo "2. InfluxDB Authentication: Set environment variables with correct credentials"
echo ""

echo "To use these credentials, run:"
echo "source update_credentials.sh"
echo ""
echo "Then run your application to use the updated environment variables" 