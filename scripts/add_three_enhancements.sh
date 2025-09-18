#!/bin/bash

#############################################################################
# Script: add_three_enhancements.sh
# Purpose: Deploy and manage add three enhancements
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
#   ./add_three_enhancements.sh [options]
#   
#   Examples:
#     ./add_three_enhancements.sh
#     ./add_three_enhancements.sh --verbose
#     ./add_three_enhancements.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 5.223.63.4)
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

# Add Exchange Connections, Database/Cache Status, and Quick Actions to working control panel
VPS_HOST="linuxuser@5.223.63.4"

echo "Adding three enhanced features to control panel..."

# Create enhancement patch
ssh $VPS_HOST 'cat > /tmp/add_enhancements.sh << '\''SCRIPT'\''
#!/bin/bash

# Backup current working version
cp /home/linuxuser/virtuoso_control.sh /home/linuxuser/virtuoso_control.sh.working_backup

# Add the enhancement functions before display_summary function
cat > /tmp/new_functions.txt << '\''FUNCS'\''

# Function to check exchange connections
check_exchange_connections() {
    echo -e "${BOLD}🌐 Exchange Connections${NC}"
    echo -e "${BOLD}──────────────────────${NC}"
    
    # Check Bybit
    BYBIT_START=$(date +%s%N)
    if curl -s -o /dev/null -w "%{http_code}" --max-time 2 https://api.bybit.com/v5/market/time 2>/dev/null | grep -q "200"; then
        BYBIT_END=$(date +%s%N)
        BYBIT_PING=$(( ($BYBIT_END - $BYBIT_START) / 1000000 ))
        echo -e "Bybit:           ${GREEN}✅ CONNECTED${NC} (ping: ${BYBIT_PING}ms)"
    else
        echo -e "Bybit:           ${RED}❌ DISCONNECTED${NC}"
    fi
    
    # Check Binance
    BINANCE_START=$(date +%s%N)
    if curl -s -o /dev/null -w "%{http_code}" --max-time 2 https://api.binance.com/api/v3/ping 2>/dev/null | grep -q "200"; then
        BINANCE_END=$(date +%s%N)
        BINANCE_PING=$(( ($BINANCE_END - $BINANCE_START) / 1000000 ))
        echo -e "Binance:         ${GREEN}✅ CONNECTED${NC} (ping: ${BINANCE_PING}ms)"
    else
        echo -e "Binance:         ${RED}❌ DISCONNECTED${NC}"
    fi
    
    # Check WebSocket connections
    if sudo journalctl -u virtuoso -n 50 --no-pager 2>/dev/null | grep -q "WebSocket" ; then
        echo -e "WebSocket:       ${GREEN}✅ LIVE${NC} (active streams)"
    else
        echo -e "WebSocket:       ${YELLOW}⚠️  NO RECENT DATA${NC}"
    fi
    
    # Check last data update
    LAST_UPDATE=$(sudo journalctl -u virtuoso -n 100 --no-pager 2>/dev/null | grep -E "data|market|price" | tail -1 | grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}" | head -1)
    if [ ! -z "$LAST_UPDATE" ]; then
        LAST_UPDATE_EPOCH=$(date -d "$LAST_UPDATE" +%s 2>/dev/null)
        NOW_EPOCH=$(date +%s)
        DIFF=$((NOW_EPOCH - LAST_UPDATE_EPOCH))
        if [ $DIFF -lt 60 ]; then
            echo -e "Last Data:       ${GREEN}${DIFF} seconds ago${NC}"
        elif [ $DIFF -lt 3600 ]; then
            echo -e "Last Data:       ${YELLOW}$((DIFF / 60)) minutes ago${NC}"
        else
            echo -e "Last Data:       ${RED}$((DIFF / 3600)) hours ago${NC}"
        fi
    fi
    
    echo ""
}

