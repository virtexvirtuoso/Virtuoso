#!/bin/bash

# Virtuoso Trading Service Control with Enhanced Status Summary
# Version 5.0 - Detailed Python process monitoring

# Configuration file for web server auto-start
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
        # Default configuration
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
        # Check for uvicorn process on port 8001
        if pgrep -f "uvicorn.*8001" > /dev/null; then
            local pid=$(pgrep -f "uvicorn.*8001" | head -1)
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

# Function to display Python processes with descriptions
show_python_processes() {
    echo -e "${BOLD}🐍 Python Process Status${NC}"
    echo -e "${BOLD}──────────────────────${NC}"
    
    # Get all Python processes and parse them
    ps aux | grep python | grep -v grep | while read line; do
        local pid=$(echo $line | awk "{print \$2}")
        local mem=$(echo $line | awk "{print \$4}")
        local cpu=$(echo $line | awk "{print \$3}")
        local cmd=$(echo $line | awk "{print \$11, \$12, \$13, \$14, \$15}" | sed "s|/home/linuxuser/trading/Virtuoso_ccxt/||g")
        
        # Identify process type and provide description
        local description=""
        local status_color="${GREEN}"
        
        if [[ $cmd == *"src/main.py"* ]]; then
            if [[ $cmd == *"-u src/main.py"* ]] && [[ $cpu != "0.0" ]]; then
                description="Main Trading Engine (Primary Process)"
            else
                description="Main Trading Engine (Worker Process)"
            fi
        elif [[ $cmd == *"uvicorn src.web_server"* ]]; then
            description="Web Dashboard Server"
        elif [[ $cmd == *"bitcoin_beta_data_service_dynamic.py"* ]]; then
            description="Bitcoin Beta Dynamic Data Collector"
        elif [[ $cmd == *"bitcoin_beta_data_service.py"* ]]; then
            description="Bitcoin Beta Data Service"
        elif [[ $cmd == *"bitcoin_beta_calculator_service.py"* ]]; then
            description="Bitcoin Beta Calculator"
        elif [[ $cmd == *"market_metrics_service.py"* ]]; then
            description="Market Metrics Analyzer"
        elif [[ $cmd == *"ticker_cache_service.py"* ]]; then
            description="Price Ticker Cache Manager"
        elif [[ $cmd == *"btc_spot_linear_service.py"* ]]; then
            description="BTC Spot/Linear Arbitrage Monitor"
        elif [[ $cmd == *"cache_monitor_fix.py"* ]]; then
            description="Cache Performance Monitor"
        elif [[ $cmd == *"unattended-upgrades"* ]]; then
            description="System Update Service"
            status_color="${BLUE}"
        else
            description="Unknown Python Process"
            status_color="${YELLOW}"
        fi
        
        # Format memory and CPU usage
        local mem_int=$(echo $mem | cut -d. -f1)
        local cpu_formatted=$(printf "%.1f" $cpu)
        
        # Color code by resource usage
        if (( $(echo "$cpu > 10" | bc -l) )); then
            cpu_color="${RED}"
        elif (( $(echo "$cpu > 1" | bc -l) )); then
            cpu_color="${YELLOW}"
        else
            cpu_color="${GREEN}"
        fi
        
        if [ $mem_int -gt 10 ]; then
            mem_color="${RED}"
        elif [ $mem_int -gt 5 ]; then
            mem_color="${YELLOW}"
        else
            mem_color="${GREEN}"
        fi
        
        echo -e "  ${status_color}●${NC} ${BOLD}$description${NC}"
        echo -e "    PID: $pid | CPU: ${cpu_color}${cpu_formatted}%${NC} | Memory: ${mem_color}${mem}%${NC}"
    done
    
    echo ""
    
    # Summary stats
    local total_python=$(pgrep -c python 2>/dev/null || echo 0)
    local total_virtuoso=$(pgrep -cf "trading/Virtuoso_ccxt" 2>/dev/null || echo 0)
    local total_cpu=$(ps aux | grep python | grep -v grep | awk "{sum += \$3} END {printf \"%.1f\", sum}")
    local total_mem=$(ps aux | grep python | grep -v grep | awk "{sum += \$4} END {printf \"%.1f\", sum}")
    
    echo -e "${BOLD}📈 Process Summary${NC}"
    echo -e "${BOLD}────────────────${NC}"
    echo -e "Total Python:    $total_python processes"
    echo -e "Virtuoso Procs:  $total_virtuoso processes"
    echo -e "Combined CPU:    ${total_cpu}%"
    echo -e "Combined Memory: ${total_mem}%"
}

