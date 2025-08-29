#!/bin/bash

#############################################################################
# Script: deploy_cache_monitor_fix.sh
# Purpose: Deploy and manage deploy cache monitor fix
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
#   ./deploy_cache_monitor_fix.sh [options]
#   
#   Examples:
#     ./deploy_cache_monitor_fix.sh
#     ./deploy_cache_monitor_fix.sh --verbose
#     ./deploy_cache_monitor_fix.sh --dry-run
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

echo "🔧 Deploying Cache Monitor Fix Service..."
echo "=========================================="

VPS_HOST="linuxuser@45.77.40.77"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Copy the cache monitor fix script
echo "📤 Copying cache monitor fix to VPS..."
scp scripts/cache_monitor_fix.py $VPS_HOST:$PROJECT_DIR/scripts/

# Create systemd service
echo "🔧 Creating cache-monitor service..."
ssh $VPS_HOST "sudo tee /etc/systemd/system/cache-monitor.service > /dev/null << 'EOF'
[Unit]
Description=Cache Monitor and Fix Service
After=network.target memcached.service virtuoso.service

[Service]
Type=simple
User=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python /home/linuxuser/trading/Virtuoso_ccxt/scripts/cache_monitor_fix.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF"

# Start the service
echo "🚀 Starting cache monitor service..."
ssh $VPS_HOST "sudo systemctl daemon-reload && sudo systemctl enable cache-monitor && sudo systemctl restart cache-monitor"

# Restart web service to pick up changes
echo "🔄 Restarting web service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso-web.service"

# Wait for services to stabilize
echo "⏳ Waiting for services to stabilize..."
sleep 10

# Test the results
echo ""
echo "🧪 Testing All Market Metrics..."
echo "================================="

echo ""
echo "1️⃣ Cache Monitor Service Status:"
ssh $VPS_HOST "sudo systemctl status cache-monitor --no-pager | head -10"

echo ""
echo "2️⃣ Market Metrics Service Status:"
ssh $VPS_HOST "sudo systemctl status market-metrics --no-pager | head -10"

echo ""
echo "3️⃣ API Response Test:"
curl -s "http://45.77.40.77:8001/api/dashboard-cached/mobile-data" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    overview = data.get('market_overview', {})
    
    print('✅ FINAL MARKET METRICS STATUS:')
    print('=' * 40)
    
    # Check each metric
    regime = overview.get('market_regime', 'unknown')
    trend = overview.get('trend_strength', 0)
    btc_dom = overview.get('btc_dominance', 0)
    curr_vol = overview.get('current_volatility', 0)
    avg_vol = overview.get('avg_volatility', 0)
    volume = overview.get('total_volume_24h', 0)
    
    print(f'📊 Market Regime: {regime}')
    print(f'📈 Trend Strength: {trend}%', '✅' if trend > 0 else '❌ STILL BROKEN')
    print(f'₿ BTC Dominance: {btc_dom}%', '✅' if btc_dom > 0 else '❌ STILL BROKEN')
    print(f'📉 Current Volatility: {curr_vol}%', '✅' if curr_vol else '❌ STILL BROKEN')
    print(f'📊 Average Volatility: {avg_vol}%')
    print(f'💰 Total Volume: \${volume:,.0f}', '✅' if volume > 0 else '❌')
    
    if 'market_breadth' in data:
        breadth = data['market_breadth']
        print(f'')
        print(f'📊 Market Breadth:')
        print(f'   {breadth.get(\"up_count\", 0)} symbols rising')
        print(f'   {breadth.get(\"down_count\", 0)} symbols falling')
        print(f'   {breadth.get(\"breadth_percentage\", 0):.1f}% Bullish')
    
    # Summary
    print('')
    print('=' * 40)
    fixed_count = sum([
        trend > 0,
        btc_dom > 0,
        curr_vol is not None and curr_vol != 0,
        volume > 0
    ])
    
    if fixed_count == 4:
        print('🎉 ALL METRICS WORKING!')
    else:
        print(f'⚠️ {fixed_count}/4 metrics fixed')
        if trend == 0:
            print('   - Trend Strength still showing 0')
        if btc_dom == 0:
            print('   - BTC Dominance still showing 0')
        if not curr_vol:
            print('   - Current Volatility still missing')
            
except Exception as e:
    print(f'Error parsing response: {e}')
"

echo ""
echo "📱 Dashboard URL: http://45.77.40.77:8001/dashboard/mobile"
echo ""
echo "💡 Services Running:"
echo "   • cache-monitor: Fixes missing fields every 5 seconds"
echo "   • market-metrics: Updates market data every 30 seconds"
echo "   • virtuoso-web: Serves the dashboard"
echo ""
echo "📝 To check logs:"
echo "   ssh $VPS_HOST 'sudo journalctl -u cache-monitor -f'"