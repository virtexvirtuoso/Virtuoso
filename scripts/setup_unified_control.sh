#!/bin/bash

# Unified System and Service Control for Virtuoso Trading Platform
# Combines service management with system administration

VPS_HOST="linuxuser@45.77.40.77"

echo "Installing unified control system..."

# Create the unified control script on VPS
ssh $VPS_HOST 'cat > /home/linuxuser/virtuoso_control.sh << "EOF"
#!/bin/bash

# Virtuoso Unified Control System
# Version 4.0 - Complete system and service management

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
    elif [ "$service" = "system" ]; then
        uptime -p | sed "s/up //"
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
    if pgrep -f "python.*web_server.py" > /dev/null; then
        WEB_PID=$(pgrep -f "python.*web_server.py")
        echo -e "${GREEN}● Web server is running (PID: $WEB_PID)${NC}"
        
        if sudo lsof -i:8003 > /dev/null 2>&1; then
            echo -e "${GREEN}  └─ Port 8003 is listening${NC}"
        else
            echo -e "${YELLOW}  └─ Warning: Process running but port 8003 not listening${NC}"
        fi
    else
        echo -e "${RED}● Web server is not running${NC}"
    fi
    
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health 2>/dev/null | grep -q "200"; then
        echo -e "${GREEN}  └─ Health endpoint responding${NC}"
    else
        echo -e "${YELLOW}  └─ Health endpoint not responding${NC}"
    fi
    
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

# Function to check main service status
check_main_service() {
    if sudo systemctl is-active virtuoso > /dev/null; then
        echo -e "${GREEN}● Virtuoso service is running${NC}"
        
        if sudo systemctl is-enabled virtuoso > /dev/null 2>&1; then
            echo -e "${BLUE}  └─ Auto-start: ENABLED${NC}"
        else
            echo -e "${YELLOW}  └─ Auto-start: DISABLED${NC}"
        fi
        
        sudo systemctl status virtuoso --no-pager | head -n 8
    else
        echo -e "${RED}● Virtuoso service is not running${NC}"
        
        if sudo systemctl is-enabled virtuoso > /dev/null 2>&1; then
            echo -e "${BLUE}  └─ Auto-start: ENABLED${NC}"
        else
            echo -e "${YELLOW}  └─ Auto-start: DISABLED${NC}"
        fi
    fi
}

