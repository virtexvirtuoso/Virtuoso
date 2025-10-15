#!/bin/bash
# Update VT Control Panel with Reliability Features
# This script patches the existing VT control panel to include reliability features

set -e

VT_SCRIPT="/home/linuxuser/bin/vt"
BACKUP_SCRIPT="/home/linuxuser/bin/vt.backup.$(date +%Y%m%d_%H%M%S)"
PROJECT_ROOT="/home/linuxuser/trading/Virtuoso_ccxt"

echo "Updating VT Control Panel with Reliability Features..."
echo "======================================================="

# Create backup
echo "Creating backup of existing VT script..."
cp "$VT_SCRIPT" "$BACKUP_SCRIPT"
echo "✅ Backup created: $BACKUP_SCRIPT"

# Source our enhancements
echo "Sourcing reliability enhancements..."
source "$PROJECT_ROOT/scripts/vt_reliability_enhancements.sh"

# 1. Update monitoring API detection in status display
echo "Updating monitoring API detection..."

# Replace the existing monitoring API check with enhanced version
sed -i '/# Monitoring API Service/,/fi/ {
    /# Monitoring API Service/a\
    # Enhanced monitoring API detection with port fallback\
    if monitor_pid=$(pgrep -f "monitoring_api.py" 2>/dev/null | head -1); then\
        # Try to detect which port it'\''s using\
        monitor_port=""\
        for port in 8001 8003 8004 8005; do\
            if curl -s -f -m 2 "http://localhost:$port/health" > /dev/null 2>&1; then\
                monitor_port="$port"\
                break\
            fi\
        done\
        \
        if [ -n "$monitor_port" ]; then\
            monitor_text="● RUNNING (:$monitor_port, PID: $monitor_pid)"\
            printf "${BOLD}${CYAN}║${NC}  Monitoring API:      ${BOLD}${CYAN}│${NC} ${GREEN}%38s${NC}${BOLD}${CYAN}║${NC}\\n" "$monitor_text"\
        else\
            monitor_text="● RUNNING (PID: $monitor_pid, Port: Unknown)"\
            printf "${BOLD}${CYAN}║${NC}  Monitoring API:      ${BOLD}${CYAN}│${NC} ${YELLOW}%38s${NC}${BOLD}${CYAN}║${NC}\\n" "$monitor_text"\
        fi\
    else\
        monitor_text="○ STOPPED"\
        printf "${BOLD}${CYAN}║${NC}  Monitoring API:      ${BOLD}${CYAN}│${NC} ${RED}%38s${NC}${BOLD}${CYAN}║${NC}\\n" "$monitor_text"\
    fi\
    #ENHANCED_MONITORING_BLOCK_END
    /# Monitoring API Service/,/fi/d
}' "$VT_SCRIPT"

# 2. Add new menu options
echo "Adding reliability menu options..."

# Find the line with option 29 and add our new options after it
sed -i '/29) echo "Configure log level"/a\
\
  echo ""\
  echo -e "${BOLD}🛡️ RELIABILITY FEATURES${NC}"\
  echo -e "${BOLD}──────────────────────${NC}"\
  echo "  30) Monitoring API emergency fix"\
  echo "  31) Monitoring API health check"\
  echo "  32) Monitoring API restart"\
  echo "  33) Show reliability status"\
  echo "  34) View monitoring logs"' "$VT_SCRIPT"

# 3. Add case handlers for new options
echo "Adding case handlers for reliability options..."

# Find the case statement and add our new cases before the default case
sed -i '/*)$/i\
        30)\
            echo -e "${BOLD}🚨 Monitoring API Emergency Fix${NC}"\
            echo -e "${BOLD}──────────────────────────────${NC}"\
            cd "$PROJECT_ROOT" || exit 1\
            if [ -f "scripts/monitoring_reliability_fixes.py" ]; then\
                echo "Running emergency fix..."\
                ./venv311/bin/python scripts/monitoring_reliability_fixes.py fix\
                echo ""\
                echo -e "${GREEN}✅ Emergency fix completed${NC}"\
                echo "Press Enter to continue..."\
                read\
            else\
                echo -e "${RED}❌ Reliability script not found${NC}"\
                echo "Press Enter to continue..."\
                read\
            fi\
            ;;\
        31)\
            echo -e "${BOLD}🔍 Monitoring API Health Check${NC}"\
            echo -e "${BOLD}─────────────────────────────${NC}"\
            cd "$PROJECT_ROOT" || exit 1\
            if [ -f "scripts/monitoring_reliability_fixes.py" ]; then\
                ./venv311/bin/python scripts/monitoring_reliability_fixes.py health\
                echo "Press Enter to continue..."\
                read\
            else\
                echo -e "${RED}❌ Reliability script not found${NC}"\
                echo "Press Enter to continue..."\
                read\
            fi\
            ;;\
        32)\
            echo -e "${BOLD}🔄 Restarting Monitoring API${NC}"\
            echo -e "${BOLD}───────────────────────────${NC}"\
            cd "$PROJECT_ROOT" || exit 1\
            if [ -f "scripts/monitoring_reliability_fixes.py" ]; then\
                ./venv311/bin/python scripts/monitoring_reliability_fixes.py restart\
                echo ""\
                echo -e "${GREEN}✅ Restart completed${NC}"\
                echo "Press Enter to continue..."\
                read\
            else\
                echo -e "${RED}❌ Reliability script not found${NC}"\
                echo "Press Enter to continue..."\
                read\
            fi\
            ;;\
        33)\
            echo -e "${BOLD}🛡️ Reliability Infrastructure Status${NC}"\
            echo -e "${BOLD}────────────────────────────────────${NC}"\
            echo ""\
            # Check scripts\
            echo -e "${BOLD}📁 Scripts${NC}"\
            echo -e "${BOLD}─────────${NC}"\
            if [ -f "$PROJECT_ROOT/scripts/monitoring_reliability_fixes.py" ]; then\
                echo -e "Reliability fixes:           ${GREEN}✅ Available${NC}"\
            else\
                echo -e "Reliability fixes:           ${RED}❌ Missing${NC}"\
            fi\
            if [ -f "$PROJECT_ROOT/scripts/monitoring_health_check.py" ]; then\
                echo -e "Health monitoring:           ${GREEN}✅ Available${NC}"\
            else\
                echo -e "Health monitoring:           ${RED}❌ Missing${NC}"\
            fi\
            echo ""\
            echo -e "${BOLD}⚙️ Automation${NC}"\
            echo -e "${BOLD}────────────${NC}"\
            cron_count=$(crontab -l 2>/dev/null | grep -c "monitoring" || echo "0")\
            if [ "$cron_count" -gt 0 ]; then\
                echo -e "Cron jobs configured:        ${GREEN}✅ $cron_count active${NC}"\
            else\
                echo -e "Cron jobs configured:        ${RED}❌ None${NC}"\
            fi\
            echo "Press Enter to continue..."\
            read\
            ;;\
        34)\
            echo -e "${BOLD}📄 Monitoring API Logs${NC}"\
            echo -e "${BOLD}─────────────────────${NC}"\
            echo ""\
            if [ -f "$PROJECT_ROOT/logs/monitoring_api.log" ]; then\
                echo "Last 20 lines of monitoring API log:"\
                echo ""\
                tail -20 "$PROJECT_ROOT/logs/monitoring_api.log"\
            else\
                echo -e "${YELLOW}⚠️  No monitoring API log found${NC}"\
            fi\
            echo ""\
            if [ -f "$PROJECT_ROOT/logs/cron_health.log" ]; then\
                echo "Last 10 lines of health check log:"\
                echo ""\
                tail -10 "$PROJECT_ROOT/logs/cron_health.log"\
            else\
                echo -e "${YELLOW}⚠️  No health check log found${NC}"\
            fi\
            echo "Press Enter to continue..."\
            read\
            ;;' "$VT_SCRIPT"

