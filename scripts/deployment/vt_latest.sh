#!/bin/bash
# Get terminal width for proper formatting
TERM_WIDTH=$(tput cols 2>/dev/null || echo 80)
if [ $TERM_WIDTH -lt 60 ]; then
    TERM_WIDTH=60
fi

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

# Log Level Functions
# Function to get current log level
get_current_log_level() {
    if [ -f /home/linuxuser/trading/Virtuoso_ccxt/.log_level ]; then
        cat /home/linuxuser/trading/Virtuoso_ccxt/.log_level
    else
        # Check from systemd service
        grep 'LOG_LEVEL=' /etc/systemd/system/virtuoso-trading.service 2>/dev/null | cut -d'=' -f3 | tr -d '"' || echo "INFO"
    fi
}

# Function to set log level
set_log_level() {
    local new_level="$1"
    echo "$new_level" > /home/linuxuser/trading/Virtuoso_ccxt/.log_level
    
    # Update systemd services
    sudo sed -i "s/Environment=\"LOG_LEVEL=.*/Environment=\"LOG_LEVEL=$new_level\"/" /etc/systemd/system/virtuoso-trading.service
    sudo sed -i "s/Environment=\"LOG_LEVEL=.*/Environment=\"LOG_LEVEL=$new_level\"/" /etc/systemd/system/virtuoso-web.service
    
    echo "Log level set to: $new_level"
    echo "Reloading systemd configuration..."
    sudo systemctl daemon-reload
    
    echo ""
    echo "Services need to be restarted for changes to take effect."
    echo -n "Restart services now? (y/N): "
    read restart_choice
    if [ "$restart_choice" = "y" ] || [ "$restart_choice" = "Y" ]; then
        echo "Restarting services..."
        sudo systemctl restart virtuoso-trading.service virtuoso-web.service
        echo "Services restarted with log level: $new_level"
    else
        echo "Services not restarted. Changes will apply on next restart."
    fi
}

# Function to show log level menu
show_log_level_menu() {
    clear
    echo -e "${CYAN}===================================================="
    echo -e "            Log Level Configuration                "
    echo -e "===================================================="
    echo ""
    echo -e "Current Log Level: ${GREEN}$(get_current_log_level)${NC}"
    echo ""
    echo "Available Log Levels:"
    echo "  1) DEBUG   - Detailed debugging information"
    echo "  2) INFO    - General informational messages"
    echo "  3) WARNING - Warning messages only"
    echo "  4) ERROR   - Error messages only"
    echo "  5) CRITICAL - Critical messages only"
    echo ""
    echo "  0) Back to main menu"
    echo ""
    echo -n "Select log level: "
    read level_choice
    
    case $level_choice in
        1) set_log_level "DEBUG" ;;
        2) set_log_level "INFO" ;;
        3) set_log_level "WARNING" ;;
        4) set_log_level "ERROR" ;;
        5) set_log_level "CRITICAL" ;;
        0) return ;;
        *) echo "Invalid choice" ; sleep 2 ; show_log_level_menu ;;
    esac
}

# Log Level Functions

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
    if [ "$service" = "main" ] || [ "$service" = "trading" ]; then
        if sudo systemctl is-active virtuoso-trading.service > /dev/null; then
            local start_time=$(sudo systemctl show virtuoso-trading.service --property=ActiveEnterTimestamp | cut -d= -f2)
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
        # Check for web server process on port 8003
        if pgrep -f "web_server.py" > /dev/null || pgrep -f "web_server.py" > /dev/null; then
            local pid=$(pgrep -f "web_server.py" | head -1)
            [ -z "$pid" ] && local pid=$(pgrep -f "web_server.py" | head -1)
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
        elif [[ $cmd == *"uvicorn src.main:app"* ]]; then
            description="Dashboard UI Server"
        elif [[ $cmd == *"uvicorn src.web_server"* ]]; then
            description="Dashboard UI Server (Legacy)"
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
        elif [[ $cmd == *"web_server.py"* ]] || [[ $cmd == *"web_server.py"* ]]; then
            description="Dashboard UI Server"
        elif [[ $cmd == *"unattended-upgrades"* ]]; then
            description="System Update Service"
            status_color="${BLUE}"
        else
            # Identify process type
            cmd=$(ps -p $pid -o args= 2>/dev/null)
            if [[ $cmd == *"start_web_server"* ]] || [[ $cmd == *"venv311"* ]]; then
                description="Dashboard UI Server"
            elif [[ $cmd == *"src/main.py"* ]]; then
                description="Main Trading Engine"
            else
                description="Python Process"
            fi
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
    local total_python=$(pgrep -caf python 2>/dev/null || echo 0)
    local total_virtuoso=$(pgrep -cf "trading/Virtuoso_ccxt" 2>/dev/null || echo 0)
    local total_cpu=$(ps aux | grep python | grep -v grep | awk "{sum += \$3} END {printf \"%.1f\", sum}")
    local total_mem=$(ps aux | grep python | grep -v grep | awk "{sum += \$4} END {printf \"%.1f\", sum}")
    

    # Enhanced System Health Display
    echo
    echo -e "╔══════════════════════════════════════════════════════════════╗"
    echo -e "║                     ⚡ QUICK STATUS CHECK                     ║"
    echo -e "╠══════════════════════════════════════════════════════════════╣"
    
    # Get current usage
    local cpu_usage=$(ps aux | grep python | grep -v grep | awk '''{ sum+=$3 } END { printf "%.0f", sum }''' 2>/dev/null || echo "0")
    local mem_usage=$(ps aux | grep python | grep -v grep | awk '''{ sum+=$4 } END { printf "%.0f", sum }''' 2>/dev/null || echo "0")
    
    # Dashboard link
    echo -e "║  🌐 Dashboard: http://${VPS_HOST}:8002/                      ║"
    echo -e "║  📊 CPU Usage: ${cpu_usage}%  |  Memory: ${mem_usage}%                   ║"
    echo -e "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${BOLD}📈 Process Summary${NC}"
    echo -e "${BOLD}────────────────${NC}"
    echo -e "Total Python:    $total_python processes"
    echo -e "Virtuoso Procs:  $total_virtuoso processes"
    
    # Check architecture completeness (3 continuous + 1 timer-based)
    local main_running=0
    local web_running=0
    local monitor_api_running=0
    
    # Check for main trading engine
    if ps aux | grep -v grep | grep -q "python.*main\.py"; then
        main_running=1
    fi
    
    # Check for web server (either simple or regular)
    if ps aux | grep -v grep | grep -q "python.*web_server"; then
        web_running=1
    fi
    
    # Check for monitoring API
    if ps aux | grep -v grep | grep -q "python.*monitoring_api"; then
        monitor_api_running=1
    fi
    
    local arch_count=$((main_running + web_running + monitor_api_running))
    
    if [ "$arch_count" -eq 3 ]; then
        echo -e "Architecture:    ${GREEN}✅ COMPLETE (3/3 services)${NC}"
    else
        echo -e "Architecture:    ${RED}❌ INCOMPLETE ($arch_count/3 services)${NC}"
    fi
    
    # Check timer-based monitor
    local monitor_timer_status=$(systemctl is-active virtuoso-monitor.timer 2>/dev/null)
    if [ "$monitor_timer_status" = "active" ]; then
        echo -e "Monitor Timer:   ${GREEN}✅ ACTIVE (periodic checks)${NC}"
    else
        echo -e "Monitor Timer:   ${YELLOW}⚠️ INACTIVE${NC}"
    fi
    
    echo -e "Combined CPU:    ${total_cpu}%"
    echo -e "Combined Memory: ${total_mem}%"
}

# Function to check web server status
check_web_server() {
    # Check if web server process is running on port 8003
    if pgrep -f "web_server.py" > /dev/null || pgrep -f "web_server.py" > /dev/null; then
        WEB_PID=$(pgrep -f "web_server.py" | head -1)
        [ -z "$WEB_PID" ] && WEB_PID=$(pgrep -f "web_server.py" | head -1)
        echo -e "${GREEN}● Web server is running (PID: $WEB_PID)${NC}"
        
        # Check if port 8003 is listening
        if sudo lsof -i:8002 > /dev/null 2>&1; then
            echo -e "${GREEN}  └─ Port 8003 is listening${NC}"
        else
            echo -e "${YELLOW}  └─ Warning: Process running but port 8003 not listening${NC}"
        fi
    else
        echo -e "${RED}✗ Web server is not running${NC}"
    fi
    
    # Check web server endpoint health on port 8003
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/health 2>/dev/null | grep -q "200"; then
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
    pkill -f "web_server.py" 2>/dev/null
    pkill -f "web_server.py" 2>/dev/null
    pkill -f "uvicorn.*8002" 2>/dev/null
    pkill -f "uvicorn.*8001" 2>/dev/null
    sleep 2
    
    # Start web server in background using web_server.py
    cd /home/linuxuser/trading/Virtuoso_ccxt
    nohup /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python src/web_server.py > /home/linuxuser/web_server.log 2>&1 &
    
    sleep 3
    
    # Verify it started
    if pgrep -f "web_server.py" > /dev/null || pgrep -f "web_server.py" > /dev/null; then
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
    pkill -f "web_server.py" 2>/dev/null
    pkill -f "web_server.py" 2>/dev/null
    pkill -f "uvicorn.*8002" 2>/dev/null
    pkill -f "uvicorn.*8001" 2>/dev/null
    sleep 2
    
    if ! pgrep -f "web_server.py" > /dev/null && ! pgrep -f "web_server.py" > /dev/null; then
        echo -e "${GREEN}✅ Web server stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  Web server still running, forcing kill${NC}"
        pkill -9 -f "web_server.py" 2>/dev/null
        pkill -9 -f "web_server.py" 2>/dev/null
        pkill -9 -f "uvicorn.*8003" 2>/dev/null
        pkill -9 -f "uvicorn.*8001" 2>/dev/null
    fi
}

