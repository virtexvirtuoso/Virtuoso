#!/bin/bash
#
# Watch for Performance Optimization Metrics on VPS
# This script monitors the VPS logs for our new performance metrics
#

VPS_HOST="${VPS_HOST:-vps}"
LOG_FILE="/home/linuxuser/trading/Virtuoso_ccxt/logs/app.log"

echo "🔍 Watching VPS for Performance Optimization Metrics"
echo "======================================================"
echo ""
echo "Looking for:"
echo "  1. ✨ Concurrency limit: 15"
echo "  2. ✨ Parallel indicator processing"
echo "  3. ✨ Symbol processing completion"
echo ""
echo "Press Ctrl+C to stop"
echo ""

ssh "${VPS_HOST}" "tail -f ${LOG_FILE}" | grep --line-buffered -E "concurrency limit|Parallel indicator|symbols processed successfully|Starting monitoring cycle"
