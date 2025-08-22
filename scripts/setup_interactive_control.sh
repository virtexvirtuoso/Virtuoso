#!/bin/bash

# Setup Interactive Control Menu with Summary Panel
# Combines visual dashboard with numbered menu options

VPS_HOST="linuxuser@45.77.40.77"

echo "Installing interactive control menu..."

# Create the interactive control script on VPS
ssh $VPS_HOST 'cat > /home/linuxuser/virtuoso_control_interactive.sh << '\''EOF'\''
#!/bin/bash

# Virtuoso Interactive Control System
# Version 5.0 - Interactive menu with summary panel

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

# Function to display the status panel
display_panel() {
    clear
    echo -e "${BOLD}${CYAN}=====================================${NC}"
    echo -e "${BOLD}${CYAN}  Virtuoso Trading Service Control${NC}"
    echo -e "${BOLD}${CYAN}=====================================${NC}"
    echo ""
    
    # Load configuration
    load_config
    
    # Main Service Status
    if sudo systemctl is-active virtuoso > /dev/null 2>&1; then
        local main_uptime=$(get_uptime main)
        echo -e "${GREEN}● Main service is running${NC} (uptime: $main_uptime)"
        sudo systemctl status virtuoso --no-pager | head -n 10
        
        if sudo systemctl is-enabled virtuoso > /dev/null 2>&1; then
            echo -e "${GREEN}● Auto-start is enabled${NC}"
        else
            echo -e "${YELLOW}● Auto-start is disabled${NC}"
        fi
    else
        echo -e "${RED}● Main service is stopped${NC}"
        if sudo systemctl is-enabled virtuoso > /dev/null 2>&1; then
            echo -e "${YELLOW}● Auto-start is enabled (will start on boot)${NC}"
        else
            echo -e "${YELLOW}● Auto-start is disabled${NC}"
        fi
    fi
    
    echo ""
    
    # Web Server Status
    if pgrep -f "python.*web_server.py" > /dev/null; then
        local web_uptime=$(get_uptime web)
        local web_pid=$(pgrep -f "python.*web_server.py")
        echo -e "${GREEN}● Web server is running${NC} (PID: $web_pid, uptime: $web_uptime)"
        
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health 2>/dev/null | grep -q "200"; then
            echo -e "  └─ ${GREEN}Dashboard accessible at port 8003${NC}"
        else
            echo -e "  └─ ${YELLOW}Dashboard not responding${NC}"
        fi
    else
        echo -e "${RED}● Web server is stopped${NC}"
    fi
    
    if [ "$WEB_SERVER_AUTO_START" = "enabled" ]; then
        echo -e "  └─ ${GREEN}Web auto-start enabled${NC}"
    else
        echo -e "  └─ ${YELLOW}Web auto-start disabled${NC}"
    fi
    
    echo ""
    
    # System Resources
    echo -e "${BOLD}System Resources:${NC}"
    echo -e "  Memory: $(free -h | grep Mem | awk "{print \$3\" / \"\$2}")"
    echo -e "  CPU Load: $(uptime | awk -F"load average:" "{print \$2}")"
    echo -e "  Disk: $(df -h / | tail -1 | awk "{print \$3\" / \"\$2\" (\"\$5\" used)\"}")"
    
    echo ""
}

