#!/bin/bash

echo "🚀 Deploying alert system fixes to VPS..."
echo "========================================"

# Deploy fixed files
echo "📦 Deploying fixed alert components..."
scp src/monitoring/alert_manager.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/
scp src/monitoring/components/alerts/alert_delivery.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/components/alerts/
scp src/core/analysis/liquidation_detector.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/core/analysis/
scp src/core/analysis/confluence.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/core/analysis/
scp src/monitoring/monitor.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/

# Deploy monitoring and fix scripts
echo "📦 Deploying monitoring scripts..."
scp scripts/monitor_alert_health.py vps:/home/linuxuser/trading/Virtuoso_ccxt/scripts/
scp scripts/fix_alert_silent_failures.py vps:/home/linuxuser/trading/Virtuoso_ccxt/scripts/

echo "🔄 Restarting services..."
ssh vps "sudo systemctl restart virtuoso.service"

echo "⏳ Waiting for services to stabilize..."
sleep 5

echo "✅ Checking service status..."
ssh vps "sudo systemctl status virtuoso.service --no-pager | head -20"

echo "🔍 Running health check..."
ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && source venv311/bin/activate && python scripts/monitor_alert_health.py | head -50"

echo "========================================"
echo "✅ Alert fixes deployed successfully!"
echo ""
echo "📊 Monitoring will run hourly via cron"
echo "📁 Check logs at: /home/linuxuser/trading/Virtuoso_ccxt/logs/alert_health.log"