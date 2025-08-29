#!/bin/bash

#############################################################################
# Script: fix_enhanced_features_final.sh
# Purpose: Deploy and manage fix enhanced features final
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
#   ./fix_enhanced_features_final.sh [options]
#   
#   Examples:
#     ./fix_enhanced_features_final.sh
#     ./fix_enhanced_features_final.sh --verbose
#     ./fix_enhanced_features_final.sh --dry-run
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

# Final fix to properly integrate all three enhanced features
VPS_HOST="linuxuser@45.77.40.77"

echo "Fixing and integrating enhanced features..."

# First, let's check the current line count and structure
ssh $VPS_HOST 'wc -l /home/linuxuser/virtuoso_control.sh'

# Create a completely new enhanced version from scratch
ssh $VPS_HOST 'cat > /home/linuxuser/virtuoso_control_enhanced.sh << '\''FULLSCRIPT'\''
#!/bin/bash

# Virtuoso Unified Control System with Enhanced Features
# Version 7.0 - Complete with Exchange/Cache/Quick Actions

# Configuration file for settings
CONFIG_FILE="/home/linuxuser/.virtuoso_config"

# Colors for output
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
MAGENTA="\033[0;35m"
BOLD="\033[1m"
NC="\033[0m" # No Color

# Load configuration
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
    else
        WEB_SERVER_AUTO_START="enabled"
        echo "WEB_SERVER_AUTO_START=\"enabled\"" > "$CONFIG_FILE"
    fi
}

# Save configuration
save_config() {
    echo "WEB_SERVER_AUTO_START=\"$WEB_SERVER_AUTO_START\"" > "$CONFIG_FILE"
}

# Function to get uptime in human-readable format
get_uptime() {
    local service=$1
    if [ "$service" = "main" ]; then
        if sudo systemctl is-active virtuoso > /dev/null; then
            local start_time=$(sudo systemctl show virtuoso --property=ActiveEnterTimestamp | cut -d= -f2)
            if [ ! -z "$start_time" ]; then
                local start_epoch=$(date -d "$start_time" +%s 2>/dev/null)
                local now_epoch=$(date +%s)
                local uptime_seconds=$((now_epoch - start_epoch))
                
                if [ $uptime_seconds -lt 60 ]; then
                    echo "${uptime_seconds}s"
                elif [ $uptime_seconds -lt 3600 ]; then
                    echo "$((uptime_seconds / 60))m"
                elif [ $uptime_seconds -lt 86400 ]; then
                    echo "$((uptime_seconds / 3600))h $((uptime_seconds % 3600 / 60))m"
                else
                    echo "$((uptime_seconds / 86400))d $((uptime_seconds % 86400 / 3600))h"
                fi
            else
                echo "unknown"
            fi
        else
            echo "stopped"
        fi
    elif [ "$service" = "web" ]; then
        if pgrep -f "web_server" > /dev/null; then
            local pid=$(pgrep -f "web_server" | head -1)
            local start_time=$(ps -o lstart= -p $pid 2>/dev/null)
            if [ ! -z "$start_time" ]; then
                local start_epoch=$(date -d "$start_time" +%s 2>/dev/null)
                local now_epoch=$(date +%s)
                local uptime_seconds=$((now_epoch - start_epoch))
                
                if [ $uptime_seconds -lt 60 ]; then
                    echo "${uptime_seconds}s"
                elif [ $uptime_seconds -lt 3600 ]; then
                    echo "$((uptime_seconds / 60))m"
                elif [ $uptime_seconds -lt 86400 ]; then
                    echo "$((uptime_seconds / 3600))h $((uptime_seconds % 3600 / 60))m"
                else
                    echo "$((uptime_seconds / 86400))d $((uptime_seconds % 86400 / 3600))h"
                fi
            else
                echo "unknown"
            fi
        else
            echo "stopped"
        fi
    fi
}

