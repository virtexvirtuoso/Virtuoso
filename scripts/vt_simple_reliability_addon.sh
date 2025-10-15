#!/bin/bash
# Simple VT Reliability Add-on
# Adds reliability features as new commands without modifying existing VT script

PROJECT_ROOT="/home/linuxuser/trading/Virtuoso_ccxt"

# Colors
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
BOLD="\033[1m"
NC="\033[0m"

show_usage() {
    echo -e "${BOLD}VT Reliability Add-on Commands${NC}"
    echo -e "${BOLD}═════════════════════════════${NC}"
    echo ""
    echo -e "${BOLD}Emergency & Quick Fixes:${NC}"
    echo "  vtr fix           Emergency monitoring API fix"
    echo "  vtr restart       Restart monitoring API safely"
    echo "  vtr health        Check monitoring API health"
    echo ""
    echo -e "${BOLD}Status & Information:${NC}"
    echo "  vtr status        Show reliability infrastructure status"
    echo "  vtr logs          View monitoring logs"
    echo "  vtr ports         Check which ports monitoring API is using"
    echo ""
    echo -e "${BOLD}Configuration:${NC}"
    echo "  vtr setup         Setup reliability infrastructure"
    echo "  vtr cron          Show/manage cron jobs"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  vtr fix           # Quick fix for monitoring API issues"
    echo "  vtr status        # Show complete reliability status"
    echo "  vtr logs | tail   # View recent logs"
}

check_monitoring_ports() {
    echo -e "${BOLD}🔍 Monitoring API Port Check${NC}"
    echo -e "${BOLD}──────────────────────────${NC}"

    local found=false
    for port in 8001 8003 8004 8005; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            local process=$(lsof -ti:$port 2>/dev/null | head -1)
            if [ -n "$process" ]; then
                local proc_name=$(ps -p $process -o comm= 2>/dev/null || echo "unknown")
                echo -e "Port $port:                  ${GREEN}✅ In use by PID $process ($proc_name)${NC}"

                # Test if it responds to health check
                if curl -s -f -m 2 "http://localhost:$port/health" > /dev/null 2>&1; then
                    echo -e "                             ${GREEN}✅ Health check: PASS${NC}"
                else
                    echo -e "                             ${YELLOW}⚠️  Health check: FAIL${NC}"
                fi
                found=true
            else
                echo -e "Port $port:                  ${YELLOW}⚠️  Bound but no process found${NC}"
            fi
        else
            echo -e "Port $port:                  ${RED}❌ Not in use${NC}"
        fi
    done

    if [ "$found" = false ]; then
        echo ""
        echo -e "${RED}❌ No monitoring API found on any expected port${NC}"
        echo -e "${YELLOW}💡 Try: vtr fix${NC}"
    fi
}

emergency_fix() {
    echo -e "${BOLD}🚨 Monitoring API Emergency Fix${NC}"
    echo -e "${BOLD}══════════════════════════════${NC}"

    cd "$PROJECT_ROOT" || { echo "❌ Cannot access project directory"; exit 1; }

    if [ ! -f "scripts/monitoring_reliability_fixes.py" ]; then
        echo -e "${RED}❌ Reliability script not found${NC}"
        echo "Please deploy the reliability infrastructure first."
        exit 1
    fi

    echo "🔧 Running emergency fix..."
    ./venv311/bin/python scripts/monitoring_reliability_fixes.py fix

    echo ""
    echo -e "${GREEN}✅ Emergency fix completed${NC}"
    echo ""
    echo "Verifying fix..."
    sleep 2
    check_health
}

restart_monitoring() {
    echo -e "${BOLD}🔄 Restarting Monitoring API${NC}"
    echo -e "${BOLD}════════════════════════════${NC}"

    cd "$PROJECT_ROOT" || { echo "❌ Cannot access project directory"; exit 1; }

    if [ ! -f "scripts/monitoring_reliability_fixes.py" ]; then
        echo -e "${RED}❌ Reliability script not found${NC}"
        exit 1
    fi

    ./venv311/bin/python scripts/monitoring_reliability_fixes.py restart

    echo ""
    echo -e "${GREEN}✅ Restart completed${NC}"
}

check_health() {
    echo -e "${BOLD}🔍 Monitoring API Health Check${NC}"
    echo -e "${BOLD}═════════════════════════════${NC}"

    cd "$PROJECT_ROOT" || { echo "❌ Cannot access project directory"; exit 1; }

    if [ ! -f "scripts/monitoring_reliability_fixes.py" ]; then
        echo -e "${RED}❌ Reliability script not found${NC}"
        echo "Basic health check:"
        check_monitoring_ports
        exit 1
    fi

    ./venv311/bin/python scripts/monitoring_reliability_fixes.py health
}

