#!/bin/bash
# VT Control Panel Reliability Enhancements
# This script adds reliability features to the existing VT control panel

PROJECT_ROOT="/home/linuxuser/trading/Virtuoso_ccxt"
VT_SCRIPT="/home/linuxuser/bin/vt"

# Enhanced monitoring API detection function
enhanced_monitoring_api_check() {
    local monitor_text=""
    local monitor_pid=""
    local monitor_port=""

    # Check if monitoring API process is running
    if monitor_pid=$(pgrep -f "monitoring_api.py" 2>/dev/null | head -1); then
        # Try to detect which port it's using
        for port in 8001 8003 8004 8005; do
            if curl -s -f -m 2 "http://localhost:$port/health" > /dev/null 2>&1; then
                monitor_port="$port"
                break
            fi
        done

        if [ -n "$monitor_port" ]; then
            monitor_text="● RUNNING (:$monitor_port, PID: $monitor_pid)"
            printf "${BOLD}${CYAN}║${NC}  Monitoring API:      ${BOLD}${CYAN}│${NC} ${GREEN}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$monitor_text"
        else
            monitor_text="● RUNNING (PID: $monitor_pid, Port: Unknown)"
            printf "${BOLD}${CYAN}║${NC}  Monitoring API:      ${BOLD}${CYAN}│${NC} ${YELLOW}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$monitor_text"
        fi
    else
        monitor_text="○ STOPPED"
        printf "${BOLD}${CYAN}║${NC}  Monitoring API:      ${BOLD}${CYAN}│${NC} ${RED}%38s${NC}${BOLD}${CYAN}║${NC}\n" "$monitor_text"
    fi
}

# Enhanced health check function for monitoring API
enhanced_monitoring_health_check() {
    echo -e "${BOLD}🔧 Monitoring API Health Check${NC}"
    echo -e "${BOLD}────────────────────────────${NC}"

    # Check monitoring API on all possible ports
    local found_port=""
    for port in 8001 8003 8004 8005; do
        local http_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/health" 2>/dev/null)
        if [ "$http_code" = "200" ]; then
            echo -e "Monitoring API (:$port):     ${GREEN}✅ OK (HTTP 200)${NC}"
            found_port="$port"
            break
        fi
    done

    if [ -z "$found_port" ]; then
        echo -e "Monitoring API:              ${RED}❌ Not responding on any port${NC}"
        echo -e "                             ${YELLOW}💡 Try: vt monitor-fix${NC}"
    fi

    # Check reliability infrastructure
    echo ""
    echo -e "${BOLD}🛡️ Reliability Infrastructure${NC}"
    echo -e "${BOLD}─────────────────────────────${NC}"

    # Check if reliability scripts exist
    if [ -f "$PROJECT_ROOT/scripts/monitoring_reliability_fixes.py" ]; then
        echo -e "Reliability script:          ${GREEN}✅ Available${NC}"
    else
        echo -e "Reliability script:          ${RED}❌ Missing${NC}"
    fi

    # Check if health monitoring is set up
    if crontab -l 2>/dev/null | grep -q "monitoring_health_check.py"; then
        echo -e "Automated monitoring:        ${GREEN}✅ Configured${NC}"
    else
        echo -e "Automated monitoring:        ${YELLOW}⚠️  Not configured${NC}"
    fi

    # Check systemd service
    if systemctl --user list-unit-files 2>/dev/null | grep -q "virtuoso-monitoring-api"; then
        echo -e "Systemd service:             ${GREEN}✅ Available${NC}"
    else
        echo -e "Systemd service:             ${YELLOW}⚠️  Not configured${NC}"
    fi
}

# Monitoring API management functions
monitor_emergency_fix() {
    echo -e "${BOLD}🚨 Monitoring API Emergency Fix${NC}"
    echo -e "${BOLD}──────────────────────────────${NC}"

    cd "$PROJECT_ROOT" || exit 1

    if [ -f "scripts/monitoring_reliability_fixes.py" ]; then
        echo "Running emergency fix..."
        ./venv311/bin/python scripts/monitoring_reliability_fixes.py fix
        echo ""
        echo -e "${GREEN}✅ Emergency fix completed${NC}"
        echo "Checking status in 3 seconds..."
        sleep 3
        monitor_health_check
    else
        echo -e "${RED}❌ Reliability script not found${NC}"
        echo "Please ensure reliability infrastructure is deployed."
    fi
}

