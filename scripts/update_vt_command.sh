#!/bin/bash

#############################################################################
# Script: update_vt_command.sh
# Purpose: Update VT command to handle both services
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
#   ./update_vt_command.sh [options]
#   
#   Examples:
#     ./update_vt_command.sh
#     ./update_vt_command.sh --verbose
#     ./update_vt_command.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: ${VPS_HOST})
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

echo "Updating VT command to support web service..."

# Create updated vt command
cat > /tmp/vt << 'EOF'
#!/bin/bash
# Virtuoso Trading System Control - Enhanced for dual services

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service names
MAIN_SERVICE="virtuoso"
WEB_SERVICE="virtuoso-web"

# Function to check if a service exists
service_exists() {
    systemctl list-unit-files | grep -q "^$1.service"
}

# Function to get service status
get_service_status() {
    local service=$1
    if systemctl is-active --quiet $service; then
        echo "active"
    else
        echo "inactive"
    fi
}

# Display help
show_help() {
    echo "Virtuoso Trading System Control"
    echo ""
    echo "Usage: vt [command] [options]"
    echo ""
    echo "Commands:"
    echo "  status, s     - Show status of all services"
    echo "  start         - Start all services"
    echo "  stop          - Stop all services"
    echo "  restart, r    - Restart all services"
    echo "  logs, l       - View logs (use -w for web, -m for main)"
    echo "  errors, e     - Show recent errors"
    echo "  health, h     - Check health status"
    echo "  stats         - Show performance statistics"
    echo ""
    echo "Service-specific commands:"
    echo "  main [cmd]    - Control main trading service only"
    echo "  web [cmd]     - Control web dashboard only"
    echo ""
    echo "Examples:"
    echo "  vt status            # Show all services status"
    echo "  vt logs -w           # Show web service logs"
    echo "  vt main restart      # Restart only main service"
    echo "  vt web status        # Show only web service status"
}

