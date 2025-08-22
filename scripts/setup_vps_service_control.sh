#!/bin/bash

# Enhanced VPS service control with web server management
# Manages both Virtuoso service and web server

VPS_HOST="linuxuser@45.77.40.77"

echo "Setting up enhanced service control on VPS..."

# Create comprehensive service control script on VPS
ssh $VPS_HOST 'cat > /home/linuxuser/virtuoso_control.sh << "EOF"
#!/bin/bash

# Virtuoso Trading Service Control with Web Server Management
# Provides unified control for all components

# Colors for output
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
NC="\033[0m" # No Color

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
}

# Function to start web server
start_web_server() {
    echo "Starting web server..."
    
    # Kill any existing web server processes
    pkill -f "python.*web_server.py" 2>/dev/null
    sleep 2
    
    # Start web server in background
    cd /home/linuxuser/trading/Virtuoso_ccxt
    nohup /home/linuxuser/trading/venv311/bin/python src/web_server.py > /home/linuxuser/web_server.log 2>&1 &
    
    sleep 3
    
    # Verify it started
    if pgrep -f "python.*web_server.py" > /dev/null; then
        echo -e "${GREEN}✅ Web server started successfully${NC}"
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
        sudo systemctl status virtuoso --no-pager | head -n 10
    else
        echo -e "${RED}● Virtuoso service is not running${NC}"
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
        echo "Starting all services..."
        sudo systemctl start virtuoso
        sleep 5
        start_web_server
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
        
    clean)
        echo "Cleaning up temporary files and logs..."
        rm -f /tmp/virtuoso.lock
        sudo journalctl --vacuum-time=7d
        echo > /home/linuxuser/web_server.log
        echo -e "${GREEN}✅ Cleanup complete${NC}"
        ;;
        
    *)
        echo "Usage: $0 {status|start|stop|restart|web-start|web-stop|web-restart|logs|logs-follow|health|clean}"
        echo ""
        echo "Commands:"
        echo "  status      - Show status of all services"
        echo "  start       - Start all services"
        echo "  stop        - Stop all services"
        echo "  restart     - Restart all services"
        echo "  web-start   - Start only web server"
        echo "  web-stop    - Stop only web server"
        echo "  web-restart - Restart only web server"
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

# Create enhanced restart script for cron
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

# Start all services
/home/linuxuser/virtuoso_control.sh start >> $LOG_FILE 2>&1
sleep 10

# Perform health check
HEALTH_CHECK=$(/home/linuxuser/virtuoso_control.sh health 2>&1)
echo "$HEALTH_CHECK" >> $LOG_FILE

# Check if services are running
if sudo systemctl is-active virtuoso > /dev/null && pgrep -f "python.*web_server.py" > /dev/null; then
    echo "$(date): All services restarted successfully" >> $LOG_FILE
    
    # Send success notification (optional - requires mail setup)
    # echo "Virtuoso services restarted successfully at $(date)" | mail -s "Virtuoso Restart Success" admin@example.com
else
    echo "$(date): ERROR - Service restart failed" >> $LOG_FILE
    
    # Try once more
    /home/linuxuser/virtuoso_control.sh start >> $LOG_FILE 2>&1
    
    # Send failure notification (optional)
    # echo "Virtuoso service restart failed at $(date). Manual intervention required." | mail -s "Virtuoso Restart Failed" admin@example.com
fi

echo "----------------------------------------" >> $LOG_FILE
EOF'

# Make restart script executable
ssh $VPS_HOST 'chmod +x /home/linuxuser/restart_virtuoso.sh'

# Update crontab for daily restart at 3 AM SGT
ssh $VPS_HOST '(crontab -l 2>/dev/null | grep -v restart_virtuoso; echo "0 3 * * * /home/linuxuser/restart_virtuoso.sh") | crontab -'

# Create a convenient alias for the control script
ssh $VPS_HOST 'echo "alias vt=\"/home/linuxuser/virtuoso_control.sh\"" >> ~/.bashrc'

echo ""
echo "✅ Enhanced service control setup complete!"
echo ""
echo "Available commands on VPS:"
echo "  vt status      - Check all services"
echo "  vt start       - Start all services"
echo "  vt stop        - Stop all services"
echo "  vt restart     - Restart all services"
echo "  vt health      - Perform health check"
echo "  vt logs        - View recent logs"
echo "  vt logs-follow - Follow logs in real-time"
echo ""
echo "Daily restart configured for 3:00 AM SGT with web server management"
echo "Logs saved to: /home/linuxuser/virtuoso_restart.log"
echo ""
echo "To check service status now:"
echo "ssh $VPS_HOST 'virtuoso_control.sh status'"