# Function to check web server status
check_web_server() {
    # Check if uvicorn web server process is running on port 8001
    if pgrep -f "uvicorn.*8001" > /dev/null; then
        WEB_PID=$(pgrep -f "uvicorn.*8001" | head -1)
        echo -e "${GREEN}● Web server is running (PID: $WEB_PID)${NC}"
        
        # Check if port 8001 is listening
        if sudo lsof -i:8001 > /dev/null 2>&1; then
            echo -e "${GREEN}  └─ Port 8001 is listening${NC}"
        else
            echo -e "${YELLOW}  └─ Warning: Process running but port 8001 not listening${NC}"
        fi
    else
        echo -e "${RED}● Web server is not running${NC}"
    fi
    
    # Check web server endpoint health on port 8001
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/health 2>/dev/null | grep -q "200"; then
        echo -e "${GREEN}  └─ Health endpoint responding${NC}"
    else
        echo -e "${YELLOW}  └─ Health endpoint not responding${NC}"
    fi
    
    # Show auto-start status
    load_config
    if [ "$WEB_SERVER_AUTO_START" = "enabled" ]; then
        echo -e "${BLUE}  └─ Auto-start: ENABLED${NC}"
    else
        echo -e "${YELLOW}  └─ Auto-start: DISABLED${NC}"
    fi
}

# Function to start web server
start_web_server() {
    echo "Starting web server..."
    
    # Kill any existing web server processes
    pkill -f "uvicorn.*8001" 2>/dev/null
    sleep 2
    
    # Start web server in background using uvicorn
    cd /home/linuxuser/trading/Virtuoso_ccxt
    nohup /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python3.11 /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/uvicorn src.web_server:app --host 0.0.0.0 --port 8001 > /home/linuxuser/web_server.log 2>&1 &
    
    sleep 3
    
    # Verify it started
    if pgrep -f "uvicorn.*8001" > /dev/null; then
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
    pkill -f "uvicorn.*8001" 2>/dev/null
    sleep 2
    
    if ! pgrep -f "uvicorn.*8001" > /dev/null; then
        echo -e "${GREEN}✅ Web server stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  Web server still running, forcing kill${NC}"
        pkill -9 -f "uvicorn.*8001" 2>/dev/null
    fi
}

# Function to check additional services
check_additional_services() {
    echo -e "${BOLD}📦 Trading Services Status${NC}"
    echo -e "${BOLD}────────────────────────${NC}"
    
    # Check Bitcoin Beta Data Service
    if pgrep -f "bitcoin_beta_data_service_dynamic" > /dev/null; then
        local pid=$(pgrep -f "bitcoin_beta_data_service_dynamic" | head -1)
        echo -e "Bitcoin Beta Dynamic:   ${GREEN}● RUNNING${NC} (PID: $pid)"
    else
        echo -e "Bitcoin Beta Dynamic:   ${RED}● STOPPED${NC}"
    fi
    
    # Check Bitcoin Beta Data Service
    if pgrep -f "bitcoin_beta_data_service.py" > /dev/null; then
        local pid=$(pgrep -f "bitcoin_beta_data_service.py" | head -1)
        echo -e "Bitcoin Beta Data:      ${GREEN}● RUNNING${NC} (PID: $pid)"
    else
        echo -e "Bitcoin Beta Data:      ${RED}● STOPPED${NC}"
    fi
    
    # Check Bitcoin Beta Calculator
    if pgrep -f "bitcoin_beta_calculator_service" > /dev/null; then
        local pid=$(pgrep -f "bitcoin_beta_calculator_service" | head -1)
        echo -e "Bitcoin Beta Calculator: ${GREEN}● RUNNING${NC} (PID: $pid)"
    else
        echo -e "Bitcoin Beta Calculator: ${RED}● STOPPED${NC}"
    fi
    
    # Check Market Metrics Service
    if pgrep -f "market_metrics_service" > /dev/null; then
        local pid=$(pgrep -f "market_metrics_service" | head -1)
        echo -e "Market Metrics:         ${GREEN}● RUNNING${NC} (PID: $pid)"
    else
        echo -e "Market Metrics:         ${RED}● STOPPED${NC}"
    fi
    
    # Check Ticker Cache Service
    if pgrep -f "ticker_cache_service" > /dev/null; then
        local pid=$(pgrep -f "ticker_cache_service" | head -1)
        echo -e "Ticker Cache:           ${GREEN}● RUNNING${NC} (PID: $pid)"
    else
        echo -e "Ticker Cache:           ${RED}● STOPPED${NC}"
    fi
    
    # Check BTC Spot Linear Service
    if pgrep -f "btc_spot_linear_service" > /dev/null; then
        local pid=$(pgrep -f "btc_spot_linear_service" | head -1)
        echo -e "BTC Spot/Linear:        ${GREEN}● RUNNING${NC} (PID: $pid)"
    else
        echo -e "BTC Spot/Linear:        ${RED}● STOPPED${NC}"
    fi
    
    # Check Cache Monitor
    if pgrep -f "cache_monitor_fix" > /dev/null; then
        local pid=$(pgrep -f "cache_monitor_fix" | head -1)
        echo -e "Cache Monitor:          ${GREEN}● RUNNING${NC} (PID: $pid)"
    else
        echo -e "Cache Monitor:          ${RED}● STOPPED${NC}"
    fi
}