# 4. Enhance the health check function
echo "Enhancing health check function..."

# Add monitoring API health check to existing health function
sed -i '/# Mobile endpoint on port 8003/a\
\
        # Enhanced Monitoring API Health Check\
        echo ""\
        echo -e "${BOLD}🔧 Monitoring API Health Check${NC}"\
        echo -e "${BOLD}────────────────────────────${NC}"\
        found_port=""\
        for port in 8001 8003 8004 8005; do\
            http_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/health" 2>/dev/null)\
            if [ "$http_code" = "200" ]; then\
                echo -e "Monitoring API (:$port):     ${GREEN}✅ OK (HTTP 200)${NC}"\
                found_port="$port"\
                break\
            fi\
        done\
        if [ -z "$found_port" ]; then\
            echo -e "Monitoring API:              ${RED}❌ Not responding on any port${NC}"\
            echo -e "                             ${YELLOW}💡 Try: vt 30 (emergency fix)${NC}"\
        fi' "$VT_SCRIPT"

# 5. Add reliability commands to help text
echo "Updating help text..."

sed -i '/vt health.*Comprehensive health check/a\
  vt monitor-fix     Emergency monitoring API fix\
  vt monitor-health  Check monitoring API health\
  vt monitor-restart Restart monitoring API' "$VT_SCRIPT"

# 6. Add command-line argument handlers
echo "Adding command-line argument handlers..."

sed -i '/health)/a\
    monitor-fix)\
        cd "$PROJECT_ROOT" || exit 1\
        if [ -f "scripts/monitoring_reliability_fixes.py" ]; then\
            echo -e "${BOLD}🚨 Monitoring API Emergency Fix${NC}"\
            ./venv311/bin/python scripts/monitoring_reliability_fixes.py fix\
        else\
            echo -e "${RED}❌ Reliability script not found${NC}"\
        fi\
        ;;\
    monitor-health)\
        cd "$PROJECT_ROOT" || exit 1\
        if [ -f "scripts/monitoring_reliability_fixes.py" ]; then\
            ./venv311/bin/python scripts/monitoring_reliability_fixes.py health\
        else\
            echo -e "${RED}❌ Reliability script not found${NC}"\
        fi\
        ;;\
    monitor-restart)\
        cd "$PROJECT_ROOT" || exit 1\
        if [ -f "scripts/monitoring_reliability_fixes.py" ]; then\
            echo -e "${BOLD}🔄 Restarting Monitoring API${NC}"\
            ./venv311/bin/python scripts/monitoring_reliability_fixes.py restart\
        else\
            echo -e "${RED}❌ Reliability script not found${NC}"\
        fi\
        ;;' "$VT_SCRIPT"

echo "✅ VT Control Panel updated successfully!"
echo ""
echo "New features added:"
echo "  • Enhanced monitoring API detection with port fallback"
echo "  • Reliability menu options (30-34)"
echo "  • Command-line shortcuts: monitor-fix, monitor-health, monitor-restart"
echo "  • Enhanced health checks"
echo "  • Monitoring log viewing"
echo ""
echo "Available commands:"
echo "  vt 30             - Emergency monitoring API fix"
echo "  vt monitor-fix    - Same as above"
echo "  vt 31             - Monitoring API health check"
echo "  vt monitor-health - Same as above"
echo "  vt 32             - Restart monitoring API"
echo "  vt monitor-restart- Same as above"
echo "  vt 33             - Show reliability status"
echo "  vt 34             - View monitoring logs"
echo ""
echo "Backup created at: $BACKUP_SCRIPT"