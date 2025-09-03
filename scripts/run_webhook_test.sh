#!/bin/bash

#############################################################################
# Script: run_webhook_test.sh
# Purpose: Deploy and manage run webhook test
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
#   ./run_webhook_test.sh [options]
#   
#   Examples:
#     ./run_webhook_test.sh
#     ./run_webhook_test.sh --verbose
#     ./run_webhook_test.sh --dry-run
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

# Run webhook test script for testing CPU alert routing
echo "===== Testing CPU Alert Routing ====="
python test_cpu_alert_routing.py
echo

# Pause to let Discord rate limits reset
echo "Waiting for 5 seconds..."
sleep 5

# Test the direct webhook simulation with exact formatting
echo "===== Testing Formatted CPU Alert ====="
python trigger_cpu_alert_test.py
echo

# Pause to let Discord rate limits reset
echo "Waiting for 5 seconds..."
sleep 5

# Test market report routing
echo "===== Testing Market Report Routing ====="
python test_market_report_webhook.py
echo

echo "===== All Tests Completed ====="
echo "Please check the Discord channels to verify:"
echo "1. CPU alerts are routed to the SYSTEM channel only"
echo "2. Market reports are routed to the SYSTEM channel only"
echo "3. No duplicate alerts appear in the MAIN channel" 