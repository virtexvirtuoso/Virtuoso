#!/bin/bash

# Enhanced VPS service control with improved status summary
# Provides comprehensive overview and management

VPS_HOST="linuxuser@45.77.40.77"

echo "Updating service control with enhanced status summary..."

# Create comprehensive service control script on VPS
ssh $VPS_HOST 'cat > /home/linuxuser/virtuoso_control.sh << "EOF"
#!/bin/bash

# Virtuoso Trading Service Control with Enhanced Status Summary
# Version 3.0 - Comprehensive overview and management

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
        if pgrep -f "python.*web_server.py" > /dev/null; then
            local pid=$(pgrep -f "python.*web_server.py" | head -1)
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

# Function to check web server status
check_web_server() {
    # Check if web server process is running
    if pgrep -f "python.*web_server.py" > /dev/null; then
        WEB_PID=$(pgrep -f "python.*web_server.py")
        echo -e "${GREEN}● Web server is running (PID: $WEB_PID)${NC}"
        
        # Check if port 8003 is listening
        if sudo lsof -i:8003 > /dev/null 2>&1; then
            echo -e "${GREEN}  └─ Port 8003 is listening${NC}"
        else
            echo -e "${YELLOW}  └─ Warning: Process running but port 8003 not listening${NC}"
        fi
    else
        echo -e "${RED}● Web server is not running${NC}"
    fi
    
    # Check web server endpoint health
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health 2>/dev/null | grep -q "200"; then
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
    pkill -f "python.*web_server.py" 2>/dev/null
    sleep 2
    
    # Start web server in background
    cd /home/linuxuser/trading/Virtuoso_ccxt
    nohup /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python src/web_server.py > /home/linuxuser/web_server.log 2>&1 &
    
    sleep 3
    
    # Verify it started
    if pgrep -f "python.*web_server.py" > /dev/null; then
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
    pkill -f "python.*web_server.py" 2>/dev/null
    sleep 2
    
    if ! pgrep -f "python.*web_server.py" > /dev/null; then
        echo -e "${GREEN}✅ Web server stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  Web server still running, forcing kill${NC}"
        pkill -9 -f "python.*web_server.py" 2>/dev/null
    fi
}

# Function to check main service status
check_main_service() {
    if sudo systemctl is-active virtuoso > /dev/null; then
        echo -e "${GREEN}● Virtuoso service is running${NC}"
        
        # Check if service is enabled
        if sudo systemctl is-enabled virtuoso > /dev/null 2>&1; then
            echo -e "${BLUE}  └─ Auto-start: ENABLED${NC}"
        else
            echo -e "${YELLOW}  └─ Auto-start: DISABLED${NC}"
        fi
        
        sudo systemctl status virtuoso --no-pager | head -n 8
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
        echo -e "Main Service:    ${GREEN}● RUNNING${NC} (uptime: $main_uptime)"
    else
        echo -e "Main Service:    ${RED}● STOPPED${NC}"
    fi
    
    # Web Server Status
    if pgrep -f "python.*web_server.py" > /dev/null; then
        local web_uptime=$(get_uptime web)
        local web_pid=$(pgrep -f "python.*web_server.py")
        echo -e "Web Server:      ${GREEN}● RUNNING${NC} (uptime: $web_uptime, PID: $web_pid)"
    else
        echo -e "Web Server:      ${RED}● STOPPED${NC}"
    fi
    
    # Dashboard Access
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health 2>/dev/null | grep -q "200"; then
        echo -e "Dashboard:       ${GREEN}● ACCESSIBLE${NC} (port 8003)"
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
}