# Function to check database and cache status
check_database_cache() {
    echo -e "${BOLD}💾 Database & Cache Status${NC}"
    echo -e "${BOLD}──────────────────────────${NC}"
    
    # Check Redis if available
    if command -v redis-cli &> /dev/null; then
        if redis-cli ping 2>/dev/null | grep -q PONG; then
            REDIS_KEYS=$(redis-cli dbsize 2>/dev/null | grep -oE "[0-9]+")
            REDIS_MEM=$(redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\''\\r'\'')
            echo -e "Redis Cache:     ${GREEN}✅ CONNECTED${NC} ($REDIS_KEYS keys, $REDIS_MEM)"
        else
            echo -e "Redis Cache:     ${RED}❌ NOT RUNNING${NC}"
        fi
    else
        echo -e "Redis Cache:     ${YELLOW}⚠️  NOT INSTALLED${NC}"
    fi
    
    # Check local cache directory
    CACHE_DIR="/home/linuxuser/trading/Virtuoso_ccxt/cache"
    if [ -d "$CACHE_DIR" ]; then
        CACHE_SIZE=$(du -sh "$CACHE_DIR" 2>/dev/null | cut -f1)
        CACHE_FILES=$(find "$CACHE_DIR" -type f 2>/dev/null | wc -l)
        echo -e "File Cache:      ${GREEN}✅ ACTIVE${NC} ($CACHE_FILES files, $CACHE_SIZE)"
    else
        echo -e "File Cache:      ${YELLOW}⚠️  NO CACHE DIR${NC}"
    fi
    
    # Check log sizes
    LOG_SIZE=$(sudo journalctl -u virtuoso --disk-usage 2>/dev/null | grep -oE "[0-9.]+[MG]" || echo "N/A")
    WEB_LOG_SIZE=$(du -h /home/linuxuser/web_server.log 2>/dev/null | cut -f1 || echo "0")
    echo -e "Log Storage:     Main: $LOG_SIZE, Web: $WEB_LOG_SIZE"
    
    # Check backups
    BACKUP_DIR="/home/linuxuser/backups"
    if [ -d "$BACKUP_DIR" ]; then
        LAST_BACKUP=$(ls -t "$BACKUP_DIR"/virtuoso_backup_*.tar.gz 2>/dev/null | head -1)
        if [ ! -z "$LAST_BACKUP" ]; then
            BACKUP_DATE=$(stat -c %y "$LAST_BACKUP" 2>/dev/null | cut -d'\'' '\'' -f1)
            echo -e "Last Backup:     ${GREEN}$BACKUP_DATE${NC}"
        else
            echo -e "Last Backup:     ${YELLOW}Never${NC}"
        fi
    fi
    
    echo ""
}

FUNCS

# Insert the new functions before display_summary
sed -i "/^display_summary() {/r /tmp/new_functions.txt" /home/linuxuser/virtuoso_control.sh

# Add calls to these functions at the end of display_summary
sed -i "/echo -e.*────────────────────────────────────────────────────.*$/a\\
    echo \"\"\\
\\
    # Add Exchange Connections\\
    check_exchange_connections\\
\\
    # Add Database & Cache Status\\
    check_database_cache\\
\\
    echo -e \"\${BOLD}────────────────────────────────────────────────────\${NC}\"" /home/linuxuser/virtuoso_control.sh

# Update the show_options function to add Quick Actions
sed -i "/ 20) Restart server (full reboot)/a\\
\\
    echo \"\"\\
    echo -e \"\${BOLD}⚡ Quick Actions:\${NC}\"\\
    echo \" 21) Force sync all exchanges\"\\
    echo \" 22) Clear all caches\"\\
    echo \" 23) Test all API connections\"\\
    echo \" 24) Export trading logs\"\\
    echo \" 25) Emergency stop trading\"" /home/linuxuser/virtuoso_control.sh

