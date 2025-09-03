#!/bin/bash

# Remove existing Virtuoso cron jobs
crontab -l | grep -v "Virtuoso" | crontab -

# Add correct cron jobs
(crontab -l 2>/dev/null; echo "0 3 * * * cd /Users/ffv_macmini/Desktop/Virtuoso_ccxt && /usr/bin/python3 scripts/utilities/clean_logs.py --execute >> logs/cleanup.log 2>&1 # Virtuoso daily log cleanup") | crontab -
(crontab -l 2>/dev/null; echo "0 2 * * 0 cd /Users/ffv_macmini/Desktop/Virtuoso_ccxt && /usr/bin/python3 scripts/utilities/clean_logs.py --execute --aggressive >> logs/cleanup.log 2>&1 # Virtuoso weekly aggressive cleanup") | crontab -

echo "Fixed cron jobs:"
crontab -l | grep Virtuoso