show_reliability_status() {
    echo -e "${BOLD}🛡️ Reliability Infrastructure Status${NC}"
    echo -e "${BOLD}═══════════════════════════════════${NC}"
    echo ""

    # Check project directory
    if [ ! -d "$PROJECT_ROOT" ]; then
        echo -e "${RED}❌ Project directory not found: $PROJECT_ROOT${NC}"
        exit 1
    fi

    # Check scripts
    echo -e "${BOLD}📁 Scripts${NC}"
    echo -e "${BOLD}─────────${NC}"
    if [ -f "$PROJECT_ROOT/scripts/monitoring_reliability_fixes.py" ]; then
        echo -e "Reliability fixes:           ${GREEN}✅ Available${NC}"
    else
        echo -e "Reliability fixes:           ${RED}❌ Missing${NC}"
    fi

    if [ -f "$PROJECT_ROOT/scripts/monitoring_health_check.py" ]; then
        echo -e "Health monitoring:           ${GREEN}✅ Available${NC}"
    else
        echo -e "Health monitoring:           ${RED}❌ Missing${NC}"
    fi

    # Check automation
    echo ""
    echo -e "${BOLD}⚙️ Automation${NC}"
    echo -e "${BOLD}────────────${NC}"
    local cron_count=$(crontab -l 2>/dev/null | grep -c "monitoring" || echo "0")
    if [ "$cron_count" -gt 0 ]; then
        echo -e "Cron jobs configured:        ${GREEN}✅ $cron_count active${NC}"
        echo -e "Next health check:           ${BLUE}$(crontab -l | grep monitoring_health_check | awk '{print $1,$2,$3,$4,$5}' | head -1)${NC}"
    else
        echo -e "Cron jobs configured:        ${RED}❌ None${NC}"
    fi

    # Check systemd
    echo ""
    echo -e "${BOLD}🖥️ System Services${NC}"
    echo -e "${BOLD}──────────────────${NC}"
    if [ -f "/etc/systemd/system/virtuoso-monitoring-api.service" ]; then
        echo -e "Systemd service:             ${GREEN}✅ Available${NC}"
        if systemctl is-active --quiet virtuoso-monitoring-api 2>/dev/null; then
            echo -e "Service status:              ${GREEN}✅ Active${NC}"
        else
            echo -e "Service status:              ${YELLOW}⚠️  Inactive${NC}"
        fi
    else
        echo -e "Systemd service:             ${YELLOW}⚠️  Not available${NC}"
    fi

    # Check current monitoring API status
    echo ""
    check_monitoring_ports

    # Show recent activity
    echo ""
    echo -e "${BOLD}📊 Recent Activity${NC}"
    echo -e "${BOLD}─────────────────${NC}"
    if [ -f "$PROJECT_ROOT/logs/cron_health.log" ]; then
        local last_check=$(tail -1 "$PROJECT_ROOT/logs/cron_health.log" 2>/dev/null | head -c 50)
        if [ -n "$last_check" ]; then
            echo -e "Last health check:           ${GREEN}✅ $(echo "$last_check" | cut -c1-30)...${NC}"
        else
            echo -e "Last health check:           ${YELLOW}⚠️  No recent activity${NC}"
        fi
    else
        echo -e "Health check logs:           ${YELLOW}⚠️  No logs found${NC}"
    fi
}

view_logs() {
    echo -e "${BOLD}📄 Monitoring Logs${NC}"
    echo -e "${BOLD}═════════════════${NC}"
    echo ""

    # Main monitoring API log
    if [ -f "$PROJECT_ROOT/logs/monitoring_api.log" ]; then
        echo -e "${BOLD}🔧 Monitoring API Log (last 15 lines):${NC}"
        echo -e "${BOLD}─────────────────────────────────────${NC}"
        tail -15 "$PROJECT_ROOT/logs/monitoring_api.log"
        echo ""
    else
        echo -e "${YELLOW}⚠️  No monitoring API log found${NC}"
        echo ""
    fi

    # Health check log
    if [ -f "$PROJECT_ROOT/logs/cron_health.log" ]; then
        echo -e "${BOLD}🔍 Health Check Log (last 10 lines):${NC}"
        echo -e "${BOLD}───────────────────────────────────${NC}"
        tail -10 "$PROJECT_ROOT/logs/cron_health.log"
        echo ""
    else
        echo -e "${YELLOW}⚠️  No health check log found${NC}"
        echo ""
    fi

    # Error log if exists
    if [ -f "$PROJECT_ROOT/logs/error.log" ]; then
        echo -e "${BOLD}❌ Recent Errors (last 5 lines):${NC}"
        echo -e "${BOLD}────────────────────────────────${NC}"
        grep -i "monitoring\|api" "$PROJECT_ROOT/logs/error.log" | tail -5 || echo "No monitoring-related errors found"
    fi
}

show_cron_status() {
    echo -e "${BOLD}⏰ Cron Job Status${NC}"
    echo -e "${BOLD}═════════════════${NC}"
    echo ""

    local monitoring_jobs=$(crontab -l 2>/dev/null | grep monitoring || echo "")

    if [ -n "$monitoring_jobs" ]; then
        echo -e "${BOLD}Active monitoring cron jobs:${NC}"
        echo "$monitoring_jobs"
        echo ""
        echo -e "${BOLD}Next execution times:${NC}"
        echo "Health check: Every 5 minutes"
        echo "Daily restart: 3:15 AM daily"
    else
        echo -e "${RED}❌ No monitoring cron jobs found${NC}"
        echo ""
        echo -e "${YELLOW}💡 To set up automated monitoring:${NC}"
        echo "Run the reliability setup script or add manually:"
        echo ""
        echo "*/5 * * * * cd $PROJECT_ROOT && ./venv311/bin/python scripts/monitoring_health_check.py --once"
        echo "15 3 * * * cd $PROJECT_ROOT && ./venv311/bin/python scripts/monitoring_reliability_fixes.py restart"
    fi
}

# Main command parsing
case "${1:-help}" in
    fix)
        emergency_fix
        ;;
    restart)
        restart_monitoring
        ;;
    health)
        check_health
        ;;
    status)
        show_reliability_status
        ;;
    logs)
        view_logs
        ;;
    ports)
        check_monitoring_ports
        ;;
    cron)
        show_cron_status
        ;;
    help|"")
        show_usage
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac