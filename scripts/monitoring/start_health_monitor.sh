#!/bin/bash

#############################################################################
# Script: start_health_monitor.sh
# Purpose: Start Critical Health Monitor - Part of Phase 1: Emergency Stabilization
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
#   ./start_health_monitor.sh [options]
#   
#   Examples:
#     ./start_health_monitor.sh
#     ./start_health_monitor.sh --verbose
#     ./start_health_monitor.sh --dry-run
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

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/venv311" ]; then
    log_error "Virtual environment venv311 not found"
    log_info "Please create the virtual environment first:"
    log_info "python3.11 -m venv venv311"
    exit 1
fi

# Activate virtual environment
source "$PROJECT_ROOT/venv311/bin/activate"

# Install required packages if not present
log_info "Installing required packages..."
pip install -q psutil aiohttp

# Check if health monitor file exists
HEALTH_MONITOR_FILE="$PROJECT_ROOT/src/monitoring/critical_health_monitor.py"
if [ ! -f "$HEALTH_MONITOR_FILE" ]; then
    log_error "Health monitor file not found: $HEALTH_MONITOR_FILE"
    exit 1
fi

log_info "Starting Critical Health Monitor..."
log_info "Monitor will check system health every 30 seconds"
log_info "Press Ctrl+C to stop monitoring"
echo ""

# Set PYTHONPATH to include project root
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Start the health monitor
cd "$PROJECT_ROOT"
python "$HEALTH_MONITOR_FILE"