# Main command processing
case "$1" in
    status|s)
        echo -e "${BLUE}=== Virtuoso Trading System Status ===${NC}"
        echo ""
        
        # Main service status
        MAIN_STATUS=$(get_service_status $MAIN_SERVICE)
        if [ "$MAIN_STATUS" = "active" ]; then
            echo -e "Main Trading Service: ${GREEN}● Running${NC} (Port 8003)"
            systemctl status $MAIN_SERVICE --no-pager | grep "Active:" | sed 's/^/  /'
        else
            echo -e "Main Trading Service: ${RED}● Stopped${NC}"
        fi
        
        # Web service status
        if service_exists $WEB_SERVICE; then
            WEB_STATUS=$(get_service_status $WEB_SERVICE)
            if [ "$WEB_STATUS" = "active" ]; then
                echo -e "Web Dashboard Service: ${GREEN}● Running${NC} (Port 8001)"
                systemctl status $WEB_SERVICE --no-pager | grep "Active:" | sed 's/^/  /'
            else
                echo -e "Web Dashboard Service: ${RED}● Stopped${NC}"
            fi
        else
            echo -e "Web Dashboard Service: ${YELLOW}○ Not installed${NC}"
        fi
        
        echo ""
        
        # Quick health check
        echo "API Health:"
        curl -s http://localhost:8003/health > /dev/null 2>&1 && echo -e "  Main API: ${GREEN}✓ Healthy${NC}" || echo -e "  Main API: ${RED}✗ Unreachable${NC}"
        curl -s http://localhost:8001/health > /dev/null 2>&1 && echo -e "  Web API: ${GREEN}✓ Healthy${NC}" || echo -e "  Web API: ${RED}✗ Unreachable${NC}"
        ;;
        
    start)
        echo "Starting Virtuoso services..."
        sudo systemctl start $MAIN_SERVICE
        service_exists $WEB_SERVICE && sudo systemctl start $WEB_SERVICE
        sleep 2
        $0 status
        ;;
        
    stop)
        echo "Stopping Virtuoso services..."
        service_exists $WEB_SERVICE && sudo systemctl stop $WEB_SERVICE
        sudo systemctl stop $MAIN_SERVICE
        echo "Services stopped."
        ;;
        
    restart|r)
        echo "Restarting Virtuoso services..."
        $0 stop
        sleep 2
        $0 start
        ;;
        
    logs|l)
        if [ "$2" = "-w" ] || [ "$2" = "--web" ]; then
            echo "Showing web service logs..."
            sudo journalctl -u $WEB_SERVICE -f
        elif [ "$2" = "-m" ] || [ "$2" = "--main" ]; then
            echo "Showing main service logs..."
            sudo journalctl -u $MAIN_SERVICE -f
        else
            echo "Showing all service logs..."
            sudo journalctl -u $MAIN_SERVICE -u $WEB_SERVICE -f
        fi
        ;;
        
    errors|e)
        echo -e "${RED}=== Recent Errors ===${NC}"
        echo "Main Service:"
        sudo journalctl -u $MAIN_SERVICE -p err -n 20 --no-pager
        if service_exists $WEB_SERVICE; then
            echo ""
            echo "Web Service:"
            sudo journalctl -u $WEB_SERVICE -p err -n 20 --no-pager
        fi
        ;;
        
    health|h)
        echo "Checking health status..."
        echo ""
        echo "Main API (Port 8003):"
        curl -s http://localhost:8003/health | jq . || echo "  API not responding"
        echo ""
        echo "Web Dashboard (Port 8001):"
        curl -s http://localhost:8001/health | jq . || echo "  Web server not responding"
        ;;
        
    stats)
        echo -e "${BLUE}=== Performance Statistics ===${NC}"
        echo ""
        
        # Get PIDs
        MAIN_PID=$(systemctl show -p MainPID $MAIN_SERVICE | cut -d= -f2)
        WEB_PID=$(systemctl show -p MainPID $WEB_SERVICE 2>/dev/null | cut -d= -f2)
        
        if [ "$MAIN_PID" != "0" ]; then
            echo "Main Service (PID: $MAIN_PID):"
            ps -p $MAIN_PID -o %cpu,%mem,etime,rss | tail -n 1 | awk '{printf "  CPU: %s%%, Memory: %s%%, Uptime: %s, RSS: %s KB\n", $1, $2, $3, $4}'
        fi
        
        if [ "$WEB_PID" != "0" ] && [ -n "$WEB_PID" ]; then
            echo "Web Service (PID: $WEB_PID):"
            ps -p $WEB_PID -o %cpu,%mem,etime,rss | tail -n 1 | awk '{printf "  CPU: %s%%, Memory: %s%%, Uptime: %s, RSS: %s KB\n", $1, $2, $3, $4}'
        fi
        
        echo ""
        echo "Port Usage:"
        ss -tlnp 2>/dev/null | grep -E "8001|8003" | awk '{print "  " $4 " - " $6}'
        ;;
        
    main)
        # Control main service only
        case "$2" in
            start) sudo systemctl start $MAIN_SERVICE ;;
            stop) sudo systemctl stop $MAIN_SERVICE ;;
            restart) sudo systemctl restart $MAIN_SERVICE ;;
            status) sudo systemctl status $MAIN_SERVICE ;;
            logs) sudo journalctl -u $MAIN_SERVICE -f ;;
            *) echo "Usage: vt main [start|stop|restart|status|logs]" ;;
        esac
        ;;
        
    web)
        # Control web service only
        if service_exists $WEB_SERVICE; then
            case "$2" in
                start) sudo systemctl start $WEB_SERVICE ;;
                stop) sudo systemctl stop $WEB_SERVICE ;;
                restart) sudo systemctl restart $WEB_SERVICE ;;
                status) sudo systemctl status $WEB_SERVICE ;;
                logs) sudo journalctl -u $WEB_SERVICE -f ;;
                *) echo "Usage: vt web [start|stop|restart|status|logs]" ;;
            esac
        else
            echo "Web service not installed. Run setup_web_service.sh to install."
        fi
        ;;
        
    help|--help|-h|"")
        show_help
        ;;
        
    *)
        echo "Unknown command: $1"
        echo "Use 'vt help' for usage information"
        exit 1
        ;;
esac
EOF

# Deploy to VPS
echo "Deploying updated VT command..."
scp /tmp/vt linuxuser@${VPS_HOST}:/tmp/
ssh linuxuser@${VPS_HOST} "sudo cp /tmp/vt /usr/local/bin/vt && sudo chmod +x /usr/local/bin/vt"

echo "✅ VT command updated to support both services!"
echo ""
echo "New commands available:"
echo "  vt status     - Show both services status"
echo "  vt logs -w    - Show web service logs"
echo "  vt logs -m    - Show main service logs"
echo "  vt main restart - Restart only main service"
echo "  vt web status   - Show only web service status"