# Function to start web server
start_web_server() {
    echo "Starting web server..."
    pkill -f "python.*web_server.py" 2>/dev/null
    sleep 2
    
    cd /home/linuxuser/trading/Virtuoso_ccxt
    nohup /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python src/web_server.py > /home/linuxuser/web_server.log 2>&1 &
    
    sleep 3
    
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

# Interactive menu
show_menu() {
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
    echo "  0) Exit"
    echo ""
    echo -n "Enter selection [0-20]: "
}

# Main interactive loop
while true; do
    display_panel
    show_menu
    read -r selection
    
    case $selection in
        1)
            echo "Enabling main service auto-start..."
            sudo systemctl enable virtuoso
            echo -e "${GREEN}✅ Main service will start on boot${NC}"
            sleep 2
            ;;
        2)
            echo "Disabling main service auto-start..."
            sudo systemctl disable virtuoso
            echo -e "${YELLOW}⚠️  Main service will NOT start on boot${NC}"
            sleep 2
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
            sleep 2
            ;;
        4)
            echo "Starting all services..."
            sudo systemctl start virtuoso
            sleep 3
            load_config
            if [ "$WEB_SERVER_AUTO_START" = "enabled" ]; then
                start_web_server
            fi
            sleep 2
            ;;
        5)
            echo "Stopping all services..."
            stop_web_server
            sudo systemctl stop virtuoso
            echo -e "${GREEN}✅ All services stopped${NC}"
            sleep 2
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
            sleep 2
            ;;
        7)
            echo "Starting main service..."
            sudo systemctl start virtuoso
            echo -e "${GREEN}✅ Main service started${NC}"
            sleep 2
            ;;
        8)
            echo "Stopping main service..."
            sudo systemctl stop virtuoso
            echo -e "${GREEN}✅ Main service stopped${NC}"
            sleep 2
            ;;
        9)
            start_web_server
            sleep 2
            ;;
        10)
            stop_web_server
            sleep 2
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
            echo ""
            echo "Press Enter to continue..."
            read
            ;;
        13)
            echo -e "${BOLD}Performing health check...${NC}"
            echo ""
            
            # Test endpoints
            echo "Testing API endpoints:"
            
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health 2>/dev/null)
            if [ "$HTTP_CODE" = "200" ]; then
                echo -e "  /health:    ${GREEN}✅ OK${NC}"
            else
                echo -e "  /health:    ${RED}❌ Failed (HTTP $HTTP_CODE)${NC}"
            fi
            
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/dashboard 2>/dev/null)
            if [ "$HTTP_CODE" = "200" ]; then
                echo -e "  /dashboard: ${GREEN}✅ OK${NC}"
            else
                echo -e "  /dashboard: ${YELLOW}⚠️  HTTP $HTTP_CODE${NC}"
            fi
            
            echo ""
            echo "Press Enter to continue..."
            read
            ;;
        14)
            echo "Cleaning temporary files..."
            rm -f /tmp/virtuoso.lock
            sudo journalctl --vacuum-time=7d
            > /home/linuxuser/web_server.log
            echo -e "${GREEN}✅ Cleanup complete${NC}"
            sleep 2
            ;;
        15)
            echo -e "${YELLOW}⚠️  Killing all Virtuoso processes...${NC}"
            pkill -f virtuoso
            pkill -f "python.*main.py"
            pkill -f "python.*web_server.py"
            echo -e "${GREEN}✅ All processes killed${NC}"
            sleep 2
            ;;
        16)
            echo -e "${BOLD}Current Configuration:${NC}"
            echo "========================"
            load_config
            echo "Main Service Auto-start: $(sudo systemctl is-enabled virtuoso 2>/dev/null || echo '\''disabled'\'')"
            echo "Web Server Auto-start:   $WEB_SERVER_AUTO_START"
            echo ""
            echo "Config file: $CONFIG_FILE"
            echo "Service file: /etc/systemd/system/virtuoso.service"
            echo ""
            echo "Press Enter to continue..."
            read
            ;;
        17)
            echo -e "${BOLD}System Information:${NC}"
            echo "==================="
            echo "Hostname: $(hostname)"
            echo "OS: $(lsb_release -ds 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2)"
            echo "Kernel: $(uname -r)"
            echo "Uptime: $(uptime -p | sed '\''s/up //'\'')"
            echo "CPU Cores: $(nproc)"
            echo "Total Memory: $(free -h | grep Mem | awk '\''{print $2}'\'')"
            echo "IP Address: $(ip -4 addr show | grep -oP '\''(?<=inet\s)\d+(\.\d+){3}'\'' | grep -v 127.0.0.1 | head -1)"
            echo ""
            echo "Press Enter to continue..."
            read
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
            if curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health 2>/dev/null | grep -q "200"; then
                echo -e "Dashboard:    ${GREEN}✅ Accessible${NC}"
            else
                echo -e "Dashboard:    ${RED}❌ Not accessible${NC}"
            fi
            
            echo ""
            echo "Press Enter to continue..."
            read
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
            sleep 3
            ;;
        20)
            echo -e "${RED}⚠️  SYSTEM REBOOT REQUESTED${NC}"
            echo "This will restart the entire server."
            echo -n "Are you sure? Type '\''yes'\'' to confirm: "
            read confirm
            if [ "$confirm" = "yes" ]; then
                echo "Rebooting in 5 seconds..."
                sleep 5
                sudo reboot
            else
                echo "Reboot cancelled"
                sleep 2
            fi
            ;;
        0)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid selection${NC}"
            sleep 1
            ;;
    esac
done
EOF'

# Make script executable
ssh $VPS_HOST 'chmod +x /home/linuxuser/virtuoso_control_interactive.sh'

# Create alias for interactive mode
ssh $VPS_HOST 'echo "alias vti=\"/home/linuxuser/virtuoso_control_interactive.sh\"" >> ~/.bashrc'

echo ""
echo "✅ Interactive Control Menu installed!"
echo ""
echo "Access methods:"
echo "  vti                    - Interactive menu (recommended)"
echo "  vt [command]           - Direct command execution"
echo ""
echo "The interactive menu provides:"
echo "  • Visual status panel"
echo "  • 20 numbered options"
echo "  • Real-time status updates"
echo "  • Easy navigation"
echo ""
echo "To use: ssh $VPS_HOST 'vti'"