# Function to check main service status
check_main_service() {
    if sudo systemctl is-active virtuoso > /dev/null; then
        local main_pid=$(sudo systemctl show virtuoso --property=MainPID | cut -d= -f2)
        echo -e "${GREEN}● Virtuoso service is running (PID: $main_pid)${NC}"
        
        # Check if service is enabled
        if sudo systemctl is-enabled virtuoso > /dev/null 2>&1; then
            echo -e "${BLUE}  └─ Auto-start: ENABLED${NC}"
        else
            echo -e "${YELLOW}  └─ Auto-start: DISABLED${NC}"
        fi
        
        # Check API endpoint on port 8003
        if sudo lsof -i:8003 > /dev/null 2>&1; then
            echo -e "${GREEN}  └─ API port 8003 is listening${NC}"
        else
            echo -e "${YELLOW}  └─ Warning: API port 8003 not listening${NC}"
        fi
    else
        echo -e "${RED}● Virtuoso service is not running${NC}"
        
        # Check if service is enabled
        if sudo systemctl is-enabled virtuoso > /dev/null 2>&1; then
            echo -e "${BLUE}  └─ Auto-start: ENABLED${NC}"
        else
            echo -e "${YELLOW}  └─ Auto-start: DISABLED${NC}"
        fi
    fi
}