# Function to display comprehensive control panel
display_control_panel() {
    echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║      VIRTUOSO TRADING PLATFORM CONTROL CENTER     ║${NC}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Load configuration
    load_config
    
    # Services Section
    echo -e "${BOLD}┌─ 📊 SERVICES ─────────────────────────────────────┐${NC}"
    
    # Main Service Status
    if sudo systemctl is-active virtuoso > /dev/null; then
        local main_uptime=$(get_uptime main)
        echo -e "│ Main Service:    ${GREEN}● RUNNING${NC} (uptime: $main_uptime)"
    else
        echo -e "│ Main Service:    ${RED}● STOPPED${NC}"
    fi
    
    # Web Server Status
    if pgrep -f "python.*web_server.py" > /dev/null; then
        local web_uptime=$(get_uptime web)
        local web_pid=$(pgrep -f "python.*web_server.py")
        echo -e "│ Web Server:      ${GREEN}● RUNNING${NC} (uptime: $web_uptime)"
    else
        echo -e "│ Web Server:      ${RED}● STOPPED${NC}"
    fi
    
    # Dashboard Access
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health 2>/dev/null | grep -q "200"; then
        echo -e "│ Dashboard:       ${GREEN}● ONLINE${NC} at port 8003"
    else
        echo -e "│ Dashboard:       ${RED}● OFFLINE${NC}"
    fi
    echo -e "${BOLD}└───────────────────────────────────────────────────┘${NC}"
    echo ""
    
    # System Section
    echo -e "${BOLD}┌─ 💻 SYSTEM ───────────────────────────────────────┐${NC}"
    echo -e "│ Hostname:        $(hostname)"
    echo -e "│ System Uptime:   $(get_uptime system)"
    echo -e "│ Load Average:    $(uptime | awk -F"load average:" "{print \$2}")"
    echo -e "│ Memory:          $(free -h | grep Mem | awk "{print \$3\" / \"\$2\" (\"int(\$3/\$2*100)\"% used)\"}")"
    echo -e "│ Disk:            $(df -h / | tail -1 | awk "{print \$3\" / \"\$2\" (\"\$5\" used)\"}")"
    echo -e "│ CPU Cores:       $(nproc)"
    echo -e "│ Python Procs:    $(pgrep -c python 2>/dev/null || echo 0) active"
    echo -e "${BOLD}└───────────────────────────────────────────────────┘${NC}"
    echo ""
    
    # Configuration Section
    echo -e "${BOLD}┌─ ⚙️  CONFIGURATION ────────────────────────────────┐${NC}"
    
    # Auto-start settings
    if sudo systemctl is-enabled virtuoso > /dev/null 2>&1; then
        echo -e "│ Boot Auto-start: ${GREEN}ENABLED${NC}"
    else
        echo -e "│ Boot Auto-start: ${YELLOW}DISABLED${NC}"
    fi
    
    if [ "$WEB_SERVER_AUTO_START" = "enabled" ]; then
        echo -e "│ Web Auto-start:  ${GREEN}ENABLED${NC}"
    else
        echo -e "│ Web Auto-start:  ${YELLOW}DISABLED${NC}"
    fi
    
    # Network info
    local ip_addr=$(ip -4 addr show | grep -oP "(?<=inet\s)\d+(\.\d+){3}" | grep -v "127.0.0.1" | head -1)
    echo -e "│ Server IP:       $ip_addr"
    echo -e "│ Dashboard URL:   http://$ip_addr:8003"
    echo -e "${BOLD}└───────────────────────────────────────────────────┘${NC}"
    echo ""
    
    # Maintenance Section
    echo -e "${BOLD}┌─ 🔧 MAINTENANCE ──────────────────────────────────┐${NC}"
    echo -e "│ Daily Restart:   ${CYAN}3:00 AM SGT${NC}"
    local last_restart=$(get_last_restart)
    echo -e "│ Last Restart:    $last_restart"
    
    # Check if cron job exists
    if crontab -l 2>/dev/null | grep -q restart_virtuoso; then
        echo -e "│ Cron Job:        ${GREEN}ACTIVE${NC}"
    else
        echo -e "│ Cron Job:        ${RED}INACTIVE${NC}"
    fi
    
    # Log file sizes
    local main_log_size=$(sudo journalctl -u virtuoso --disk-usage 2>/dev/null | grep -oP "\d+\.?\d*[MG]" || echo "N/A")
    local web_log_size=$(du -h /home/linuxuser/web_server.log 2>/dev/null | cut -f1 || echo "N/A")
    echo -e "│ Main Log Size:   $main_log_size"
    echo -e "│ Web Log Size:    $web_log_size"
    echo -e "${BOLD}└───────────────────────────────────────────────────┘${NC}"
}

# System management functions
system_info() {
    echo -e "${BOLD}${CYAN}System Information${NC}"
    echo "═══════════════════"
    echo ""
    echo -e "${BOLD}Hardware:${NC}"
    echo "  CPU: $(lscpu | grep "Model name" | cut -d: -f2 | xargs)"
    echo "  Cores: $(nproc)"
    echo "  Memory: $(free -h | grep Mem | awk "{print \$2}")"
    echo "  Disk: $(df -h / | tail -1 | awk "{print \$2}")"
    echo ""
    echo -e "${BOLD}Operating System:${NC}"
    echo "  OS: $(lsb_release -ds 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '"')"
    echo "  Kernel: $(uname -r)"
    echo "  Uptime: $(uptime -p)"
    echo ""
    echo -e "${BOLD}Network:${NC}"
    echo "  Hostname: $(hostname)"
    echo "  IP Address: $(ip -4 addr show | grep -oP "(?<=inet\s)\d+(\.\d+){3}" | grep -v "127.0.0.1" | head -1)"
    echo "  Public IP: $(curl -s ifconfig.me 2>/dev/null || echo "Unable to determine")"
    echo ""
    echo -e "${BOLD}Docker:${NC}"
    if command -v docker &> /dev/null; then
        echo "  Version: $(docker --version | cut -d" " -f3 | tr -d ",")"
        echo "  Containers: $(docker ps -q | wc -l) running"
    else
        echo "  Not installed"
    fi
}