monitor_health_check() {
    echo -e "${BOLD}🔍 Monitoring API Health Check${NC}"
    echo -e "${BOLD}─────────────────────────────${NC}"

    cd "$PROJECT_ROOT" || exit 1

    if [ -f "scripts/monitoring_reliability_fixes.py" ]; then
        ./venv311/bin/python scripts/monitoring_reliability_fixes.py health
    else
        echo -e "${RED}❌ Reliability script not found${NC}"
    fi
}

monitor_restart() {
    echo -e "${BOLD}🔄 Restarting Monitoring API${NC}"
    echo -e "${BOLD}───────────────────────────${NC}"

    cd "$PROJECT_ROOT" || exit 1

    if [ -f "scripts/monitoring_reliability_fixes.py" ]; then
        ./venv311/bin/python scripts/monitoring_reliability_fixes.py restart
        echo ""
        echo -e "${GREEN}✅ Restart completed${NC}"
    else
        echo -e "${RED}❌ Reliability script not found${NC}"
    fi
}

# Add new menu options for reliability features
show_reliability_menu() {
    echo ""
    echo -e "${BOLD}🛡️ RELIABILITY FEATURES${NC}"
    echo -e "${BOLD}──────────────────────${NC}"
    echo "  30) Monitoring API emergency fix"
    echo "  31) Monitoring API health check"
    echo "  32) Monitoring API restart"
    echo "  33) Show reliability status"
    echo "  34) View monitoring logs"
}

# Show reliability status
show_reliability_status() {
    echo -e "${BOLD}🛡️ Reliability Infrastructure Status${NC}"
    echo -e "${BOLD}────────────────────────────────────${NC}"
    echo ""

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

    echo ""
    echo -e "${BOLD}⚙️ Automation${NC}"
    echo -e "${BOLD}────────────${NC}"
    local cron_count=$(crontab -l 2>/dev/null | grep -c "monitoring")
    if [ "$cron_count" -gt 0 ]; then
        echo -e "Cron jobs configured:        ${GREEN}✅ $cron_count active${NC}"
    else
        echo -e "Cron jobs configured:        ${RED}❌ None${NC}"
    fi

    # Check systemd
    echo ""
    echo -e "${BOLD}🖥️ System Services${NC}"
    echo -e "${BOLD}──────────────────${NC}"
    if systemctl --user list-unit-files 2>/dev/null | grep -q "virtuoso-monitoring-api"; then
        echo -e "Systemd service:             ${GREEN}✅ Available${NC}"
        if systemctl --user is-active --quiet virtuoso-monitoring-api 2>/dev/null; then
            echo -e "Service status:              ${GREEN}✅ Active${NC}"
        else
            echo -e "Service status:              ${YELLOW}⚠️  Inactive${NC}"
        fi
    else
        echo -e "Systemd service:             ${YELLOW}⚠️  Not available${NC}"
    fi

    echo ""
    enhanced_monitoring_health_check
}

# View monitoring logs
view_monitoring_logs() {
    echo -e "${BOLD}📄 Monitoring API Logs${NC}"
    echo -e "${BOLD}─────────────────────${NC}"
    echo ""

    if [ -f "$PROJECT_ROOT/logs/monitoring_api.log" ]; then
        echo "Last 20 lines of monitoring API log:"
        echo ""
        tail -20 "$PROJECT_ROOT/logs/monitoring_api.log"
    else
        echo -e "${YELLOW}⚠️  No monitoring API log found${NC}"
    fi

    echo ""
    if [ -f "$PROJECT_ROOT/logs/cron_health.log" ]; then
        echo "Last 10 lines of health check log:"
        echo ""
        tail -10 "$PROJECT_ROOT/logs/cron_health.log"
    else
        echo -e "${YELLOW}⚠️  No health check log found${NC}"
    fi
}

# Export functions for use in VT script
export -f enhanced_monitoring_api_check
export -f enhanced_monitoring_health_check
export -f monitor_emergency_fix
export -f monitor_health_check
export -f monitor_restart
export -f show_reliability_menu
export -f show_reliability_status
export -f view_monitoring_logs