# Main control logic
case "$1" in
    status)
        display_summary
        echo ""
        echo -e "${BOLD}📋 Detailed Service Status${NC}"
        echo -e "${BOLD}────────────────────────${NC}"
        echo ""
        check_main_service
        echo ""
        check_web_server
        echo ""
        
        # Show recent logs
        echo -e "${BOLD}📜 Recent Activity (last 5 entries)${NC}"
        echo -e "${BOLD}──────────────────────────────────${NC}"
        echo "Main service:"
        sudo journalctl -u virtuoso -n 5 --no-pager --no-hostname -o short
        echo ""
        echo "Web server:"
        tail -n 5 /home/linuxuser/web_server.log 2>/dev/null || echo "No web server logs found"
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
        
        # API Endpoint Checks
        echo -e "${BOLD}🌐 API Endpoint Tests${NC}"
        echo -e "${BOLD}──────────────────${NC}"
        
        # Health endpoint
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            echo -e "/health endpoint:    ${GREEN}✅ OK (HTTP 200)${NC}"
        else
            echo -e "/health endpoint:    ${RED}❌ Failed (HTTP $HTTP_CODE)${NC}"
        fi
        
        # Dashboard endpoint
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/dashboard 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            echo -e "/dashboard endpoint: ${GREEN}✅ OK (HTTP 200)${NC}"
        else
            echo -e "/dashboard endpoint: ${YELLOW}⚠️  HTTP $HTTP_CODE${NC}"
        fi
        
        # Mobile endpoint
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/mobile 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            echo -e "/mobile endpoint:    ${GREEN}✅ OK (HTTP 200)${NC}"
        else
            echo -e "/mobile endpoint:    ${YELLOW}⚠️  HTTP $HTTP_CODE${NC}"
        fi
        
        echo ""
        echo -e "${BOLD}✅ Health check complete${NC}"
        ;;
        
    summary)
        display_summary
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
        
    *)
        echo -e "${BOLD}Virtuoso Trading Service Control${NC}"
        echo "================================="
        echo ""
        echo -e "${BOLD}Usage:${NC} $0 {command}"
        echo ""
        echo -e "${BOLD}Main Commands:${NC}"
        echo "  status      - Show comprehensive status with summary"
        echo "  summary     - Show only the summary panel"
        echo "  start       - Start main service (and web if enabled)"
        echo "  stop        - Stop all services"
        echo "  restart     - Restart all services"
        echo ""
        echo -e "${BOLD}Web Server Commands:${NC}"
        echo "  web-start   - Start only web server"
        echo "  web-stop    - Stop only web server"
        echo "  web-restart - Restart only web server"
        echo "  web-toggle  - Toggle web server auto-start"
        echo ""
        echo -e "${BOLD}Configuration:${NC}"
        echo "  enable      - Enable main service auto-start on boot"
        echo "  disable     - Disable main service auto-start on boot"
        echo "  config      - Show current configuration"
        echo ""
        echo -e "${BOLD}Monitoring & Maintenance:${NC}"
        echo "  health      - Perform comprehensive health check"
        echo "  logs        - Show recent logs"
        echo "  logs-follow - Follow logs in real-time"
        echo "  clean       - Clean temporary files and old logs"
        echo ""
        echo -e "${BOLD}Quick Check:${NC} vt summary"
        exit 1
        ;;
esac
EOF'

# Make script executable
ssh $VPS_HOST 'chmod +x /home/linuxuser/virtuoso_control.sh'

# Update alias
ssh $VPS_HOST 'grep -q "alias vt=" ~/.bashrc || echo "alias vt=\"/home/linuxuser/virtuoso_control.sh\"" >> ~/.bashrc'

echo ""
echo "✅ Enhanced service control with comprehensive summary installed!"
echo ""
echo "New Features:"
echo "  • Comprehensive status summary panel"
echo "  • Service uptime tracking"
echo "  • Maintenance schedule display"
echo "  • System resource monitoring"
echo "  • Enhanced health checks"
echo "  • Improved visual formatting"
echo ""
echo "Key Commands:"
echo "  vt status   - Full status with summary"
echo "  vt summary  - Quick summary only"
echo "  vt health   - Comprehensive health check"
echo ""
echo "To see the new summary:"
echo "ssh $VPS_HOST 'virtuoso_control.sh status'"