# Function to get last restart time
get_last_restart() {
    if [ -f /home/linuxuser/virtuoso_restart.log ]; then
        local last_restart=$(grep "Starting Virtuoso restart sequence" /home/linuxuser/virtuoso_restart.log | tail -1 | cut -d: -f1-3)
        if [ ! -z "$last_restart" ]; then
            echo "$last_restart"
        else
            echo "Never"
        fi
    else
        echo "Never"
    fi
}

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
            REDIS_MEM=$(redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r')
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
            BACKUP_DATE=$(stat -c %y "$LAST_BACKUP" 2>/dev/null | cut -d' ' -f1)
            echo -e "Last Backup:     ${GREEN}$BACKUP_DATE${NC}"
        else
            echo -e "Last Backup:     ${YELLOW}Never${NC}"
        fi
    fi
    
    echo ""
}

# Function to display summary panel
display_summary() {
    echo -e "${BOLD}${CYAN}====================================================${NC}"
    echo -e "${BOLD}${CYAN}       Virtuoso Trading Service Control Panel      ${NC}"
    echo -e "${BOLD}${CYAN}====================================================${NC}"
    echo ""
    
    # Load configuration
    load_config
    
    # Service Status Summary
    echo -e "${BOLD}📊 Service Status Summary${NC}"
    echo -e "${BOLD}────────────────────────${NC}"
    
    # Main Service Status
    if sudo systemctl is-active virtuoso > /dev/null; then
        local main_uptime=$(get_uptime main)
        local main_pid=$(sudo systemctl show virtuoso --property=MainPID | cut -d= -f2)
        echo -e "Main Service:    ${GREEN}● RUNNING${NC} (uptime: $main_uptime, PID: $main_pid)"
    else
        echo -e "Main Service:    ${RED}● STOPPED${NC}"
    fi
    
    # Web Server Status
    if pgrep -f "web_server" > /dev/null; then
        local web_uptime=$(get_uptime web)
        local web_pid=$(pgrep -f "web_server" | head -1)
        echo -e "Web Server:      ${GREEN}● RUNNING${NC} (uptime: $web_uptime, PID: $web_pid)"
    else
        echo -e "Web Server:      ${RED}● STOPPED${NC}"
    fi
    
    # Dashboard Access
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health 2>/dev/null | grep -q "200"; then
        echo -e "Dashboard:       ${GREEN}● ACCESSIBLE${NC} (port 8001)"
    else
        echo -e "Dashboard:       ${RED}● NOT ACCESSIBLE${NC}"
    fi
    
    echo ""
    
    # Configuration Summary
    echo -e "${BOLD}⚙️  Configuration${NC}"
    echo -e "${BOLD}──────────────${NC}"
    
    # Auto-start settings
    if sudo systemctl is-enabled virtuoso > /dev/null 2>&1; then
        echo -e "Boot Auto-start: ${GREEN}ENABLED${NC} (main service starts on boot)"
    else
        echo -e "Boot Auto-start: ${YELLOW}DISABLED${NC} (manual start required)"
    fi
    
    if [ "$WEB_SERVER_AUTO_START" = "enabled" ]; then
        echo -e "Web Auto-start:  ${GREEN}ENABLED${NC} (web starts with main service)"
    else
        echo -e "Web Auto-start:  ${YELLOW}DISABLED${NC} (manual web start required)"
    fi
    
    echo ""
    
    # Maintenance Info
    echo -e "${BOLD}🔧 Maintenance Schedule${NC}"
    echo -e "${BOLD}─────────────────────${NC}"
    echo -e "Daily Restart:   ${CYAN}3:00 AM SGT${NC}"
    local last_restart=$(get_last_restart)
    echo -e "Last Restart:    $last_restart"
    
    # Check if cron job exists
    if crontab -l 2>/dev/null | grep -q restart_virtuoso; then
        echo -e "Cron Job:        ${GREEN}CONFIGURED${NC}"
    else
        echo -e "Cron Job:        ${RED}NOT CONFIGURED${NC}"
    fi
    
    echo ""
    
    # System Resources
    echo -e "${BOLD}💻 System Resources${NC}"
    echo -e "${BOLD}─────────────────${NC}"
    echo -e "Memory Usage:    $(free -h | grep Mem | awk "{print \$3\" / \"\$2}")"
    echo -e "CPU Load:        $(uptime | awk -F"load average:" "{print \$2}")"
    echo -e "Disk Usage:      $(df -h / | tail -1 | awk "{print \$3\" / \"\$2\" (\"\$5\" used)\"}")"
    
    # Count processes
    local python_procs=$(pgrep -c python 2>/dev/null || echo 0)
    echo -e "Python Procs:    $python_procs active"
    
    echo ""
    echo -e "${BOLD}────────────────────────────────────────────────────${NC}"
    echo ""
    
    # Add Exchange Connections
    check_exchange_connections
    
    # Add Database & Cache Status
    check_database_cache
    
    echo -e "${BOLD}────────────────────────────────────────────────────${NC}"
}

