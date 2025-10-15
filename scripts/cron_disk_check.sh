#!/bin/bash
# Cron wrapper for disk usage monitoring
cd "/Users/ffv_macmini/desktop/virtuoso_ccxt"
USAGE=$(df -P "/Users/ffv_macmini/desktop/virtuoso_ccxt" | awk 'NR==2 {print $5}' | tr -d '%')

if [[ $USAGE -gt 90 ]]; then
    echo "$(date): CRITICAL - Disk usage ${USAGE}% - Running emergency cleanup" >> "/Users/ffv_macmini/desktop/virtuoso_ccxt/logs/disk_monitor.log"
    "/Users/ffv_macmini/desktop/virtuoso_ccxt/scripts/comprehensive_cleanup.sh" --local-only >> "/Users/ffv_macmini/desktop/virtuoso_ccxt/logs/emergency_cleanup.log" 2>&1
elif [[ $USAGE -gt 80 ]]; then
    echo "$(date): WARNING - Disk usage ${USAGE}%" >> "/Users/ffv_macmini/desktop/virtuoso_ccxt/logs/disk_monitor.log"
fi
