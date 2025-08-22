#!/bin/bash

# Enhanced VPS service control with web server management and auto-start toggle
# Manages both Virtuoso service and web server with configurable auto-start

VPS_HOST="linuxuser@45.77.40.77"

echo "Setting up enhanced service control with web server toggle..."

# Create comprehensive service control script on VPS
ssh $VPS_HOST 'cat > /home/linuxuser/virtuoso_control.sh << "EOF"
#!/bin/bash

# Virtuoso Trading Service Control with Web Server Management
# Provides unified control for all components with auto-start toggle

# Configuration file for web server auto-start
CONFIG_FILE="/home/linuxuser/.virtuoso_config"

# Colors for output
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
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

# Main control logic
case "$1" in
    status)
        echo "=====================================
  Virtuoso Trading Service Control
====================================="
        echo ""
        check_main_service
        echo ""
        check_web_server
        echo ""
        
        # Show recent logs
        echo "Recent logs (last 5 lines):"
        echo "Main service:"
        sudo journalctl -u virtuoso -n 5 --no-pager
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
        $0 status
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
        echo "=== Main Service Logs (last 20 lines) ==="
        sudo journalctl -u virtuoso -n 20 --no-pager
        echo ""
        echo "=== Web Server Logs (last 20 lines) ==="
        tail -n 20 /home/linuxuser/web_server.log 2>/dev/null || echo "No web server logs found"
        ;;
        
    logs-follow)
        echo "Following logs (Ctrl+C to exit)..."
        echo "Main service logs in real-time:"
        sudo journalctl -u virtuoso -f
        ;;
        
    health)
        echo "Performing health check..."
        echo ""
        
        # Check service
        check_main_service
        echo ""
        check_web_server
        echo ""
        
        # Check API endpoints
        echo "API Endpoint Checks:"
        
        # Health endpoint
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            echo -e "${GREEN}✅ /health endpoint: OK${NC}"
        else
            echo -e "${RED}❌ /health endpoint: Failed (HTTP $HTTP_CODE)${NC}"
        fi
        
        # Dashboard endpoint
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/dashboard 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            echo -e "${GREEN}✅ /dashboard endpoint: OK${NC}"
        else
            echo -e "${YELLOW}⚠️  /dashboard endpoint: HTTP $HTTP_CODE${NC}"
        fi
        
        # System resources
        echo ""
        echo "System Resources:"
        echo "Memory: $(free -h | grep Mem | awk "{print \$3\"/\"\$2}")"
        echo "CPU Load: $(uptime | awk -F"load average:" "{print \$2}")"
        echo "Disk: $(df -h / | tail -1 | awk "{print \$3\"/\"\$2\" used\"}")"
        ;;
        
    config)
        echo "Current Configuration:"
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
        echo "Usage: $0 {status|start|stop|restart|web-start|web-stop|web-restart|web-toggle|enable|disable|logs|logs-follow|health|config|clean}"
        echo ""
        echo "Service Control:"
        echo "  status      - Show status of all services"
        echo "  start       - Start main service (and web if enabled)"
        echo "  stop        - Stop all services"
        echo "  restart     - Restart all services"
        echo ""
        echo "Web Server Control:"
        echo "  web-start   - Start only web server"
        echo "  web-stop    - Stop only web server"
        echo "  web-restart - Restart only web server"
        echo "  web-toggle  - Toggle web server auto-start with main service"
        echo ""
        echo "Auto-start Configuration:"
        echo "  enable      - Enable main service auto-start on boot"
        echo "  disable     - Disable main service auto-start on boot"
        echo "  config      - Show current configuration"
        echo ""
        echo "Monitoring:"
        echo "  logs        - Show recent logs"
        echo "  logs-follow - Follow logs in real-time"
        echo "  health      - Perform health check"
        echo "  clean       - Clean temporary files and old logs"
        exit 1
        ;;
esac
EOF'

# Make script executable
ssh $VPS_HOST 'chmod +x /home/linuxuser/virtuoso_control.sh'

# Update the restart script to respect web server auto-start setting
ssh $VPS_HOST 'cat > /home/linuxuser/restart_virtuoso.sh << "EOF"
#!/bin/bash
# Enhanced Virtuoso service restart script with web server management
# Runs daily at 3 AM SGT to prevent memory leaks

LOG_FILE="/home/linuxuser/virtuoso_restart.log"

echo "$(date): Starting Virtuoso restart sequence" >> $LOG_FILE

# Use the control script for clean restart
/home/linuxuser/virtuoso_control.sh stop >> $LOG_FILE 2>&1
sleep 5

# Clean up before restart
/home/linuxuser/virtuoso_control.sh clean >> $LOG_FILE 2>&1

# Start services (will respect web server auto-start setting)
/home/linuxuser/virtuoso_control.sh start >> $LOG_FILE 2>&1
sleep 10

# Perform health check
HEALTH_CHECK=$(/home/linuxuser/virtuoso_control.sh health 2>&1)
echo "$HEALTH_CHECK" >> $LOG_FILE

# Check if main service is running
if sudo systemctl is-active virtuoso > /dev/null; then
    echo "$(date): Main service restarted successfully" >> $LOG_FILE
    
    # Check web server based on config
    source /home/linuxuser/.virtuoso_config 2>/dev/null
    if [ "$WEB_SERVER_AUTO_START" = "enabled" ]; then
        if pgrep -f "python.*web_server.py" > /dev/null; then
            echo "$(date): Web server restarted successfully" >> $LOG_FILE
        else
            echo "$(date): WARNING - Web server failed to start" >> $LOG_FILE
            /home/linuxuser/virtuoso_control.sh web-start >> $LOG_FILE 2>&1
        fi
    else
        echo "$(date): Web server auto-start is disabled (skipped)" >> $LOG_FILE
    fi
else
    echo "$(date): ERROR - Service restart failed" >> $LOG_FILE
    
    # Try once more
    /home/linuxuser/virtuoso_control.sh start >> $LOG_FILE 2>&1
fi

echo "----------------------------------------" >> $LOG_FILE
EOF'

# Make restart script executable
ssh $VPS_HOST 'chmod +x /home/linuxuser/restart_virtuoso.sh'

# Set default configuration (web server auto-start enabled)
ssh $VPS_HOST 'echo "WEB_SERVER_AUTO_START=\"enabled\"" > /home/linuxuser/.virtuoso_config'

# Update alias
ssh $VPS_HOST 'grep -q "alias vt=" ~/.bashrc || echo "alias vt=\"/home/linuxuser/virtuoso_control.sh\"" >> ~/.bashrc'

echo ""
echo "✅ Enhanced service control with toggle feature setup complete!"
echo ""
echo "Available commands on VPS:"
echo "  vt status      - Check all services"
echo "  vt start       - Start services (respects auto-start settings)"
echo "  vt stop        - Stop all services"
echo "  vt restart     - Restart all services"
echo "  vt health      - Perform health check"
echo "  vt config      - Show configuration"
echo ""
echo "Auto-start configuration:"
echo "  vt enable      - Enable main service auto-start on boot"
echo "  vt disable     - Disable main service auto-start on boot"
echo "  vt web-toggle  - Toggle web server auto-start with main service"
echo ""
echo "Current settings:"
echo "  Main service auto-start: ENABLED (on boot)"
echo "  Web server auto-start: ENABLED (with main service)"
echo ""
echo "To check current configuration:"
echo "ssh $VPS_HOST 'virtuoso_control.sh config'"