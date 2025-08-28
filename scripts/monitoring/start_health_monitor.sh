#!/bin/bash
# Start Critical Health Monitor - Part of Phase 1: Emergency Stabilization

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