network_test() {
    echo -e "${BOLD}${CYAN}Network Connectivity Test${NC}"
    echo "═════════════════════════"
    echo ""
    
    # Test local services
    echo -e "${BOLD}Local Services:${NC}"
    
    # Main service
    if sudo systemctl is-active virtuoso > /dev/null; then
        echo -e "  Main Service:     ${GREEN}✓${NC} Accessible"
    else
        echo -e "  Main Service:     ${RED}✗${NC} Not running"
    fi
    
    # Web server
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health 2>/dev/null | grep -q "200"; then
        echo -e "  Web Server:       ${GREEN}✓${NC} Responding (port 8003)"
    else
        echo -e "  Web Server:       ${RED}✗${NC} Not responding"
    fi
    
    echo ""
    echo -e "${BOLD}External Connectivity:${NC}"
    
    # DNS
    if nslookup google.com > /dev/null 2>&1; then
        echo -e "  DNS Resolution:   ${GREEN}✓${NC} Working"
    else
        echo -e "  DNS Resolution:   ${RED}✗${NC} Failed"
    fi
    
    # Internet
    if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
        echo -e "  Internet:         ${GREEN}✓${NC} Connected"
    else
        echo -e "  Internet:         ${RED}✗${NC} No connection"
    fi
    
    # API endpoints
    echo ""
    echo -e "${BOLD}API Endpoints:${NC}"
    
    # Bybit
    if curl -s -o /dev/null -w "%{http_code}" https://api.bybit.com/v5/market/time 2>/dev/null | grep -q "200"; then
        echo -e "  Bybit API:        ${GREEN}✓${NC} Reachable"
    else
        echo -e "  Bybit API:        ${RED}✗${NC} Unreachable"
    fi
    
    # Binance
    if curl -s -o /dev/null -w "%{http_code}" https://api.binance.com/api/v3/ping 2>/dev/null | grep -q "200"; then
        echo -e "  Binance API:      ${GREEN}✓${NC} Reachable"
    else
        echo -e "  Binance API:      ${RED}✗${NC} Unreachable"
    fi
}

backup_config() {
    echo -e "${BOLD}Creating configuration backup...${NC}"
    
    BACKUP_DIR="/home/linuxuser/backups"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/virtuoso_backup_$TIMESTAMP.tar.gz"
    
    mkdir -p $BACKUP_DIR
    
    # Create backup
    tar -czf $BACKUP_FILE \
        /home/linuxuser/.virtuoso_config \
        /home/linuxuser/trading/Virtuoso_ccxt/config/ \
        /home/linuxuser/trading/Virtuoso_ccxt/.env \
        /etc/systemd/system/virtuoso.service \
        2>/dev/null
    
    if [ -f $BACKUP_FILE ]; then
        echo -e "${GREEN}✅ Backup created: $BACKUP_FILE${NC}"
        echo "Size: $(du -h $BACKUP_FILE | cut -f1)"
        
        # Keep only last 7 backups
        ls -t $BACKUP_DIR/virtuoso_backup_*.tar.gz | tail -n +8 | xargs -r rm
        echo "Keeping last 7 backups"
    else
        echo -e "${RED}❌ Backup failed${NC}"
    fi
}

