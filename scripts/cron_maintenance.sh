#!/bin/bash
# Cron wrapper for maintenance tasks
cd "/Users/ffv_macmini/desktop/virtuoso_ccxt"
export PYTHONPATH="/Users/ffv_macmini/desktop/virtuoso_ccxt"
source venv311/bin/activate 2>/dev/null || true

# Run local maintenance (excluding VPS for safety in cron)
"/Users/ffv_macmini/desktop/virtuoso_ccxt/scripts/automated_maintenance.py" --categories logs archives reports >> "/Users/ffv_macmini/desktop/virtuoso_ccxt/logs/cron_maintenance.log" 2>&1