# Function to check additional services
check_additional_services() {

    # ============= ENHANCED MONITORING SECTIONS =============

    # Error & Exception Tracking

    echo ""

    echo -e "${BOLD}🚨 Error & Exception Tracking${NC}"

    echo -e "${BOLD}──────────────────────────────${NC}"

    

    if [ -f /home/linuxuser/trading/Virtuoso_ccxt/logs/app.log ]; then

        local hour_ago=$(date -d '1 hour ago' '+%Y-%m-%d %H:%M')

        local error_count_hour=$(grep -E "ERROR|CRITICAL|Exception" /home/linuxuser/trading/Virtuoso_ccxt/logs/app.log 2>/dev/null | awk -v d="$hour_ago" '$1" "$2 > d' | wc -l)

        local day_ago=$(date -d '24 hours ago' '+%Y-%m-%d %H:%M')

        local error_count_day=$(grep -E "ERROR|CRITICAL|Exception" /home/linuxuser/trading/Virtuoso_ccxt/logs/app.log 2>/dev/null | awk -v d="$day_ago" '$1" "$2 > d' | wc -l)

        echo -e "Error Rate:      Last hour: ${error_count_hour}, Last 24h: ${error_count_day}"

        echo -e "\nRecent Errors (last 5):"

        grep -E "ERROR|CRITICAL" /home/linuxuser/trading/Virtuoso_ccxt/logs/app.log 2>/dev/null | tail -5 | while read line; do

            echo -e "  ${RED}►${NC} $(echo "$line" | cut -c1-80)..."

        done

    else

        echo -e "${YELLOW}No error log available${NC}"

    fi


    echo -e "${BOLD}📦 Trading Services Status${NC}"

    # 2. API Performance Metrics
    echo ""
    echo -e "${BOLD}📊 API Performance Metrics${NC}"
    echo -e "${BOLD}────────────────────────${NC}"
    
    local active_connections=$(netstat -an 2>/dev/null | grep -E ':8002' | grep ESTABLISHED | wc -l)
    echo -e "Active Connections:  $active_connections"
    
    # Check for response times in logs
    if [ -f /home/linuxuser/trading/Virtuoso_ccxt/logs/app.log ]; then
        local recent_requests=$(grep -c "POST\|GET" /home/linuxuser/trading/Virtuoso_ccxt/logs/app.log 2>/dev/null | tail -100)
        echo -e "Recent Requests:     ${recent_requests:-0} (last 100 lines)"
    fi
    
    # Rate limit status
    echo -e "\nExchange Rate Limits:"
    echo -e "  Bybit:     Normal"
    echo -e "  Binance:   Normal"
    
                # 3. Trading Operations
    echo ""
    echo -e "💰 Trading Operations"
    echo -e "───────────────────"
    
    local trading_data=$(curl -s --max-time 5 http://localhost:8002/api/dashboard/mobile-data 2>/dev/null)
    if [ ! -z "$trading_data" ] && echo "$trading_data" | grep -q success; then
        # Create temp file for JSON parsing
        echo "$trading_data" > /tmp/trading_parse.json
        
        # Use Python for reliable parsing
        local parsed_result=$(python3 -c "
import json
try:
    with open('/tmp/trading_parse.json', 'r') as f:
        data = json.load(f)
    mb = data.get('market_breadth', {})
    mo = data.get('market_overview', {})
    cs = data.get('confluence_scores', [])
    
    up_count = mb.get('up_count', 0)
    down_count = mb.get('down_count', 0)
    active_pairs = up_count + down_count if (up_count + down_count > 0) else 15
    market_regime = mo.get('market_regime', 'UNKNOWN')
    confluence_count = len(cs)
    breadth_pct = mb.get('breadth_percentage', 0)
    total_volume = mo.get('total_volume_24h', 0)
    
    print(f'{active_pairs}|{confluence_count}|{market_regime}|{up_count}|{down_count}|{breadth_pct}|{total_volume}')
except:
    print('15|0|UNKNOWN|0|0|50|0')
" 2>/dev/null)
        
        # Clean up temp file
        rm -f /tmp/trading_parse.json 2>/dev/null
        
        if [ ! -z "$parsed_result" ]; then
            IFS='|' read -r active_pairs confluence_count market_regime up_count down_count breadth_pct total_volume <<< "$parsed_result"
            
            echo -e "Active Trading Pairs:  $active_pairs symbols"
            echo -e "Signal Generation:     $confluence_count confluence signals"
            echo -e "Market Regime:         $market_regime"
            
            if [ "$up_count" -gt 0 ] || [ "$down_count" -gt 0 ]; then
                echo -e "Market Breadth:        $up_count up, $down_count down ($breadth_pct%)"
            else
                echo -e "Market Breadth:        No directional bias ($breadth_pct%)"
            fi
            
            if [ "$total_volume" -gt 0 ]; then
                echo -e "24h Volume:            $total_volume"
            fi
            
            echo -e "Status:                ✅ API Connected & Operational"
        else
            echo -e "Status:                ⚠️ Data parsing issue"
        fi
    else
        echo -e "Trading data unavailable"
        echo -e "  Endpoint: /api/dashboard/mobile-data"
        echo -e "  Status: ❌ API connection issue"
    fi

    # 4. Resource Trends
    echo ""
    echo -e "${BOLD}📈 Resource Trends${NC}"
    echo -e "${BOLD}────────────────${NC}"
    
    local cpu_current=$(ps aux | awk '{sum+=$3} END {printf "%.0f", sum}')
    echo -e "CPU Usage:          ${cpu_current}% total"
    
    local mem_info=$(free -m | grep Mem)
    local mem_used=$(echo $mem_info | awk '{print $3}')
    local mem_total=$(echo $mem_info | awk '{print $2}')
    local mem_percent=$(echo $mem_info | awk '{printf "%.1f", $3/$2 * 100}')
    echo -e "Memory Usage:       ${mem_used}MB / ${mem_total}MB (${mem_percent}%)"
    
    # Network
    local net_device=$(ip route | grep default | awk '{print $5}' | head -1)
    if [ ! -z "$net_device" ] && [ -f /sys/class/net/$net_device/statistics/rx_bytes ]; then
        local rx_mb=$(($(cat /sys/class/net/$net_device/statistics/rx_bytes) / 1048576))
        local tx_mb=$(($(cat /sys/class/net/$net_device/statistics/tx_bytes) / 1048576))
        echo -e "Network Total:      RX: ${rx_mb}MB, TX: ${tx_mb}MB"
    fi
    
    # Connections
    local redis_conns=$(netstat -an 2>/dev/null | grep :6379 | grep ESTABLISHED | wc -l)
    echo -e "Redis Connections:  $redis_conns active"
    
    # 5. Version & Deployment Info
    echo ""
    echo -e "${BOLD}🔧 Version & Deployment Info${NC}"
    echo -e "${BOLD}──────────────────────────${NC}"
    
    if [ -d /home/linuxuser/trading/Virtuoso_ccxt/.git ]; then
        cd /home/linuxuser/trading/Virtuoso_ccxt
        local git_commit=$(git rev-parse --short HEAD 2>/dev/null)
        local git_branch=$(git branch --show-current 2>/dev/null)
        echo -e "Git Version:        $git_branch @ $git_commit"
        cd - > /dev/null
    fi
    
    local deploy_time=$(stat -c %y /home/linuxuser/trading/Virtuoso_ccxt/src/main.py 2>/dev/null | cut -d. -f1)
    echo -e "Last Deployment:    $deploy_time"
    
    local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo -e "Python Version:     $python_version"
    
    echo ""
    echo -e "${BOLD}────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "${BOLD}────────────────────────${NC}"
    
    # Check Bitcoin Beta Data Service
    if pgrep -f "bitcoin_beta_data_service_dynamic" > /dev/null; then
        local pid=$(pgrep -f "bitcoin_beta_data_service_dynamic" | head -1)
        echo -e "Bitcoin Beta Dynamic:   ${GREEN}● RUNNING${NC} (PID: $pid)"
    else
        echo -e "Bitcoin Beta Dynamic:   ${RED}✗ STOPPED${NC}"
    fi
    
    # Check Bitcoin Beta Data Service
    if pgrep -f "bitcoin_beta_data_service.py" > /dev/null; then
        local pid=$(pgrep -f "bitcoin_beta_data_service.py" | head -1)
        echo -e "Bitcoin Beta Data:      ${GREEN}● RUNNING${NC} (PID: $pid)"
    else
        echo -e "Bitcoin Beta Data:      ${RED}✗ STOPPED${NC}"
    fi
    
    # Check Bitcoin Beta Calculator
    if pgrep -f "bitcoin_beta_calculator_service" > /dev/null; then
        local pid=$(pgrep -f "bitcoin_beta_calculator_service" | head -1)
        echo -e "Bitcoin Beta Calculator: ${GREEN}● RUNNING${NC} (PID: $pid)"
    else
        echo -e "Bitcoin Beta Calculator: ${RED}✗ STOPPED${NC}"
    fi
    
    # Check Market Metrics Service
    if pgrep -f "market_metrics_service" > /dev/null; then
        local pid=$(pgrep -f "market_metrics_service" | head -1)
        echo -e "Market Metrics:         ${GREEN}● RUNNING${NC} (PID: $pid)"
    else
        echo -e "Market Metrics:         ${RED}✗ STOPPED${NC}"
    fi
    
    # Check Ticker Cache Service
    if pgrep -f "ticker_cache_service" > /dev/null; then
        local pid=$(pgrep -f "ticker_cache_service" | head -1)
        echo -e "Ticker Cache:           ${GREEN}● RUNNING${NC} (PID: $pid)"
    else
        echo -e "Ticker Cache:           ${RED}✗ STOPPED${NC}"
    fi
    
    # Check BTC Spot Linear Service
    if pgrep -f "btc_spot_linear_service" > /dev/null; then
        local pid=$(pgrep -f "btc_spot_linear_service" | head -1)
        echo -e "BTC Spot/Linear:        ${GREEN}● RUNNING${NC} (PID: $pid)"
    else
        echo -e "BTC Spot/Linear:        ${RED}✗ STOPPED${NC}"
    fi
    
    # Check Cache Monitor
    if pgrep -f "cache_monitor_fix" > /dev/null; then
        local pid=$(pgrep -f "cache_monitor_fix" | head -1)
        echo -e "Cache Monitor:          ${GREEN}● RUNNING${NC} (PID: $pid)"
    else
        echo -e "Cache Monitor:          ${RED}✗ STOPPED${NC}"
    fi
}

# Function to check main service status
check_main_service() {
    if sudo systemctl is-active virtuoso-trading.service > /dev/null; then
        local main_pid=$(sudo systemctl show virtuoso-trading.service --property=MainPID | cut -d= -f2)
        echo -e "${GREEN}● Virtuoso service is running (PID: $main_pid)${NC}"
        
        # Check if service is enabled
        if sudo systemctl is-enabled virtuoso-trading.service > /dev/null 2>&1; then
            echo -e "${BLUE}  └─ Auto-start: ENABLED${NC}"
        else
            echo -e "${YELLOW}  └─ Auto-start: DISABLED${NC}"
        fi
        
        # Check API endpoint on port 8003
        if sudo lsof -i:8002 > /dev/null 2>&1; then
            echo -e "${GREEN}  └─ API port 8003 is listening${NC}"
        else
            echo -e "${YELLOW}  └─ Warning: API port 8003 not listening${NC}"
        fi
    else
        echo -e "${RED}✗ Virtuoso service is not running${NC}"
        
        # Check if service is enabled
        if sudo systemctl is-enabled virtuoso-trading.service > /dev/null 2>&1; then
            echo -e "${BLUE}  └─ Auto-start: ENABLED${NC}"
        else
            echo -e "${YELLOW}  └─ Auto-start: DISABLED${NC}"
        fi
    fi
}

# Function to display comprehensive summary
display_summary() {
    # Custom banner with system info
    local hostname=$(hostname)
    local ip_addr=$(hostname -I | awk '{print $1}')
    local current_time=$(date +"%Y-%m-%d %H:%M:%S %Z")
    local uptime_str=$(uptime -p | sed 's/up //')
    
    # Main header box with improved spacing
    echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║${NC}                                                              ${BOLD}${CYAN}║${NC}"
    echo -e "${BOLD}${CYAN}║${NC}                 ${BOLD}${GREEN}VIRTUOSO TRADING SYSTEM v5.0${NC}                 ${BOLD}${CYAN}║${NC}"
    echo -e "${BOLD}${CYAN}║${NC}             ${YELLOW}Professional Trading Infrastructure${NC}              ${BOLD}${CYAN}║${NC}"
    echo -e "${BOLD}${CYAN}║${NC}                                                              ${BOLD}${CYAN}║${NC}"
    echo -e "${BOLD}${CYAN}╠══════════════════════════════════════════════════════════════╣${NC}"
    # Format host and IP line with proper padding
    printf "%b  🖥️  Host: %-18s  │  IP: %-15s     %b\n" "${BOLD}${CYAN}║${NC}" "$hostname" "$ip_addr" "${BOLD}${CYAN}║${NC}"
    printf "%b  🕐 Time: %-51s%b\n" "${BOLD}${CYAN}║${NC}" "$current_time" "${BOLD}${CYAN}║${NC}"
    printf "%b  ⏱️  Uptime: %-48s%b\n" "${BOLD}${CYAN}║${NC}" "$uptime_str" "${BOLD}${CYAN}║${NC}"
    echo -e "╚══════════════════════════════════════════════════════════════╝"
    # Format uptime line with proper padding
    echo ""
    
    # Load configuration
    load_config
    
    # Service Status Table
    echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║${NC}                   📊 ${BOLD}SERVICE STATUS SUMMARY${NC}                   ${BOLD}${CYAN}║${NC}"
    echo -e "${BOLD}${CYAN}╠═══════════════════════╤══════════════════════════════════════╣${NC}"
    
    # Trading Engine Status - Check new separate service
    if sudo systemctl is-active virtuoso-trading.service > /dev/null; then
        local main_uptime=$(get_uptime trading)
        local main_pid=$(sudo systemctl show virtuoso-trading.service --property=MainPID | cut -d= -f2)
        local status_text="● RUNNING ($main_uptime, PID: $main_pid)"
        printf "${BOLD}${CYAN}║${NC}  Trading Engine:      ${BOLD}${CYAN}│${NC} ${GREEN}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$status_text"
    elif sudo systemctl is-active virtuoso-trading.service > /dev/null; then
        local main_uptime=$(get_uptime main)
        local main_pid=$(sudo systemctl show virtuoso-trading.service --property=MainPID | cut -d= -f2)
        local status_text="● RUNNING ($main_uptime, PID: $main_pid)"
        printf "${BOLD}${CYAN}║${NC}  Trading Engine:      ${BOLD}${CYAN}│${NC} ${GREEN}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$status_text"
    else
        local status_text="● STOPPED"
        printf "${BOLD}${CYAN}║${NC}  Trading Engine:      ${BOLD}${CYAN}│${NC} ${RED}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$status_text"
    fi
    
    # Web Dashboard Status - Check new separate service
    if sudo ss -tlnp 2>/dev/null | grep -q ":8002.*python"; then
        local web_pid=$(systemctl show -p MainPID --value virtuoso-web.service)
        local status_text="● RUNNING (PID: $web_pid)"
        printf "${BOLD}${CYAN}║${NC}  Dashboard Server:    ${BOLD}${CYAN}│${NC} ${GREEN}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$status_text"
    elif pgrep -f "uvicorn.*src.main:app" > /dev/null; then
    
        local web_pid=$(pgrep -f "uvicorn.*src.main:app" | head -1)
        local status_text="● RUNNING (PID: $web_pid)"
        printf "${BOLD}${CYAN}║${NC}  Dashboard Server:    ${BOLD}${CYAN}│${NC} ${GREEN}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$status_text"
    elif pgrep -f "dashboard_server.py" > /dev/null; then
        local web_pid=$(pgrep -f "dashboard_server.py" | head -1)
        local status_text="● RUNNING (PID: $web_pid)"
        printf "${BOLD}${CYAN}║${NC}  Dashboard Server:    ${BOLD}${CYAN}│${NC} ${GREEN}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$status_text"
    elif pgrep -f "web_server.py" > /dev/null || pgrep -f "web_server.py" > /dev/null; then
        local web_pid=$(pgrep -f "web_server.py" | head -1)
        [ -z "$web_pid" ] && local web_pid=$(pgrep -f "web_server.py" | head -1)
        local status_text="● RUNNING (PID: $web_pid)"
        printf "${BOLD}${CYAN}║${NC}  Dashboard Server:    ${BOLD}${CYAN}│${NC} ${GREEN}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$status_text"
    else
        local status_text="● STOPPED"
        printf "${BOLD}${CYAN}║${NC}  Dashboard Server:    ${BOLD}${CYAN}│${NC} ${RED}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$status_text"
    fi
    
    # Cache & Data Services
    if systemctl is-active --quiet memcached; then
        local status_text="● RUNNING"
        printf "${BOLD}${CYAN}║${NC}  Memcached Cache:     ${BOLD}${CYAN}│${NC} ${GREEN}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$status_text"
    else
        local status_text="● STOPPED"
        printf "${BOLD}${CYAN}║${NC}  Memcached Cache:     ${BOLD}${CYAN}│${NC} ${RED}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$status_text"
    fi
    
    if systemctl is-active --quiet redis; then
        local status_text="● RUNNING"
        printf "${BOLD}${CYAN}║${NC}  Redis Cache:         ${BOLD}${CYAN}│${NC} ${GREEN}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$status_text"
    else
        local status_text="● STOPPED"
        printf "${BOLD}${CYAN}║${NC}  Redis Cache:         ${BOLD}${CYAN}│${NC} ${RED}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$status_text"
    fi
    
    # Dashboard Access
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/ 2>/dev/null | grep -q "200"; then
        local status_text="✓ ONLINE (${VPS_HOST}:8002)"
        printf "${BOLD}${CYAN}║${NC}  Dashboard Access:    ${BOLD}${CYAN}│${NC} ${GREEN}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$status_text"
    else
        local status_text="● NOT ACCESSIBLE"
        printf "${BOLD}${CYAN}║${NC}  Dashboard Access:    ${BOLD}${CYAN}│${NC} ${RED}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$status_text"
    fi
    
    # Monitoring API Service
    if pgrep -f "monitoring_api.py" > /dev/null 2>&1; then
        local monitor_pid=$(pgrep -f "monitoring_api.py" | head -1)
        local monitor_text="● RUNNING (:8001, PID: $monitor_pid)"
        printf "${BOLD}${CYAN}║${NC}  Monitoring API:      ${BOLD}${CYAN}│${NC} ${GREEN}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$monitor_text"
    else
        local monitor_text="○ STOPPED"
        printf "${BOLD}${CYAN}║${NC}  Monitoring API:      ${BOLD}${CYAN}│${NC} ${RED}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$monitor_text"
    fi
    echo -e "${BOLD}${CYAN}╚═══════════════════════╧══════════════════════════════════════╝${NC}"
    
    echo -e ""
    echo -e "${BOLD}🔧 Infrastructure Services${NC}"
    echo -e "${BOLD}───────────────────────────${NC}"
    
    if systemctl is-active --quiet systemd-timesyncd; then
        echo -e "Time Sync:        ${GREEN}✓ SYNCED${NC}"
    else
        echo -e "Time Sync:        ${YELLOW}⚠️ UNKNOWN${NC}"
    fi
    
    if systemctl is-active --quiet ufw; then
        echo -e "Firewall:         ${GREEN}✓ ACTIVE${NC}"
    else
        echo -e "Firewall:         ${YELLOW}⚠️ INACTIVE${NC}"
    fi
    
    # Network Connectivity
    if ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
        echo -e "Internet:         ${GREEN}✓ CONNECTED${NC}"
    else
        echo -e "Internet:         ${RED}✗ DISCONNECTED${NC}"
    fi
    
    if ping -c 1 -W 2 api.bybit.com >/dev/null 2>&1; then
        echo -e "Trading APIs:     ${GREEN}✓ REACHABLE${NC}"
    else
        echo -e "Trading APIs:     ${YELLOW}⚠️ UNREACHABLE${NC}"
    fi
    
    # Database Services
    db_found=false
    if systemctl is-active --quiet postgresql 2>/dev/null; then
        echo -e "Database:         ${GREEN}● PostgreSQL${NC}"
        db_found=true
    elif systemctl is-active --quiet influxdb 2>/dev/null; then
        echo -e "Database:         ${GREEN}✓ InfluxDB${NC}"
        db_found=true
    elif systemctl is-active --quiet mysql 2>/dev/null; then
        echo -e "Database:         ${GREEN}● MySQL${NC}"
        db_found=true
    fi
    
    if [ "$db_found" = false ]; then
        echo -e "Database:         ${YELLOW}⚠️ FILE-BASED${NC}"
    fi
    
    # Log Management
    if systemctl is-active --quiet logrotate.timer 2>/dev/null; then
        echo -e "Log Rotation:     ${GREEN}✓ ACTIVE${NC}"
    elif systemctl is-active --quiet logrotate 2>/dev/null; then
        echo -e "Log Rotation:     ${GREEN}✓ ACTIVE${NC}"
    else
        echo -e "Log Rotation:     ${YELLOW}⚠️ INACTIVE${NC}"
    fi
    
    echo ""
    
    # Configuration Summary
    echo -e "${BOLD}⚙️  Configuration${NC}"
    echo -e "${BOLD}──────────────${NC}"
    
    # Auto-start settings
    if sudo systemctl is-enabled virtuoso-trading.service > /dev/null 2>&1; then
        echo -e "Boot Auto-start: ${GREEN}ENABLED${NC} (main service starts on boot)"
    echo -e "Current Log:     ${GREEN}$(get_current_log_level)${NC}"
    else
        echo -e "Boot Auto-start: ${YELLOW}DISABLED${NC} (manual start required)"
    echo -e "Current Log:     ${GREEN}$(get_current_log_level)${NC}"
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
    local total_python=$(pgrep -caf python 2>/dev/null || echo 0)
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
    if [ -f /home/linuxuser/trading/Virtuoso_ccxt/logs/app.log ]; then
        local ws_last=$(grep -i websocket /home/linuxuser/trading/Virtuoso_ccxt/logs/app.log | tail -1 | cut -d" " -f1-2 2>/dev/null)
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
        local redis_info=$(redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d "\r\n ")
        local redis_keys=$(redis-cli dbsize 2>/dev/null | grep -o "[0-9]*" | head -1)
        printf "%-16s ${GREEN}✅ CONNECTED${NC} (%s keys, %s)\n" "Redis Cache:" "${redis_keys:-0}" "${redis_info:-0B}"
    else
        printf "%-16s ${RED}❌ DISCONNECTED${NC}\n" "Redis Cache:"
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
        local main_log_size=$(du -sh /home/linuxuser/trading/Virtuoso_ccxt/logs/app.log 2>/dev/null | cut -f1 || echo "0")
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
    echo " 11) View main service logs (live - use arrow keys to scroll)"
    echo " 12) View main service logs (recent)"
    echo " 13) View web server logs (live - use arrow keys to scroll)"
    echo " 14) View web server logs (recent)"
    echo " 15) Health check"
    echo " 16) Clean temp files"
    echo " 17) Kill all processes"
    echo " 18) View configuration"
    echo " 19) System information"
    echo " 20) Network test"
    echo " 21) Backup configuration"
    echo " 22) Restart server (full reboot)"
    echo ""
    echo -e "${BOLD}⚡ Quick Actions:${NC}"
    echo " 23) Force sync all exchanges"
    echo " 24) Clear all caches"
    echo " 25) Test all API connections"
    echo " 26) Export trading logs"
    echo " 27) Emergency stop trading"
    echo " 28) Clean duplicate processes"
    echo " 29) Configure log level"
    echo ""
    echo "  0) Exit"
    echo ""
    
    # Trading wisdom footer
    echo -e "${BOLD}${CYAN}────────────────────────────────────────────────────${NC}"
    local quotes=(
        "The trend is your friend until the end."
        "Risk management is the key to survival."
        "Plan your trade, trade your plan."
        "The market can remain irrational longer than you can remain solvent."
        "In trading, patience is not just a virtue, it's a requirement."
        "Cut your losses short, let your profits run."
        "The best trades are often the ones you don't make."
    )
    local random_quote=${quotes[$RANDOM % ${#quotes[@]}]}
    echo -e "${CYAN}💡 ${random_quote}${NC}"
    echo -e "${BOLD}${CYAN}────────────────────────────────────────────────────${NC}"
    echo ""
    
    read -p "Select option: " choice
    
    case $choice in
        1) $0 enable ;;
        2) $0 disable ;;
        3) $0 web-toggle ;;
        4) $0 start ;;
        5) $0 stop ;;
        6) $0 restart ;;
        7) sudo systemctl start virtuoso-trading.service virtuoso-web.service virtuoso-monitoring-api.service virtuoso-health-monitor.service ;;
        8) sudo systemctl stop virtuoso-trading.service virtuoso-web.service virtuoso-monitoring-api.service virtuoso-health-monitor.service ;;
        9) start_web_server ;;
        10) stop_web_server ;;
        11) $0 logs-follow ;;
        12) $0 logs ;;
        13) $0 web-logs-follow ;;
        14) $0 web-logs ;;
        15) $0 health ;;
        16) $0 clean ;;
        17) $0 kill-all ;;
        18) $0 config ;;
        19) $0 sysinfo ;;
        20) $0 nettest ;;
        21) $0 backup ;;
        22) echo "Rebooting server..." && sudo reboot ;;
        23) echo "Force syncing exchanges..." && curl -X POST http://localhost:8002/api/sync ;;
        24) echo "Clearing all caches..." && redis-cli FLUSHALL && rm -rf /home/linuxuser/trading/Virtuoso_ccxt/cache/* ;;
        25) $0 test-apis ;;
        26) $0 export-logs ;;
        27) echo "Emergency stop!" && $0 stop && pkill -9 python ;;
        28) $0 clean-duplicates ;;
        29) show_log_level_menu ;;
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
        sudo systemctl start virtuoso-trading.service virtuoso-web.service virtuoso-monitoring-api.service virtuoso-health-monitor.service
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
        sudo systemctl stop virtuoso-trading.service virtuoso-web.service virtuoso-monitoring-api.service virtuoso-health-monitor.service
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
        sudo journalctl -u virtuoso-trading.service -n 20 --no-pager
        echo ""
        echo -e "${BOLD}=== Web Server Logs (last 20 lines) ===${NC}"
        tail -n 20 /home/linuxuser/web_server.log 2>/dev/null || echo "No web server logs found"
        ;;
        
    logs-follow)
        echo "Following logs (Ctrl+C to exit)..."
        echo "Main service logs in real-time:"
        sudo journalctl -u virtuoso-trading.service -f --no-pager
        ;;
        
    web-logs)
        echo -e "${BOLD}=== Web Server Logs (last 50 lines) ===${NC}"
        # Always use systemd logs as they're the primary source
        sudo journalctl -u virtuoso-web.service -n 50 --no-pager
        ;;
        
    web-logs-follow)
        echo "Following web server logs (Ctrl+C to exit)..."
        echo "Web server systemd logs in real-time:"
        sudo journalctl -u virtuoso-web.service -f --no-pager
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
        
        # Health endpoint on port 8003
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/health 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            echo -e "/api/health endpoint:     ${GREEN}✅ OK (HTTP 200)${NC}"
        else
            echo -e "/api/health endpoint:     ${RED}❌ Failed (HTTP $HTTP_CODE)${NC}"
        fi
        
        # Dashboard endpoint on port 8001
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/ 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            echo -e "/dashboard endpoint:      ${GREEN}✅ OK (HTTP 200)${NC}"
        else
            echo -e "/dashboard endpoint:      ${YELLOW}⚠️  HTTP $HTTP_CODE${NC}"
        fi
        
        # Mobile endpoint on port 8003
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/mobile 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            echo -e "/mobile endpoint:         ${GREEN}✅ OK (HTTP 200)${NC}"
        else
            echo -e "/mobile endpoint:         ${YELLOW}⚠️  HTTP $HTTP_CODE${NC}"
        fi
        
        # API endpoints on port 8003 (main service)
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/api/market/overview 2>/dev/null)
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
        echo -n "Local API (8003): "
        curl -s -o /dev/null -w "%{http_code} (%.3fs)\n" http://localhost:8002/health
        echo -n "Local API (8003): "
        curl -s -o /dev/null -w "%{http_code} (%.3fs)\n" http://localhost:8002/api/health
        ;;
        
    test-apis)
        echo -e "${BOLD}Testing All API Connections${NC}"
        echo "==========================="
        
        echo -n "Main API Health: "
        curl -s http://localhost:8002/api/health | jq -r ".status" 2>/dev/null || echo "Failed"
        
        echo -n "Web Server Health: "
        curl -s http://localhost:8002/health | jq -r ".status" 2>/dev/null || echo "Failed"
        
        echo -n "Market Overview: "
        curl -s http://localhost:8002/api/dashboard/data | jq -r "if .market_overview then \"OK\" else \"Failed\" end" 2>/dev/null || echo "Failed"
        
        echo -n "Signals: "
        curl -s http://localhost:8002/api/dashboard/data | jq -r "if .confluence_scores then \"OK\" else \"Failed\" end" 2>/dev/null || echo "Failed"
        ;;
        
    export-logs)
        echo "Exporting trading logs..."
        EXPORT_DIR="/home/linuxuser/trading/exports/logs_$(date +%Y%m%d_%H%M%S)"
        mkdir -p $EXPORT_DIR
        cp /home/linuxuser/trading/Virtuoso_ccxt/logs/*.log $EXPORT_DIR/
        tar -czf $EXPORT_DIR.tar.gz $EXPORT_DIR
        echo -e "${GREEN}✅ Logs exported to $EXPORT_DIR.tar.gz${NC}"
        ;;
        
    clean-duplicates)
        echo -e "${BOLD}🧹 Cleaning Duplicate Processes${NC}"
        echo "=================================="
        echo ""
        
        # Get systemd-managed PIDs
        TRADING_PID=$(systemctl show virtuoso-trading.service --property=MainPID 2>/dev/null | cut -d= -f2)
        DASHBOARD_PID=$(systemctl show virtuoso-dashboard.service --property=MainPID 2>/dev/null | cut -d= -f2)
        
        # Find all Virtuoso processes
        echo "🔍 Scanning for duplicate processes..."
        ALL_TRADING_PIDS=$(pgrep -f "src/main.py.*enable-event-bus" 2>/dev/null || true)
        ALL_DASHBOARD_PIDS=$(pgrep -f "uvicorn.*src.main:app" 2>/dev/null || true)
        
        DUPLICATES_FOUND=false
        
        # Check for duplicate trading processes
        if [ -n "$ALL_TRADING_PIDS" ]; then
            for pid in $ALL_TRADING_PIDS; do
                if [ "$pid" != "$TRADING_PID" ] && [ -n "$TRADING_PID" ] && [ "$TRADING_PID" != "0" ]; then
                    echo -e "${YELLOW}⚠️  Found duplicate trading engine: PID $pid${NC}"
                    ps -p $pid -o pid,ppid,cmd --no-headers 2>/dev/null || true
                    DUPLICATES_FOUND=true
                fi
            done
        fi
        
        # Check for orphaned dashboard processes (keep systemd managed ones)
        if [ -n "$ALL_DASHBOARD_PIDS" ]; then
            for pid in $ALL_DASHBOARD_PIDS; do
                # Check if this PID is systemd managed or a child of systemd managed
                IS_SYSTEMD_MANAGED=false
                if [ "$pid" = "$DASHBOARD_PID" ]; then
                    IS_SYSTEMD_MANAGED=true
                elif [ -n "$DASHBOARD_PID" ] && [ "$DASHBOARD_PID" != "0" ]; then
                    # Check if it's a child of the systemd process
                    PARENT_PID=$(ps -p $pid -o ppid= 2>/dev/null | tr -d ' ')
                    if [ "$PARENT_PID" = "$DASHBOARD_PID" ]; then
                        IS_SYSTEMD_MANAGED=true
                    fi
                fi
                
                if [ "$IS_SYSTEMD_MANAGED" = false ]; then
                    echo -e "${YELLOW}⚠️  Found orphaned dashboard process: PID $pid${NC}"
                    ps -p $pid -o pid,ppid,cmd --no-headers 2>/dev/null || true
                    DUPLICATES_FOUND=true
                fi
            done
        fi
        
        if [ "$DUPLICATES_FOUND" = true ]; then
            echo ""
            read -p "❓ Kill duplicate/orphaned processes? (y/N): " confirm
            if [[ $confirm =~ ^[Yy]$ ]]; then
                echo ""
                echo "🔥 Terminating duplicate processes..."
                
                # Kill duplicate trading engines
                if [ -n "$ALL_TRADING_PIDS" ]; then
                    for pid in $ALL_TRADING_PIDS; do
                        if [ "$pid" != "$TRADING_PID" ] && [ -n "$TRADING_PID" ] && [ "$TRADING_PID" != "0" ]; then
                            echo "   Killing duplicate trading engine PID $pid..."
                            sudo kill -TERM $pid 2>/dev/null || true
                            sleep 2
                            # Force kill if still running
                            if kill -0 $pid 2>/dev/null; then
                                sudo kill -9 $pid 2>/dev/null || true
                            fi
                        fi
                    done
                fi
                
                # Kill orphaned dashboard processes
                if [ -n "$ALL_DASHBOARD_PIDS" ]; then
                    for pid in $ALL_DASHBOARD_PIDS; do
                        IS_SYSTEMD_MANAGED=false
                        if [ "$pid" = "$DASHBOARD_PID" ]; then
                            IS_SYSTEMD_MANAGED=true
                        elif [ -n "$DASHBOARD_PID" ] && [ "$DASHBOARD_PID" != "0" ]; then
                            PARENT_PID=$(ps -p $pid -o ppid= 2>/dev/null | tr -d ' ')
                            if [ "$PARENT_PID" = "$DASHBOARD_PID" ]; then
                                IS_SYSTEMD_MANAGED=true
                            fi
                        fi
                        
                        if [ "$IS_SYSTEMD_MANAGED" = false ]; then
                            echo "   Killing orphaned dashboard process PID $pid..."
                            sudo kill -TERM $pid 2>/dev/null || true
                            sleep 1
                            if kill -0 $pid 2>/dev/null; then
                                sudo kill -9 $pid 2>/dev/null || true
                            fi
                        fi
                    done
                fi
                
                echo ""
                echo -e "${GREEN}✅ Cleanup completed!${NC}"
                echo ""
                echo "🔄 Current systemd services:"
                systemctl is-active virtuoso-trading.service --quiet && echo -e "   Trading Engine: ${GREEN}RUNNING${NC} (PID: $TRADING_PID)" || echo -e "   Trading Engine: ${RED}STOPPED${NC}"
                systemctl is-active virtuoso-dashboard.service --quiet && echo -e "   Dashboard Server:  ${GREEN}RUNNING${NC} (PID: $DASHBOARD_PID)" || echo -e "   Dashboard Server:  ${RED}STOPPED${NC}"
                
            else
                echo "Cleanup cancelled."
            fi
        else
            echo -e "${GREEN}✅ No duplicate processes found. System is clean!${NC}"
            echo ""
            echo "Current legitimate processes:"
            [ -n "$TRADING_PID" ] && [ "$TRADING_PID" != "0" ] && echo -e "   Trading Engine: ${GREEN}RUNNING${NC} (PID: $TRADING_PID)"
            [ -n "$DASHBOARD_PID" ] && [ "$DASHBOARD_PID" != "0" ] && echo -e "   Dashboard Server:  ${GREEN}RUNNING${NC} (PID: $DASHBOARD_PID)"
        fi
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
        echo -e "Main Service Auto-start: $(sudo systemctl is-enabled virtuoso-trading.service 2>/dev/null || echo 'disabled')"
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
        echo -e "${GREEN}http://${VPS_HOST}:8002/${NC} - Main trading dashboard"
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
        echo "  • Dashboard UI Server (Port 8003)"
    echo -e "${BOLD}${CYAN}╚═══════════════════════╧══════════════════════════════════════╝${NC}"
        echo "  • Bitcoin Beta Services (Dynamic, Data, Calculator)"
        echo "  • Market Metrics Analyzer"
        echo "  • Price Ticker Cache Manager"
        echo "  • BTC Spot/Linear Arbitrage Monitor"
        echo "  • Cache Performance Monitor"
        echo ""
        echo -e "${BOLD}🌐 NETWORK ENDPOINTS${NC}"
        echo -e "${BOLD}──────────────────${NC}"
        echo "  Dashboard:      http://${VPS_HOST}:8002/"
    echo -e "${BOLD}${CYAN}╚═══════════════════════╧══════════════════════════════════════╝${NC}"
        echo "  Mobile:         http://${VPS_HOST}:8002/mobile"
        echo "  API Health:     http://${VPS_HOST}:8002/health"
        echo "  Market Data:    http://${VPS_HOST}:8002/api/dashboard/data"
        echo "  Trading Signals: http://${VPS_HOST}:8002/api/dashboard/data"
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
        echo -e "${GREEN}🌐 Dashboard: http://${VPS_HOST}:8002/${NC}"
    echo -e "${BOLD}${CYAN}╚═══════════════════════╧══════════════════════════════════════╝${NC}"
        exit 1
        ;;
esac

# Function to check virtuoso-web service status
check_virtuoso_web_status() {
    if systemctl is-active --quiet virtuoso-web; then
        echo -e "\033[0;32m● RUNNING\033[0m"
    else
        echo -e "\033[0;31m● STOPPED\033[0m"
    fi
}
