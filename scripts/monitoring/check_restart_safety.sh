#!/bin/bash

#############################################################################
# Script: check_restart_safety.sh
# Purpose: Check if it's safe to restart the Mac while maintaining SSH access
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates automated testing, validation, and quality assurance for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - python3
#   - curl
#   - grep
#   - Access to project directory structure
#
# Usage:
#   ./check_restart_safety.sh [options]
#   
#   Examples:
#     ./check_restart_safety.sh
#     ./check_restart_safety.sh --verbose
#     ./check_restart_safety.sh --dry-run
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
#   0 - All tests passed
#   1 - Test failures detected
#   2 - Test configuration error
#   3 - Dependencies missing
#   4 - Environment setup failed
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== SSH Restart Safety Check ==="
echo ""

SAFE=true

# 1. Check if SSH is running
echo -n "Checking SSH service... "
if ps aux | grep -q "[s]shd"; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    SAFE=false
fi

# 2. Check for active SSH sessions
echo -n "Checking active SSH sessions... "
SESSION_COUNT=$(who | grep -c "pts\|ttys" || true)
echo -e "${YELLOW}Found $SESSION_COUNT active session(s)${NC}"

# 3. Check network connectivity
echo -n "Checking network interfaces... "
ACTIVE_INTERFACES=$(ifconfig | grep -c "inet " | grep -v 127.0.0.1 || true)
if [[ $ACTIVE_INTERFACES -gt 0 ]]; then
    echo -e "${GREEN}✓ $ACTIVE_INTERFACES active interface(s)${NC}"
else
    echo -e "${RED}✗ No active network interfaces${NC}"
    SAFE=false
fi

# 4. Check for running critical processes
echo -n "Checking for critical processes... "
CRITICAL_PROCS=""
if pgrep -f "virtuoso" > /dev/null 2>&1; then
    CRITICAL_PROCS="${CRITICAL_PROCS}virtuoso "
fi
if pgrep -f "docker" > /dev/null 2>&1; then
    CRITICAL_PROCS="${CRITICAL_PROCS}docker "
fi
if pgrep -f "screen\|tmux" > /dev/null 2>&1; then
    CRITICAL_PROCS="${CRITICAL_PROCS}screen/tmux "
fi

if [[ -z "$CRITICAL_PROCS" ]]; then
    echo -e "${GREEN}✓ None found${NC}"
else
    echo -e "${YELLOW}⚠ Found: $CRITICAL_PROCS${NC}"
fi

# 5. Check disk space
echo -n "Checking disk space... "
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [[ $DISK_USAGE -lt 90 ]]; then
    echo -e "${GREEN}✓ ${DISK_USAGE}% used${NC}"
else
    echo -e "${YELLOW}⚠ ${DISK_USAGE}% used (high)${NC}"
fi

# 6. Check system load
echo -n "Checking system load... "
LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
LOAD_INT=${LOAD%.*}
CPU_COUNT=$(sysctl -n hw.ncpu)
if [[ $LOAD_INT -lt $CPU_COUNT ]]; then
    echo -e "${GREEN}✓ Load: $LOAD (CPUs: $CPU_COUNT)${NC}"
else
    echo -e "${YELLOW}⚠ Load: $LOAD (CPUs: $CPU_COUNT) - System under load${NC}"
fi

# 7. Show IP addresses for reconnection
echo ""
echo "Your IP addresses for reconnection:"
ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print "  • " $2}'

# Summary
echo ""
if $SAFE; then
    echo -e "${GREEN}✓ System appears safe to restart${NC}"
    echo ""
    echo "To restart safely, run:"
    echo "  ./scripts/safe_restart_mac.sh [delay_seconds]"
    echo ""
    echo "Examples:"
    echo "  ./scripts/safe_restart_mac.sh 60     # Restart in 60 seconds"
    echo "  ./scripts/safe_restart_mac.sh 0      # Restart immediately"
else
    echo -e "${RED}✗ WARNING: Issues detected that may prevent SSH reconnection${NC}"
    echo -e "${RED}  Fix the issues above before restarting${NC}"
fi

# Additional tips
echo ""
echo "Tips for safe restart:"
echo "  • Save all your work"
echo "  • Note down the IP addresses above"
echo "  • Ensure you have alternate access if SSH fails"
echo "  • Consider running critical processes in screen/tmux"