# Function to display comprehensive summary
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
    if pgrep -f "uvicorn.*8001" > /dev/null; then
        local web_uptime=$(get_uptime web)
        local web_pid=$(pgrep -f "uvicorn.*8001" | head -1)
        echo -e "Web Server:      ${GREEN}● RUNNING${NC} (uptime: $web_uptime, PID: $web_pid)"
    else
        echo -e "Web Server:      ${RED}● STOPPED${NC}"
    fi
    
    # Dashboard Access
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/dashboard 2>/dev/null | grep -q "200"; then
        echo -e "Dashboard:       ${GREEN}● ACCESSIBLE${NC} (http://5.223.63.4:8001/dashboard)"
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
    
    # Count processes with more detail
    local total_python=$(pgrep -c python 2>/dev/null || echo 0)
    local virtuoso_python=$(pgrep -cf "trading/Virtuoso_ccxt" 2>/dev/null || echo 0)
    echo -e "Python Procs:    $total_python active ($virtuoso_python Virtuoso)"
    
    echo ""
    echo -e "${BOLD}────────────────────────────────────────────────────${NC}"
    echo ""
    
    # Show detailed Python processes
    show_python_processes
    echo ""
    
    # Exchange Connections
    echo -e "${BOLD}🌐 Exchange Connections${NC}"
    echo -e "${BOLD}──────────────────────${NC}"
    
    # Check Bybit connection
    local bybit_ping=$(curl -s -w "\n%{time_total}" -o /dev/null https://api.bybit.com/v5/market/time 2>/dev/null | tail -1)
    if [ ! -z "$bybit_ping" ] && [ "$bybit_ping" != "0.000000" ]; then
        bybit_ping=$(echo "$bybit_ping * 1000" | bc | cut -d. -f1)
        echo -e "Bybit:           ${GREEN}✅ CONNECTED${NC} (ping: ${bybit_ping}ms)"
    else
        echo -e "Bybit:           ${RED}❌ DISCONNECTED${NC}"
    fi
    
    # Check Binance connection
    local binance_ping=$(curl -s -w "\n%{time_total}" -o /dev/null https://api.binance.com/api/v3/time 2>/dev/null | tail -1)
    if [ ! -z "$binance_ping" ] && [ "$binance_ping" != "0.000000" ]; then
        binance_ping=$(echo "$binance_ping * 1000" | bc | cut -d. -f1)
        echo -e "Binance:         ${GREEN}✅ CONNECTED${NC} (ping: ${binance_ping}ms)"
    else
        echo -e "Binance:         ${RED}❌ DISCONNECTED${NC}"
    fi
    
    # Check WebSocket status
    if [ -f /home/linuxuser/trading/Virtuoso_ccxt/logs/main.log ]; then
        local ws_last=$(grep -i websocket /home/linuxuser/trading/Virtuoso_ccxt/logs/main.log | tail -1 | cut -d" " -f1-2 2>/dev/null)
        if [ ! -z "$ws_last" ]; then
            local ws_epoch=$(date -d "$ws_last" +%s 2>/dev/null || echo 0)
            local now_epoch=$(date +%s)
            local ws_age=$((now_epoch - ws_epoch))
            if [ $ws_age -lt 60 ]; then
                echo -e "WebSocket:       ${GREEN}✅ ACTIVE${NC}"
            elif [ $ws_age -lt 300 ]; then
                echo -e "WebSocket:       ${YELLOW}⚠️  NO RECENT DATA${NC}"
            else
                echo -e "WebSocket:       ${RED}❌ INACTIVE${NC}"
            fi
            echo -e "Last Data:       ${ws_age} seconds ago"
        else
            echo -e "WebSocket:       ${YELLOW}⚠️  NO DATA${NC}"
        fi
    else
        echo -e "WebSocket:       ${YELLOW}⚠️  NO LOG FILE${NC}"
    fi
    
    echo ""
    
    # Database & Cache Status
    echo -e "${BOLD}💾 Database & Cache Status${NC}"
    echo -e "${BOLD}──────────────────────────${NC}"
    
    # Check Redis
    if redis-cli ping 2>/dev/null | grep -q PONG; then
        local redis_info=$(redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d r)
        local redis_keys=$(redis-cli dbsize 2>/dev/null)
        echo -e "Redis Cache:     ${GREEN}✅ CONNECTED${NC} ($redis_keys keys, $redis_info)"
    else
        echo -e "Redis Cache:     ${RED}❌ DISCONNECTED${NC}"
    fi
    
    # Check file cache
    if [ -d /home/linuxuser/trading/Virtuoso_ccxt/cache ]; then
        local cache_files=$(find /home/linuxuser/trading/Virtuoso_ccxt/cache -type f 2>/dev/null | wc -l)
        local cache_size=$(du -sh /home/linuxuser/trading/Virtuoso_ccxt/cache 2>/dev/null | cut -f1)
        echo -e "File Cache:      ${GREEN}✅ ACTIVE${NC} ($cache_files files, $cache_size)"
    else
        echo -e "File Cache:      ${YELLOW}⚠️  NO CACHE DIR${NC}"
    fi
    
    # Check logs
    if [ -d /home/linuxuser/trading/Virtuoso_ccxt/logs ]; then
        local main_log_size=$(du -sh /home/linuxuser/trading/Virtuoso_ccxt/logs/main.log 2>/dev/null | cut -f1 || echo "0")
        local web_log_size=$(du -sh /home/linuxuser/web_server.log 2>/dev/null | cut -f1 || echo "0")
        echo -e "Log Storage:     Main: $main_log_size, Web: $web_log_size"
    fi
    
    # Check backup
    local last_backup=$(ls -lt /home/linuxuser/trading/backups 2>/dev/null | head -2 | tail -1 | awk "{print \$6\" \"\$7\" \"\$8}" || echo "Never")
    echo -e "Last Backup:     $last_backup"
    
    echo ""
    echo -e "${BOLD}────────────────────────────────────────────────────${NC}"
}

# Interactive menu function
show_menu() {
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
    read -p "Select option: " choice
    
    case $choice in
        1) $0 enable ;;
        2) $0 disable ;;
        3) $0 web-toggle ;;
        4) $0 start ;;
        5) $0 stop ;;
        6) $0 restart ;;
        7) sudo systemctl start virtuoso ;;
        8) sudo systemctl stop virtuoso ;;
        9) start_web_server ;;
        10) stop_web_server ;;
        11) $0 logs-follow ;;
        12) $0 logs ;;
        13) $0 health ;;
        14) $0 clean ;;
        15) $0 kill-all ;;
        16) $0 config ;;
        17) $0 sysinfo ;;
        18) $0 nettest ;;
        19) $0 backup ;;
        20) echo "Rebooting server..." && sudo reboot ;;
        21) echo "Force syncing exchanges..." && curl -X POST http://localhost:8001/api/sync ;;
        22) echo "Clearing all caches..." && redis-cli FLUSHALL && rm -rf /home/linuxuser/trading/Virtuoso_ccxt/cache/* ;;
        23) $0 test-apis ;;
        24) $0 export-logs ;;
        25) echo "Emergency stop!" && $0 stop && pkill -9 python ;;
        0) exit 0 ;;
        *) echo -e "${RED}Invalid option${NC}" ;;
    esac
}

# Main control logic
case "$1" in
    status)
        display_summary
        echo ""
        check_additional_services
        echo ""
        echo -e "${BOLD}📋 Detailed Service Status${NC}"
        echo -e "${BOLD}────────────────────────${NC}"
        echo ""
        check_main_service
        echo ""
        check_web_server
        ;;
        
    processes)
        show_python_processes
        ;;
        
    start)
        echo "Starting services..."
        sudo systemctl start virtuoso
        sleep 5
        
        # Check if web server auto-start is enabled
        load_config
        if [ "$WEB_SERVER_AUTO_START" = "enabled" ]; then
            start_web_server
        else
            echo -e "${YELLOW}ℹ️  Web server auto-start is disabled. Use 'web-start' to start manually.${NC}"
        fi
        
        echo ""
        display_summary
        ;;
        
    stop)
        echo "Stopping all services..."
        stop_web_server
        sudo systemctl stop virtuoso
        echo -e "${GREEN}✅ All services stopped${NC}"
        ;;
        
    restart)
        echo "Restarting all services..."
        $0 stop
        sleep 5
        $0 start
        ;;
        
    web-start)
        start_web_server
        ;;
        
    web-stop)
        stop_web_server
        ;;
        
    web-restart)
        stop_web_server
        sleep 2
        start_web_server
        ;;
        
    web-toggle)
        load_config
        if [ "$WEB_SERVER_AUTO_START" = "enabled" ]; then
            WEB_SERVER_AUTO_START="disabled"
            echo -e "${YELLOW}⚠️  Web server auto-start DISABLED${NC}"
            echo "The web server will NOT start automatically with the main service."
        else
            WEB_SERVER_AUTO_START="enabled"
            echo -e "${GREEN}✅ Web server auto-start ENABLED${NC}"
            echo "The web server will start automatically with the main service."
        fi
        save_config
        ;;
        
    enable)
        echo "Enabling auto-start for main service..."
        sudo systemctl enable virtuoso
        echo -e "${GREEN}✅ Main service will start automatically on boot${NC}"
        ;;
        
    disable)
        echo "Disabling auto-start for main service..."
        sudo systemctl disable virtuoso
        echo -e "${YELLOW}⚠️  Main service will NOT start automatically on boot${NC}"
        ;;
        
    logs)
        echo -e "${BOLD}=== Main Service Logs (last 20 lines) ===${NC}"
        sudo journalctl -u virtuoso -n 20 --no-pager
        echo ""
        echo -e "${BOLD}=== Web Server Logs (last 20 lines) ===${NC}"
        tail -n 20 /home/linuxuser/web_server.log 2>/dev/null || echo "No web server logs found"
        ;;
        
    logs-follow)
        echo "Following logs (Ctrl+C to exit)..."
        echo "Main service logs in real-time:"
        sudo journalctl -u virtuoso -f
        ;;
        
    health)
        echo -e "${BOLD}🏥 Performing Health Check...${NC}"
        echo ""
        
        display_summary
        echo ""
        check_additional_services
        echo ""
        
        # API Endpoint Checks
        echo -e "${BOLD}🌐 API Endpoint Tests${NC}"
        echo -e "${BOLD}──────────────────${NC}"
        
        # Health endpoint on port 8001
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/health 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            echo -e "/api/health endpoint:     ${GREEN}✅ OK (HTTP 200)${NC}"
        else
            echo -e "/api/health endpoint:     ${RED}❌ Failed (HTTP $HTTP_CODE)${NC}"
        fi
        
        # Dashboard endpoint on port 8001
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/dashboard 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            echo -e "/dashboard endpoint:      ${GREEN}✅ OK (HTTP 200)${NC}"
        else
            echo -e "/dashboard endpoint:      ${YELLOW}⚠️  HTTP $HTTP_CODE${NC}"
        fi
        
        # Mobile endpoint on port 8001
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/mobile 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            echo -e "/mobile endpoint:         ${GREEN}✅ OK (HTTP 200)${NC}"
        else
            echo -e "/mobile endpoint:         ${YELLOW}⚠️  HTTP $HTTP_CODE${NC}"
        fi
        
        # API endpoints on port 8003 (main service)
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/api/market/overview 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            echo -e "/api/market/overview:     ${GREEN}✅ OK (HTTP 200)${NC}"
        else
            echo -e "/api/market/overview:     ${YELLOW}⚠️  HTTP $HTTP_CODE${NC}"
        fi
        
        echo ""
        echo -e "${BOLD}✅ Health check complete${NC}"
        ;;
        
    summary)
        display_summary
        show_menu
        ;;
        
    sysinfo)
        echo -e "${BOLD}System Information${NC}"
        echo "=================="
        uname -a
        echo ""
        free -h
        echo ""
        df -h
        echo ""
        top -bn1 | head -20
        ;;
        
    nettest)
        echo -e "${BOLD}Network Connectivity Test${NC}"
        echo "========================="
        echo -n "Bybit API: "
        curl -s -o /dev/null -w "%{http_code} (%.3fs)\n" https://api.bybit.com/v5/market/time
        echo -n "Binance API: "
        curl -s -o /dev/null -w "%{http_code} (%.3fs)\n" https://api.binance.com/api/v3/time
        echo -n "Local API (8001): "
        curl -s -o /dev/null -w "%{http_code} (%.3fs)\n" http://localhost:8001/api/health
        echo -n "Local API (8003): "
        curl -s -o /dev/null -w "%{http_code} (%.3fs)\n" http://localhost:8003/api/health
        ;;
        
    test-apis)
        echo -e "${BOLD}Testing All API Connections${NC}"
        echo "==========================="
        
        echo -n "Main API Health: "
        curl -s http://localhost:8003/api/health | jq -r ".status" 2>/dev/null || echo "Failed"
        
        echo -n "Web Server Health: "
        curl -s http://localhost:8001/api/health | jq -r ".status" 2>/dev/null || echo "Failed"
        
        echo -n "Market Overview: "
        curl -s http://localhost:8001/api/market/overview | jq -r "if .btc_price then \"OK\" else \"Failed\" end" 2>/dev/null || echo "Failed"
        
        echo -n "Signals: "
        curl -s http://localhost:8001/api/signals | jq -r "if .signals then \"OK\" else \"Failed\" end" 2>/dev/null || echo "Failed"
        ;;
        
    export-logs)
        echo "Exporting trading logs..."
        EXPORT_DIR="/home/linuxuser/trading/exports/logs_$(date +%Y%m%d_%H%M%S)"
        mkdir -p $EXPORT_DIR
        cp /home/linuxuser/trading/Virtuoso_ccxt/logs/*.log $EXPORT_DIR/
        tar -czf $EXPORT_DIR.tar.gz $EXPORT_DIR
        echo -e "${GREEN}✅ Logs exported to $EXPORT_DIR.tar.gz${NC}"
        ;;
        
    backup)
        echo "Creating configuration backup..."
        BACKUP_DIR="/home/linuxuser/trading/backups/backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p $BACKUP_DIR
        cp -r /home/linuxuser/trading/Virtuoso_ccxt/config $BACKUP_DIR/
        cp /home/linuxuser/.virtuoso_config $BACKUP_DIR/
        tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
        echo -e "${GREEN}✅ Backup created at $BACKUP_DIR.tar.gz${NC}"
        ;;
        
    kill-all)
        echo -e "${RED}Killing all Python processes...${NC}"
        pkill -9 python
        echo -e "${GREEN}✅ All Python processes terminated${NC}"
        ;;
        
    config)
        echo -e "${BOLD}Current Configuration:${NC}"
        echo "====================="
        load_config
        echo -e "Main Service Auto-start: $(sudo systemctl is-enabled virtuoso 2>/dev/null || echo 'disabled')"
        echo -e "Web Server Auto-start:   $WEB_SERVER_AUTO_START"
        echo ""
        echo "Toggle commands:"
        echo "  $0 enable      - Enable main service auto-start on boot"
        echo "  $0 disable     - Disable main service auto-start on boot"
        echo "  $0 web-toggle  - Toggle web server auto-start with main service"
        ;;
        
    clean)
        echo "Cleaning up temporary files and logs..."
        rm -f /tmp/virtuoso.lock
        sudo journalctl --vacuum-time=7d
        echo > /home/linuxuser/web_server.log
        echo -e "${GREEN}✅ Cleanup complete${NC}"
        ;;
        
    "")
        # No argument provided, show summary and menu
        display_summary
        show_menu
        ;;
        
    help|--help|-h)
        echo -e "${BOLD}${CYAN}====================================================${NC}"
        echo -e "${BOLD}${CYAN}      Virtuoso Trading Service Control v5.0        ${NC}"
        echo -e "${BOLD}${CYAN}====================================================${NC}"
        echo ""
        echo -e "${BOLD}OVERVIEW:${NC}"
        echo "Complete management interface for Virtuoso Trading System"
        echo "Monitors and controls all trading services, processes, and resources"
        echo ""
        echo -e "${BOLD}DASHBOARD ACCESS:${NC}"
        echo -e "${GREEN}http://5.223.63.4:8001/dashboard${NC} - Main trading dashboard"
        echo ""
        echo -e "${BOLD}QUICK START:${NC}"
        echo "  vt              - Interactive control panel with menu"
        echo "  vt status       - Complete system status report"
        echo "  vt health       - Run comprehensive health check"
        echo ""
        echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${BOLD}📊 MONITORING COMMANDS${NC}"
        echo -e "${BOLD}────────────────────${NC}"
        echo "  status          Show comprehensive system status"
        echo "  summary         Quick overview with interactive menu"
        echo "  processes       Detailed Python process monitoring"
        echo "  health          Complete health check (APIs, services, connections)"
        echo "  logs            Show recent service logs"
        echo "  logs-follow     Follow logs in real-time (Ctrl+C to exit)"
        echo "  sysinfo         System information (CPU, memory, disk)"
        echo "  nettest         Network connectivity tests"
        echo "  test-apis       Test all API endpoints"
        echo ""
        echo -e "${BOLD}🚀 SERVICE MANAGEMENT${NC}"
        echo -e "${BOLD}───────────────────${NC}"
        echo "  start           Start all services (main + web if enabled)"
        echo "  stop            Stop all services gracefully"
        echo "  restart         Restart all services"
        echo "  web-start       Start web server only"
        echo "  web-stop        Stop web server only"
        echo "  web-restart     Restart web server only"
        echo ""
        echo -e "${BOLD}⚙️  CONFIGURATION${NC}"
        echo -e "${BOLD}──────────────${NC}"
        echo "  enable          Enable main service auto-start on boot"
        echo "  disable         Disable main service auto-start on boot"
        echo "  web-toggle      Toggle web server auto-start with main service"
        echo "  config          Show current configuration settings"
        echo ""
        echo -e "${BOLD}🔧 MAINTENANCE & UTILITIES${NC}"
        echo -e "${BOLD}─────────────────────────${NC}"
        echo "  clean           Clean temporary files and old logs"
        echo "  backup          Create configuration backup"
        echo "  export-logs     Export trading logs to archive"
        echo "  kill-all        Emergency: Kill all Python processes"
        echo ""
        echo -e "${BOLD}📦 MONITORED SERVICES${NC}"
        echo -e "${BOLD}───────────────────${NC}"
        echo "  • Main Trading Engine (Primary + Worker processes)"
        echo "  • Web Dashboard Server (Port 8001)"
        echo "  • Bitcoin Beta Services (Dynamic, Data, Calculator)"
        echo "  • Market Metrics Analyzer"
        echo "  • Price Ticker Cache Manager"
        echo "  • BTC Spot/Linear Arbitrage Monitor"
        echo "  • Cache Performance Monitor"
        echo ""
        echo -e "${BOLD}🌐 NETWORK ENDPOINTS${NC}"
        echo -e "${BOLD}──────────────────${NC}"
        echo "  Dashboard:      http://5.223.63.4:8001/dashboard"
        echo "  Mobile:         http://5.223.63.4:8001/mobile"
        echo "  API Health:     http://5.223.63.4:8001/api/health"
        echo "  Market Data:    http://5.223.63.4:8001/api/market/overview"
        echo "  Trading Signals: http://5.223.63.4:8001/api/signals"
        echo ""
        echo -e "${BOLD}🎮 INTERACTIVE FEATURES${NC}"
        echo -e "${BOLD}──────────────────────${NC}"
        echo "When you run vt without arguments, you get an interactive menu with:"
        echo "  • Real-time service status summary"
        echo "  • System resource monitoring"
        echo "  • Exchange connection status with ping times"
        echo "  • Redis cache and file cache statistics"
        echo "  • 25 quick action options"
        echo "  • Color-coded process monitoring"
        echo ""
        echo -e "${BOLD}⚡ QUICK ACTIONS (Available in Interactive Mode)${NC}"
        echo -e "${BOLD}───────────────────────────────────────────────${NC}"
        echo "  21) Force sync all exchanges"
        echo "  22) Clear all caches (Redis + File)"
        echo "  23) Test all API connections"
        echo "  24) Export trading logs"
        echo "  25) Emergency stop trading"
        echo ""
        echo -e "${BOLD}🚨 EMERGENCY PROCEDURES${NC}"
        echo -e "${BOLD}─────────────────────${NC}"
        echo "  Service Down:     vt restart"
        echo "  High CPU Usage:   vt processes (identify problem)"
        echo "  API Not Responding: vt test-apis (diagnose)"
        echo "  Complete Reset:   vt stop && vt kill-all && vt start"
        echo "  System Reboot:    Use option 20 in interactive menu"
        echo ""
        echo -e "${BOLD}📈 RESOURCE MONITORING${NC}"
        echo -e "${BOLD}────────────────────${NC}"
        echo "The system automatically monitors:"
        echo "  • CPU usage per process (color-coded: Green < 1%, Yellow 1-10%, Red > 10%)"
        echo "  • Memory usage per process (Green < 5%, Yellow 5-10%, Red > 10%)"
        echo "  • Exchange API response times"
        echo "  • WebSocket connection status"
        echo "  • Redis cache performance"
        echo "  • File cache statistics"
        echo "  • Log file sizes"
        echo ""
        echo -e "${BOLD}🔍 EXAMPLES${NC}"
        echo -e "${BOLD}─────────${NC}"
        echo "  vt                    # Interactive control panel"
        echo "  vt status             # Full system status"
        echo "  vt processes          # Process details only"
        echo "  vt health             # Complete health check"
        echo "  vt restart            # Restart all services"
        echo "  vt logs-follow        # Watch logs in real-time"
        echo ""
        echo -e "${BOLD}💡 TIPS${NC}"
        echo -e "${BOLD}────${NC}"
        echo "• Run vt regularly to monitor system health"
        echo "• Use vt health before and after deployments"
        echo "• Check vt processes if system is slow"
        echo "• Use vt nettest if exchanges seem unresponsive"
        echo "• Set up a cron job: vt backup for daily backups"
        echo ""
        echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BOLD}Version: 5.0 | Updated: $(date +%Y-%m-%d) | Virtuoso Trading System${NC}"
        echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        ;;
        
    *)
        echo -e "${BOLD}${CYAN}Virtuoso Trading Service Control v5.0${NC}"
        echo ""
        echo -e "${BOLD}Usage:${NC} vt [command]"
        echo ""
        echo -e "${BOLD}Quick Commands:${NC}"
        echo "  vt              Interactive control panel with menu"
        echo "  vt status       Complete system status report"
        echo "  vt health       Comprehensive health check"
        echo "  vt processes    Detailed Python process monitoring"
        echo "  vt help         Show detailed help and documentation"
        echo ""
        echo -e "${BOLD}Service Management:${NC}"
        echo "  start, stop, restart    Control all services"
        echo "  web-start, web-stop     Control web server only"
        echo ""
        echo -e "${BOLD}Monitoring:${NC}"
        echo "  logs, logs-follow       View service logs"
        echo "  nettest, test-apis      Test connectivity"
        echo "  sysinfo                 System information"
        echo ""
        echo -e "${BOLD}Configuration:${NC}"
        echo "  enable, disable         Auto-start settings"
        echo "  config, backup          Configuration management"
        echo ""
        echo -e "${GREEN}💡 Run vt help for complete documentation${NC}"
        echo -e "${GREEN}🌐 Dashboard: http://5.223.63.4:8001/dashboard${NC}"
        exit 1
        ;;
esac
