#!/bin/bash
#
# vt - Virtuoso Trading Quick Command Tool
# A lightweight CLI for common operations
#

SERVICE_NAME="virtuoso"
API_URL="http://localhost:8001"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Quick status with minimal output
status() {
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${GREEN}●${NC} Running"
        if curl -s -f -m 1 $API_URL/health > /dev/null 2>&1; then
            echo -e "${GREEN}●${NC} API OK"
        else
            echo -e "${RED}●${NC} API Down"
        fi
    else
        echo -e "${RED}●${NC} Stopped"
    fi
}

# Intelligence system status
intelligence_status() {
    if ! systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${RED}●${NC} Service not running"
        return
    fi

    # Check Intelligence System API
    local intel_status=$(curl -s -f -m 3 "$API_URL/api/system/intelligence/status" 2>/dev/null)
    if [[ -n "$intel_status" ]]; then
        local enabled=$(echo "$intel_status" | jq -r '.intelligence_enabled // false' 2>/dev/null)
        local components=$(echo "$intel_status" | jq -r '.components_enabled // 0' 2>/dev/null)
        local total_components=$(echo "$intel_status" | jq -r '.total_components // 8' 2>/dev/null)
        
        if [[ "$enabled" == "true" ]]; then
            echo -e "${GREEN}●${NC} Intelligence System: ENABLED"
            echo -e "${GREEN}●${NC} Components: $components/$total_components active"
            
            # Show component details if available
            if [[ "$components" == "$total_components" ]]; then
                echo -e "${GREEN}●${NC} All systems operational"
            else
                echo -e "${YELLOW}●${NC} Some components inactive"
            fi
        else
            echo -e "${YELLOW}●${NC} Intelligence System: FALLBACK MODE"
        fi
    else
        echo -e "${YELLOW}●${NC} Intelligence status unknown"
    fi
}

# Show usage
usage() {
    cat << EOF
Virtuoso Trading Quick Commands

Usage: vt [command]

Commands:
  status    - Show service status
  start     - Start service
  stop      - Stop service  
  restart   - Restart service
  logs      - View live logs
  errors    - View recent errors
  health    - Check API health
  stats     - Show performance stats
  intel     - Intelligence System status
  
Quick shortcuts:
  vt s      - status
  vt r      - restart
  vt l      - logs
  vt e      - errors
  vt i      - intelligence status

Examples:
  vt status
  vt restart
  vt intel
  vt logs | grep ERROR

Intelligence System:
  The Intelligence System provides advanced API optimization,
  connection pooling, and timeout prevention for Bybit trading.

EOF
}

# Enhanced status with intelligence info
enhanced_status() {
    echo "=== Virtuoso Trading System Status ==="
    status
    echo
    intelligence_status
}

# Parse command
case "${1:-help}" in
    status|s)
        enhanced_status
        ;;
    start)
        sudo systemctl start $SERVICE_NAME
        echo "Starting..."
        sleep 2
        enhanced_status
        ;;
    stop)
        sudo systemctl stop $SERVICE_NAME
        echo "Stopped"
        ;;
    restart|r)
        sudo systemctl restart $SERVICE_NAME
        echo "Restarting..."
        sleep 3
        enhanced_status
        ;;
    logs|l)
        sudo journalctl -u $SERVICE_NAME -f
        ;;
    errors|e)
        sudo journalctl -u $SERVICE_NAME -p err -n 50 --no-pager
        ;;
    health|h)
        curl -s $API_URL/health | jq . 2>/dev/null || echo "API not responding"
        ;;
    intel|i)
        intelligence_status
        ;;
    stats)
        if systemctl is-active --quiet $SERVICE_NAME; then
            PID=$(systemctl show $SERVICE_NAME --property=MainPID | cut -d'=' -f2)
            if [[ "$PID" != "0" ]]; then
                ps -p $PID -o pid,pcpu,pmem,etime,args --no-headers
            fi
        else
            echo "Service not running"
        fi
        ;;
    help|--help|-h|*)
        usage
        ;;
esac