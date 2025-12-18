#!/bin/bash
#
# Cron Setup Script for Daily Performance Monitor
#
# This script helps set up a cron job for the performance monitor
# (alternative to systemd timer)
#
# Usage:
#   ./scripts/cron_setup.sh [--install|--uninstall|--test]
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Determine project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_BIN="${PROJECT_ROOT}/venv311/bin/python"

# Use venv python if it exists
if [[ -f "$VENV_BIN" ]]; then
    PYTHON_BIN="$VENV_BIN"
fi

# Cron job entry
CRON_JOB="0 9 * * * cd $PROJECT_ROOT && $PYTHON_BIN $PROJECT_ROOT/scripts/daily_performance_monitor.py >> $PROJECT_ROOT/logs/performance_monitor.log 2>&1"

function install_cron() {
    echo -e "${GREEN}Installing cron job...${NC}"

    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "daily_performance_monitor.py"; then
        echo -e "${YELLOW}Cron job already exists!${NC}"
        echo "Current entry:"
        crontab -l | grep "daily_performance_monitor.py"
        echo ""
        read -p "Replace it? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborting."
            exit 0
        fi
        # Remove old entry
        (crontab -l | grep -v "daily_performance_monitor.py") | crontab -
    fi

    # Add new entry
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

    echo -e "${GREEN}✓ Cron job installed${NC}"
    echo ""
    echo "Schedule: Daily at 9:00 AM"
    echo "Log file: $PROJECT_ROOT/logs/performance_monitor.log"
    echo ""
    echo "Current crontab:"
    crontab -l | grep "daily_performance_monitor.py"
}

function uninstall_cron() {
    echo -e "${YELLOW}Uninstalling cron job...${NC}"

    if crontab -l 2>/dev/null | grep -q "daily_performance_monitor.py"; then
        (crontab -l | grep -v "daily_performance_monitor.py") | crontab -
        echo -e "${GREEN}✓ Cron job removed${NC}"
    else
        echo "No cron job found."
    fi
}

function test_cron() {
    echo -e "${GREEN}Testing cron job command...${NC}"
    echo "Python: $PYTHON_BIN"
    echo "Project: $PROJECT_ROOT"
    echo ""

    # Create logs directory
    mkdir -p "$PROJECT_ROOT/logs"

    # Test command
    cd "$PROJECT_ROOT" && $PYTHON_BIN "$PROJECT_ROOT/scripts/daily_performance_monitor.py" --dry-run

    if [[ $? -eq 0 || $? -eq 1 ]]; then
        echo ""
        echo -e "${GREEN}✓ Test successful${NC}"
        echo ""
        echo "To install cron job, run:"
        echo "  ./scripts/cron_setup.sh --install"
    else
        echo ""
        echo -e "${RED}✗ Test failed${NC}"
        exit 1
    fi
}

# Parse arguments
case "$1" in
    --install)
        install_cron
        ;;
    --uninstall)
        uninstall_cron
        ;;
    --test)
        test_cron
        ;;
    *)
        echo "Usage: $0 [--install|--uninstall|--test]"
        echo ""
        echo "Options:"
        echo "  --install    Install cron job (daily at 9 AM)"
        echo "  --uninstall  Remove cron job"
        echo "  --test       Test the command without installing"
        echo ""
        echo "Examples:"
        echo "  ./scripts/cron_setup.sh --test"
        echo "  ./scripts/cron_setup.sh --install"
        echo ""
        echo "Current crontab (if any):"
        crontab -l 2>/dev/null | grep "daily_performance_monitor.py" || echo "  (none)"
        exit 1
        ;;
esac
