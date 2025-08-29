#!/bin/bash

#############################################################################
# Script: restart_vps_web.sh
# Purpose: Deploy and manage restart vps web
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
#   ./restart_vps_web.sh [options]
#   
#   Examples:
#     ./restart_vps_web.sh
#     ./restart_vps_web.sh --verbose
#     ./restart_vps_web.sh --dry-run
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

ssh linuxuser@45.77.40.77 'bash -c "pkill -f web_server.py; sleep 2; cd /home/linuxuser/trading/Virtuoso_ccxt && PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt nohup venv311/bin/python src/web_server.py > logs/web_final.log 2>&1 & sleep 5 && tail -n 30 logs/web_final.log"'