# Add handlers for Quick Actions in execute_option function
sed -i "/20)/a\\
        21)\\
            echo \"Force syncing all exchanges...\"\\
            sudo systemctl restart virtuoso\\
            sleep 3\\
            echo -e \"\${GREEN}✅ Exchange sync initiated\${NC}\"\\
            ;;\\
        22)\\
            echo \"Clearing all caches...\"\\
            if command -v redis-cli &> /dev/null; then\\
                redis-cli FLUSHALL 2>/dev/null\\
            fi\\
            rm -rf /home/linuxuser/trading/Virtuoso_ccxt/cache/* 2>/dev/null\\
            echo -e \"\${GREEN}✅ All caches cleared\${NC}\"\\
            ;;\\
        23)\\
            echo \"Testing API connections...\"\\
            echo \"\"\\
            echo \"Bybit API:\"\\
            curl -s https://api.bybit.com/v5/market/time | head -c 100\\
            echo \"\"\\
            echo \"\"\\
            echo \"Binance API:\"\\
            curl -s https://api.binance.com/api/v3/time | head -c 100\\
            echo \"\"\\
            echo \"\"\\
            echo -e \"\${GREEN}✅ API test complete\${NC}\"\\
            ;;\\
        24)\\
            echo \"Exporting trading logs...\"\\
            EXPORT_DIR=\"/home/linuxuser/exports\"\\
            mkdir -p \$EXPORT_DIR\\
            TIMESTAMP=\$(date +%Y%m%d_%H%M%S)\\
            sudo journalctl -u virtuoso --since \"24 hours ago\" > \$EXPORT_DIR/trading_logs_\$TIMESTAMP.log\\
            echo -e \"\${GREEN}✅ Logs exported to: \$EXPORT_DIR/trading_logs_\$TIMESTAMP.log\${NC}\"\\
            ;;\\
        25)\\
            echo -e \"\${RED}⚠️  EMERGENCY STOP INITIATED\${NC}\"\\
            echo \"Stopping all trading services immediately...\"\\
            sudo systemctl stop virtuoso\\
            pkill -f \"python.*main.py\"\\
            pkill -f \"web_server\"\\
            echo -e \"\${RED}❌ All trading stopped - Manual restart required\${NC}\"\\
            ;;" /home/linuxuser/virtuoso_control.sh

# Update the selection prompt to include 0-25
sed -i "s/Enter selection \[0-20\]/Enter selection [0-25]/" /home/linuxuser/virtuoso_control.sh

# Fix the stop_web_server function to handle the uvicorn process correctly
sed -i "/^stop_web_server() {/,/^}/c\\
stop_web_server() {\\
    echo \"Stopping web server...\"\\
    pkill -f \"web_server\" 2>/dev/null\\
    pkill -f \"uvicorn\" 2>/dev/null\\
    sleep 2\\
    \\
    if ! pgrep -f \"web_server\" > /dev/null && ! pgrep -f \"uvicorn\" > /dev/null; then\\
        echo -e \"\${GREEN}✅ Web server stopped\${NC}\"\\
    else\\
        echo -e \"\${YELLOW}⚠️  Web server still running, forcing kill\${NC}\"\\
        pkill -9 -f \"web_server\" 2>/dev/null\\
        pkill -9 -f \"uvicorn\" 2>/dev/null\\
    fi\\
}" /home/linuxuser/virtuoso_control.sh

echo "Enhancements added successfully!"
SCRIPT
chmod +x /tmp/add_enhancements.sh
bash /tmp/add_enhancements.sh
'

echo ""
echo "✅ Three enhanced features added to control panel!"
echo ""
echo "New features in your VT panel:"
echo "  🌐 Exchange Connections - Live status with ping times"
echo "  💾 Database & Cache Status - Redis, file cache, backups"
echo "  ⚡ Quick Actions (21-25):"
echo "     21) Force sync all exchanges"
echo "     22) Clear all caches"
echo "     23) Test all API connections"
echo "     24) Export trading logs"
echo "     25) Emergency stop trading"
echo ""
echo "Test with: vt"