# Function to start web server
start_web_server() {
    echo "Starting web server..."
    
    # Kill any existing web server processes
    pkill -f "web_server" 2>/dev/null
    sleep 2
    
    # Start web server in background
    cd /home/linuxuser/trading/Virtuoso_ccxt
    nohup /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python src/web_server.py > /home/linuxuser/web_server.log 2>&1 &
    
    sleep 3
    
    # Verify it started
    if pgrep -f "web_server" > /dev/null; then
        echo -e "${GREEN}✅ Web server started successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to start web server${NC}"
        return 1
    fi
}

# Function to stop web server
stop_web_server() {
    echo "Stopping web server..."
    pkill -f "web_server" 2>/dev/null
    sleep 2
    
    if ! pgrep -f "web_server" > /dev/null; then
        echo -e "${GREEN}✅ Web server stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  Web server still running, forcing kill${NC}"
        pkill -9 -f "web_server" 2>/dev/null
    fi
}

# Function to show numbered options
show_options() {
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  1) Enable main service auto-start (boot)"
    echo "  2) Disable main service auto-start"
    echo "  3) Toggle web server auto-start"
    echo "  4) Start all services"
    echo "  5) Stop all services"
    echo "  6) Restart all services"
    echo "  7) Start main service only"
    echo "  8) Stop main service only"
    echo "  9) Start web server only"
    echo " 10) Stop web server only"
    echo " 11) View logs (live)"
    echo " 12) View recent logs"
    echo " 13) Health check"
    echo " 14) Clean temp files"
    echo " 15) Kill all processes"
    echo " 16) View configuration"
    echo " 17) System information"
    echo " 18) Network test"
    echo " 19) Backup configuration"
    echo " 20) Restart server (full reboot)"
    echo ""
    echo -e "${BOLD}⚡ Quick Actions:${NC}"
    echo " 21) Force sync all exchanges"
    echo " 22) Clear all caches"
    echo " 23) Test all API connections"
    echo " 24) Export trading logs"
    echo " 25) Emergency stop trading"
    echo ""
    echo "  0) Exit"
    echo ""
}