# Main control logic
case "$1" in
    "")
        # No argument - show control panel and menu
        display_control_panel
        echo ""
        echo -e "${BOLD}Available Commands:${NC}"
        echo -e "${BOLD}═══════════════════${NC}"
        echo ""
        echo -e "${BOLD}Service Control:${NC}"
        echo "  start       - Start all services"
        echo "  stop        - Stop all services"
        echo "  restart     - Restart all services"
        echo "  status      - Detailed service status"
        echo ""
        echo -e "${BOLD}Web Server:${NC}"
        echo "  web-start   - Start web server"
        echo "  web-stop    - Stop web server"
        echo "  web-restart - Restart web server"
        echo "  web-toggle  - Toggle auto-start"
        echo ""
        echo -e "${BOLD}System Control:${NC}"
        echo "  system      - System information"
        echo "  network     - Network connectivity test"
        echo "  backup      - Backup configuration"
        echo "  update      - Update system packages"
        echo "  reboot      - Reboot server (requires confirmation)"
        echo ""
        echo -e "${BOLD}Configuration:${NC}"
        echo "  enable      - Enable boot auto-start"
        echo "  disable     - Disable boot auto-start"
        echo "  config      - Show configuration"
        echo ""
        echo -e "${BOLD}Monitoring:${NC}"
        echo "  health      - Health check"
        echo "  logs        - View logs"
        echo "  logs-follow - Follow logs"
        echo "  top         - Resource monitor"
        echo ""
        echo -e "${BOLD}Maintenance:${NC}"
        echo "  clean       - Clean temp files"
        echo "  backup      - Backup configuration"
        echo ""
        echo -e "Usage: ${BOLD}vt [command]${NC}"
        ;;
        
    status)
        display_control_panel
        echo ""
        echo -e "${BOLD}📋 Detailed Service Status${NC}"
        echo -e "${BOLD}────────────────────────${NC}"
        echo ""
        check_main_service
        echo ""
        check_web_server
        ;;
        
    start)
        echo "Starting services..."
        sudo systemctl start virtuoso
        sleep 5
        
        load_config
        if [ "$WEB_SERVER_AUTO_START" = "enabled" ]; then
            start_web_server
        else
            echo -e "${YELLOW}ℹ️  Web server auto-start is disabled${NC}"
        fi
        
        echo ""
        display_control_panel
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
        else
            WEB_SERVER_AUTO_START="enabled"
            echo -e "${GREEN}✅ Web server auto-start ENABLED${NC}"
        fi
        save_config
        ;;
        
    enable)
        echo "Enabling auto-start for main service..."
        sudo systemctl enable virtuoso
        echo -e "${GREEN}✅ Main service will start on boot${NC}"
        ;;
        
    disable)
        echo "Disabling auto-start for main service..."
        sudo systemctl disable virtuoso
        echo -e "${YELLOW}⚠️  Main service will NOT start on boot${NC}"
        ;;
        
    system)
        system_info
        ;;
        
    network)
        network_test
        ;;
        
    backup)
        backup_config
        ;;
        
    update)
        echo -e "${BOLD}Updating system packages...${NC}"
        sudo apt update
        sudo apt list --upgradable
        echo ""
        read -p "Proceed with upgrade? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo apt upgrade -y
            echo -e "${GREEN}✅ System updated${NC}"
        else
            echo "Update cancelled"
        fi
        ;;
        
    reboot)
        echo -e "${YELLOW}⚠️  Server reboot requested${NC}"
        read -p "Are you sure you want to reboot? (yes/no): " -r
        if [ "$REPLY" = "yes" ]; then
            echo "Rebooting in 5 seconds..."
            sleep 5
            sudo reboot
        else
            echo "Reboot cancelled"
        fi
        ;;
        
    logs)
        echo -e "${BOLD}=== Main Service Logs (last 20) ===${NC}"
        sudo journalctl -u virtuoso -n 20 --no-pager
        echo ""
        echo -e "${BOLD}=== Web Server Logs (last 20) ===${NC}"
        tail -n 20 /home/linuxuser/web_server.log 2>/dev/null || echo "No logs"
        ;;
        
    logs-follow)
        echo "Following main service logs (Ctrl+C to exit)..."
        sudo journalctl -u virtuoso -f
        ;;
        
    health)
        echo -e "${BOLD}🏥 System Health Check${NC}"
        echo ""
        display_control_panel
        echo ""
        network_test
        ;;
        
    top)
        echo -e "${BOLD}Resource Monitor (q to quit)${NC}"
        sleep 2
        htop || top
        ;;
        
    config)
        echo -e "${BOLD}Current Configuration:${NC}"
        echo "═════════════════════"
        load_config
        echo "Main Service Auto-start: $(sudo systemctl is-enabled virtuoso 2>/dev/null || echo 'disabled')"
        echo "Web Server Auto-start:   $WEB_SERVER_AUTO_START"
        echo ""
        echo "Config file: $CONFIG_FILE"
        echo "Service file: /etc/systemd/system/virtuoso.service"
        ;;
        
    clean)
        echo "Cleaning up..."
        rm -f /tmp/virtuoso.lock
        sudo journalctl --vacuum-time=7d
        > /home/linuxuser/web_server.log
        echo -e "${GREEN}✅ Cleanup complete${NC}"
        ;;
        
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Run 'vt' without arguments to see available commands"
        exit 1
        ;;
esac
EOF'

# Make script executable
ssh $VPS_HOST 'chmod +x /home/linuxuser/virtuoso_control.sh'

# Update alias
ssh $VPS_HOST 'grep -q "alias vt=" ~/.bashrc || echo "alias vt=\"/home/linuxuser/virtuoso_control.sh\"" >> ~/.bashrc'

echo ""
echo "✅ Unified Control System installed!"
echo ""
echo "Features:"
echo "  • Complete service and system control"
echo "  • Visual control panel dashboard"
echo "  • System information and monitoring"
echo "  • Network connectivity testing"
echo "  • Configuration backup"
echo "  • Package updates"
echo "  • Resource monitoring"
echo ""
echo "Access with: ssh $VPS_HOST 'vt'"
echo "Or just type 'vt' after logging in"