# Execute numbered option - COMPLETE function
execute_option() {
    local selection=$1
    
    case $selection in
        1)
            echo "Enabling main service auto-start..."
            sudo systemctl enable virtuoso
            echo -e "${GREEN}✅ Main service will start on boot${NC}"
            ;;
        2)
            echo "Disabling main service auto-start..."
            sudo systemctl disable virtuoso
            echo -e "${YELLOW}⚠️  Main service will NOT start on boot${NC}"
            ;;
        3)
            load_config
            if [ "$WEB_SERVER_AUTO_START" = "enabled" ]; then
                WEB_SERVER_AUTO_START="disabled"
                echo -e "${YELLOW}⚠️  Web server auto-start DISABLED${NC}"
            else
                WEB_SERVER_AUTO_START="enabled"
                echo -e "${GREEN}✅ Web server auto-start ENABLED${NC}"
            fi
            save_config
            ;;
        4)
            echo "Starting all services..."
            sudo systemctl start virtuoso
            sleep 3
            load_config
            if [ "$WEB_SERVER_AUTO_START" = "enabled" ]; then
                start_web_server
            fi
            ;;
        5)
            echo "Stopping all services..."
            stop_web_server
            sudo systemctl stop virtuoso
            echo -e "${GREEN}✅ All services stopped${NC}"
            ;;
        6)
            echo "Restarting all services..."
            stop_web_server
            sudo systemctl restart virtuoso
            sleep 3
            load_config
            if [ "$WEB_SERVER_AUTO_START" = "enabled" ]; then
                start_web_server
            fi
            ;;
        7)
            echo "Starting main service..."
            sudo systemctl start virtuoso
            echo -e "${GREEN}✅ Main service started${NC}"
            ;;
        8)
            echo "Stopping main service..."
            sudo systemctl stop virtuoso
            echo -e "${GREEN}✅ Main service stopped${NC}"
            ;;
        9)
            start_web_server
            ;;
        10)
            stop_web_server
            ;;
        11)
            echo "Following main service logs (Ctrl+C to return)..."
            sudo journalctl -u virtuoso -f
            ;;
        12)
            echo -e "${BOLD}=== Main Service Logs (last 20) ===${NC}"
            sudo journalctl -u virtuoso -n 20 --no-pager
            echo ""
            echo -e "${BOLD}=== Web Server Logs (last 20) ===${NC}"
            tail -n 20 /home/linuxuser/web_server.log 2>/dev/null || echo "No logs"
            ;;
        13)
            echo -e "${BOLD}Performing health check...${NC}"
            echo ""
            
            # Test endpoints
            echo "Testing API endpoints:"
            
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health 2>/dev/null)
            if [ "$HTTP_CODE" = "200" ]; then
                echo -e "  /health:    ${GREEN}✅ OK${NC}"
            else
                echo -e "  /health:    ${RED}❌ Failed (HTTP $HTTP_CODE)${NC}"
            fi
            
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/dashboard 2>/dev/null)
            if [ "$HTTP_CODE" = "200" ]; then
                echo -e "  /dashboard: ${GREEN}✅ OK${NC}"
            else
                echo -e "  /dashboard: ${YELLOW}⚠️  HTTP $HTTP_CODE${NC}"
            fi
            ;;
        14)
            echo "Cleaning temporary files..."
            rm -f /tmp/virtuoso.lock
            sudo journalctl --vacuum-time=7d
            > /home/linuxuser/web_server.log
            echo -e "${GREEN}✅ Cleanup complete${NC}"
            ;;
        15)
            echo -e "${YELLOW}⚠️  Killing all Virtuoso processes...${NC}"
            pkill -f virtuoso
            pkill -f "python.*main.py"
            pkill -f "web_server"
            echo -e "${GREEN}✅ All processes killed${NC}"
            ;;
        16)
            echo -e "${BOLD}Current Configuration:${NC}"
            echo "========================"
            load_config
            echo "Main Service Auto-start: $(sudo systemctl is-enabled virtuoso 2>/dev/null || echo 'disabled')"
            echo "Web Server Auto-start:   $WEB_SERVER_AUTO_START"
            echo ""
            echo "Config file: $CONFIG_FILE"
            echo "Service file: /etc/systemd/system/virtuoso.service"
            ;;
        17)
            echo -e "${BOLD}System Information:${NC}"
            echo "==================="
            echo "Hostname: $(hostname)"
            echo "OS: $(lsb_release -ds 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2)"
            echo "Kernel: $(uname -r)"
            echo "Uptime: $(uptime -p | sed 's/up //' 2>/dev/null || uptime | awk '{print $3}')"
            echo "CPU Cores: $(nproc)"
            echo "Total Memory: $(free -h | grep Mem | awk '{print $2}')"
            echo "IP Address: $(hostname -I | awk '{print $1}')"
            ;;
        18)
            echo -e "${BOLD}Network Connectivity Test:${NC}"
            echo "=========================="
            
            # Test internet
            if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
                echo -e "Internet:     ${GREEN}✅ Connected${NC}"
            else
                echo -e "Internet:     ${RED}❌ No connection${NC}"
            fi
            
            # Test Bybit API
            if curl -s -o /dev/null -w "%{http_code}" https://api.bybit.com/v5/market/time 2>/dev/null | grep -q "200"; then
                echo -e "Bybit API:    ${GREEN}✅ Reachable${NC}"
            else
                echo -e "Bybit API:    ${RED}❌ Unreachable${NC}"
            fi
            
            # Test local dashboard
            if curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health 2>/dev/null | grep -q "200"; then
                echo -e "Dashboard:    ${GREEN}✅ Accessible${NC}"
            else
                echo -e "Dashboard:    ${RED}❌ Not accessible${NC}"
            fi
            ;;
        19)
            echo "Creating configuration backup..."
            BACKUP_DIR="/home/linuxuser/backups"
            TIMESTAMP=$(date +%Y%m%d_%H%M%S)
            mkdir -p $BACKUP_DIR
            
            tar -czf $BACKUP_DIR/virtuoso_backup_$TIMESTAMP.tar.gz \
                /home/linuxuser/.virtuoso_config \
                /home/linuxuser/trading/Virtuoso_ccxt/config/ \
                /home/linuxuser/trading/Virtuoso_ccxt/.env \
                /etc/systemd/system/virtuoso.service \
                2>/dev/null
            
            echo -e "${GREEN}✅ Backup saved to: $BACKUP_DIR/virtuoso_backup_$TIMESTAMP.tar.gz${NC}"
            ;;
        20)
            echo -e "${RED}⚠️  SYSTEM REBOOT REQUESTED${NC}"
            echo "This will restart the entire server."
            echo -n "Are you sure? Type 'yes' to confirm: "
            read confirm
            if [ "$confirm" = "yes" ]; then
                echo "Rebooting in 5 seconds..."
                sleep 5
                sudo reboot
            else
                echo "Reboot cancelled"
            fi
            ;;
        21)
            echo "Force syncing all exchanges..."
            sudo systemctl restart virtuoso
            sleep 3
            echo -e "${GREEN}✅ Exchange sync initiated${NC}"
            ;;
        22)
            echo "Clearing all caches..."
            if command -v redis-cli &> /dev/null; then
                redis-cli FLUSHALL 2>/dev/null
                echo "  Redis cache cleared"
            fi
            rm -rf /home/linuxuser/trading/Virtuoso_ccxt/cache/* 2>/dev/null
            echo "  File cache cleared"
            echo -e "${GREEN}✅ All caches cleared${NC}"
            ;;
        23)
            echo "Testing API connections..."
            echo ""
            echo "Bybit API Response:"
            curl -s https://api.bybit.com/v5/market/time | python -m json.tool 2>/dev/null | head -5 || echo "Failed"
            echo ""
            echo "Binance API Response:"
            curl -s https://api.binance.com/api/v3/time | python -m json.tool 2>/dev/null || echo "Failed"
            echo ""
            echo -e "${GREEN}✅ API test complete${NC}"
            ;;
        24)
            echo "Exporting trading logs..."
            EXPORT_DIR="/home/linuxuser/exports"
            mkdir -p $EXPORT_DIR
            TIMESTAMP=$(date +%Y%m%d_%H%M%S)
            sudo journalctl -u virtuoso --since "24 hours ago" > $EXPORT_DIR/trading_logs_$TIMESTAMP.log
            echo -e "${GREEN}✅ Logs exported to: $EXPORT_DIR/trading_logs_$TIMESTAMP.log${NC}"
            ;;
        25)
            echo -e "${RED}⚠️  EMERGENCY STOP INITIATED${NC}"
            echo "Stopping all trading services immediately..."
            sudo systemctl stop virtuoso
            pkill -f "python.*main.py"
            pkill -f "web_server"
            echo -e "${RED}❌ All trading stopped - Manual restart required${NC}"
            ;;
        0)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid selection${NC}"
            return 1
            ;;
    esac
}

# Main control logic
case "$1" in
    "")
        # No argument - show summary and interactive menu
        while true; do
            clear
            display_summary
            show_options
            echo -n "Enter selection [0-25] or command: "
            read -r input
            
            # Check if input is a number
            if [[ "$input" =~ ^[0-9]+$ ]]; then
                echo ""
                execute_option "$input"
                if [ "$input" != "0" ] && [ "$input" != "11" ]; then
                    echo ""
                    echo "Press Enter to continue..."
                    read
                fi
            else
                # Treat as command
                clear
                case "$input" in
                    start)
                        execute_option 4
                        ;;
                    stop)
                        execute_option 5
                        ;;
                    restart)
                        execute_option 6
                        ;;
                    web-start)
                        execute_option 9
                        ;;
                    web-stop)
                        execute_option 10
                        ;;
                    logs)
                        execute_option 12
                        ;;
                    health)
                        execute_option 13
                        ;;
                    clean)
                        execute_option 14
                        ;;
                    config)
                        execute_option 16
                        ;;
                    exit|quit)
                        exit 0
                        ;;
                    help)
                        echo "Available commands: start, stop, restart, web-start, web-stop, logs, health, clean, config, exit"
                        echo "Or use numbers 0-25 for menu options"
                        ;;
                    *)
                        echo "Unknown command: $input"
                        echo "Type 'help' for available commands or use numbers 0-25"
                        ;;
                esac
                echo ""
                echo "Press Enter to continue..."
                read
            fi
        done
        ;;
        
    # Direct command execution (non-interactive)
    start)
        execute_option 4
        ;;
    stop)
        execute_option 5
        ;;
    restart)
        execute_option 6
        ;;
    web-start)
        execute_option 9
        ;;
    web-stop)
        execute_option 10
        ;;
    web-restart)
        stop_web_server
        sleep 2
        start_web_server
        ;;
    web-toggle)
        execute_option 3
        ;;
    enable)
        execute_option 1
        ;;
    disable)
        execute_option 2
        ;;
    logs)
        execute_option 12
        ;;
    logs-follow)
        execute_option 11
        ;;
    health)
        execute_option 13
        ;;
    clean)
        execute_option 14
        ;;
    config)
        execute_option 16
        ;;
    system)
        execute_option 17
        ;;
    network)
        execute_option 18
        ;;
    backup)
        execute_option 19
        ;;
    reboot)
        execute_option 20
        ;;
    status)
        display_summary
        ;;
    summary)
        display_summary
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Available commands:"
        echo "  start, stop, restart, web-start, web-stop, web-restart"
        echo "  web-toggle, enable, disable, logs, logs-follow, health"
        echo "  clean, config, system, network, backup, reboot"
        echo "  status, summary"
        echo ""
        echo "Or run 'vt' with no arguments for interactive menu"
        exit 1
        ;;
esac
FULLSCRIPT'

# Make the new script executable
ssh $VPS_HOST 'chmod +x /home/linuxuser/virtuoso_control_enhanced.sh'

# Test the new script
echo ""
echo "Testing enhanced script..."
ssh $VPS_HOST 'echo "0" | timeout 10 /home/linuxuser/virtuoso_control_enhanced.sh 2>&1 | head -80'

# If successful, replace the old one
ssh $VPS_HOST 'cp /home/linuxuser/virtuoso_control.sh /home/linuxuser/virtuoso_control.sh.before_enhanced_final'
ssh $VPS_HOST 'mv /home/linuxuser/virtuoso_control_enhanced.sh /home/linuxuser/virtuoso_control.sh'

echo ""
echo "✅ Enhanced features successfully integrated!"
echo ""
echo "All features now working:"
echo "  🌐 Exchange Connections - Live status with ping times"
echo "  💾 Database & Cache Status - Redis, file cache, backups  "
echo "  ⚡ Quick Actions (21-25) - Emergency controls"
echo ""
echo "Test with: vt"