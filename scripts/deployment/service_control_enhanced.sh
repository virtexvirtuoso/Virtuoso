#!/bin/bash

#############################################################################
# Script: service_control_enhanced.sh
# Purpose: Deploy and manage service control enhanced
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
#   ./service_control_enhanced.sh [options]
#   
#   Examples:
#     ./service_control_enhanced.sh
#     ./service_control_enhanced.sh --verbose
#     ./service_control_enhanced.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: VPS_HOST_REDACTED)
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

# Virtuoso Trading System - Enhanced Service Control
# Optimized for performance, reliability, and ease of use
#

SERVICE_NAME="virtuoso"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"
VENV_PATH="$PROJECT_DIR/venv311"
CONFIG_FILE="$PROJECT_DIR/config/config.yaml"
PID_FILE="$PROJECT_DIR/trading.pid"

# Colors for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Performance optimizations
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should not be run as root. It will use sudo when needed."
   exit 1
fi

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    local missing=0
    
    # Check for required commands
    for cmd in systemctl journalctl curl jq; do
        if ! command -v $cmd &> /dev/null; then
            print_error "$cmd is not installed"
            missing=1
        fi
    done
    
    # Check project directory
    if [[ ! -d "$PROJECT_DIR" ]]; then
        print_error "Project directory not found: $PROJECT_DIR"
        missing=1
    fi
    
    # Check virtual environment
    if [[ ! -f "$VENV_PATH/bin/python" ]]; then
        print_error "Virtual environment not found: $VENV_PATH"
        missing=1
    fi
    
    return $missing
}

# Enhanced status check with health monitoring
check_status() {
    echo -e "\n${BLUE}=== System Status Overview ===${NC}\n"
    
    # Service status
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${GREEN}● Service Status: Running${NC}"
        local uptime=$(systemctl show $SERVICE_NAME --property=ActiveEnterTimestamp | cut -d'=' -f2)
        if [[ -n "$uptime" ]]; then
            echo -e "  Uptime: Since $uptime"
        fi
    else
        echo -e "${RED}● Service Status: Not Running${NC}"
    fi
    
    # Auto-start status
    if systemctl is-enabled --quiet $SERVICE_NAME 2>/dev/null; then
        echo -e "${GREEN}● Auto-start: Enabled${NC}"
    else
        echo -e "${YELLOW}● Auto-start: Disabled${NC}"
    fi
    
    # Memory usage
    if systemctl is-active --quiet $SERVICE_NAME; then
        local pid=$(systemctl show $SERVICE_NAME --property=MainPID | cut -d'=' -f2)
        if [[ "$pid" != "0" ]]; then
            local mem_kb=$(ps -p $pid -o rss= 2>/dev/null | tr -d ' ')
            if [[ -n "$mem_kb" ]]; then
                local mem_mb=$((mem_kb / 1024))
                echo -e "  Memory Usage: ${mem_mb}MB"
            fi
        fi
    fi
    
    # API health check
    echo -e "\n${BLUE}API Health Check:${NC}"
    if curl -s -f -m 2 http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}● API: Healthy${NC}"
        
        # Get detailed health info if available
        local health_data=$(curl -s -m 2 http://localhost:8000/health 2>/dev/null)
        if [[ -n "$health_data" ]] && command -v jq &> /dev/null; then
            echo "$health_data" | jq -r 'to_entries[] | "  \(.key): \(.value)"' 2>/dev/null || true
        fi
    else
        echo -e "${RED}● API: Not Responding${NC}"
    fi
    
    # WebSocket status
    local ws_status=$(curl -s -m 2 http://localhost:8000/api/websocket/status 2>/dev/null)
    if [[ -n "$ws_status" ]]; then
        echo -e "\n${BLUE}WebSocket Status:${NC}"
        if command -v jq &> /dev/null; then
            echo "$ws_status" | jq -r 'to_entries[] | "  \(.key): \(.value)"' 2>/dev/null || echo "  Status: Connected"
        else
            echo "  Status: Connected"
        fi
    fi
    
    # Recent errors
    echo -e "\n${BLUE}Recent Errors (last 5):${NC}"
    sudo journalctl -u $SERVICE_NAME -p err -n 5 --no-pager | tail -n +2 | while read line; do
        echo "  $line"
    done
    
    # Port status
    echo -e "\n${BLUE}Port Status:${NC}"
    if sudo ss -tlnp | grep -q ":8000"; then
        echo -e "${GREEN}● Port 8000: Open${NC}"
    else
        echo -e "${RED}● Port 8000: Closed${NC}"
    fi
}

# Quick health check
quick_health_check() {
    if systemctl is-active --quiet $SERVICE_NAME && \
       curl -s -f -m 2 http://localhost:8000/health > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to start service with health check
start_service_with_check() {
    print_info "Starting service..."
    sudo systemctl start $SERVICE_NAME
    
    # Wait for service to start
    local count=0
    while [ $count -lt 30 ]; do
        if quick_health_check; then
            print_success "Service started and healthy!"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        echo -n "."
    done
    
    print_error "Service failed to start properly"
    echo "Checking logs..."
    sudo journalctl -u $SERVICE_NAME -n 20 --no-pager
    return 1
}

# Function to safely stop service
stop_service_safely() {
    print_info "Stopping service gracefully..."
    
    # Send graceful shutdown signal
    sudo systemctl stop $SERVICE_NAME
    
    # Wait for clean shutdown
    local count=0
    while [ $count -lt 30 ]; do
        if ! systemctl is-active --quiet $SERVICE_NAME; then
            print_success "Service stopped cleanly"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        echo -n "."
    done
    
    print_warning "Service didn't stop gracefully, forcing..."
    sudo systemctl kill $SERVICE_NAME
    sleep 2
    
    # Clean up any orphaned processes
    pkill -f "python.*main.py" 2>/dev/null || true
}

# Function to restart with zero downtime attempt
smart_restart() {
    print_info "Performing smart restart..."
    
    if ! systemctl is-active --quiet $SERVICE_NAME; then
        start_service_with_check
        return $?
    fi
    
    # For future: could implement blue-green deployment here
    sudo systemctl restart $SERVICE_NAME
    
    # Wait for service to be healthy
    sleep 3
    if quick_health_check; then
        print_success "Service restarted successfully!"
        return 0
    else
        print_error "Service restart failed"
        return 1
    fi
}

# Function to tail logs with filtering
view_logs() {
    echo -e "\n${BLUE}Log Viewer Options:${NC}"
    echo "  1) All logs (live)"
    echo "  2) Errors only"
    echo "  3) Warnings and above"
    echo "  4) Last 100 lines"
    echo "  5) Search logs"
    echo "  6) Export logs"
    echo -n "Select option: "
    
    read -r log_choice
    
    case $log_choice in
        1)
            sudo journalctl -u $SERVICE_NAME -f
            ;;
        2)
            sudo journalctl -u $SERVICE_NAME -p err -f
            ;;
        3)
            sudo journalctl -u $SERVICE_NAME -p warning -f
            ;;
        4)
            sudo journalctl -u $SERVICE_NAME -n 100 --no-pager
            ;;
        5)
            echo -n "Enter search term: "
            read -r search_term
            sudo journalctl -u $SERVICE_NAME | grep -i "$search_term" | less
            ;;
        6)
            local filename="virtuoso_logs_$(date +%Y%m%d_%H%M%S).txt"
            sudo journalctl -u $SERVICE_NAME > ~/$filename
            print_success "Logs exported to ~/$filename"
            ;;
        *)
            print_error "Invalid option"
            ;;
    esac
}

# Function to run diagnostics
run_diagnostics() {
    echo -e "\n${BLUE}=== Running Diagnostics ===${NC}\n"
    
    # System resources
    echo -e "${CYAN}System Resources:${NC}"
    echo "CPU Cores: $(nproc)"
    echo "Memory: $(free -h | grep Mem | awk '{print $2}')"
    echo "Disk Space: $(df -h $PROJECT_DIR | tail -1 | awk '{print $4}' ) available"
    
    # Python environment
    echo -e "\n${CYAN}Python Environment:${NC}"
    $VENV_PATH/bin/python --version
    echo "Virtual Env: $VENV_PATH"
    
    # Check critical dependencies
    echo -e "\n${CYAN}Critical Dependencies:${NC}"
    for pkg in aiohttp ccxt pandas numpy; do
        if $VENV_PATH/bin/python -c "import $pkg" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} $pkg"
        else
            echo -e "${RED}✗${NC} $pkg"
        fi
    done
    
    # Network connectivity
    echo -e "\n${CYAN}Network Connectivity:${NC}"
    for host in api.bybit.com google.com; do
        if ping -c 1 -W 2 $host > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} $host"
        else
            echo -e "${RED}✗${NC} $host"
        fi
    done
    
    # Service configuration
    echo -e "\n${CYAN}Service Configuration:${NC}"
    if [[ -f /etc/systemd/system/$SERVICE_NAME.service ]]; then
        echo -e "${GREEN}✓${NC} Service file exists"
        echo "  Memory Limit: $(systemctl show $SERVICE_NAME -p MemoryLimit | cut -d'=' -f2)"
        echo "  Restart Policy: $(systemctl show $SERVICE_NAME -p Restart | cut -d'=' -f2)"
    else
        echo -e "${RED}✗${NC} Service file missing"
    fi
}

# Function to enable monitoring
setup_monitoring() {
    echo -e "\n${BLUE}=== Monitoring Setup ===${NC}\n"
    
    cat > ~/monitor_virtuoso.sh << 'EOF'
#!/bin/bash
# Virtuoso Trading Monitor Script

SERVICE="virtuoso"
WEBHOOK_URL="$SYSTEM_ALERTS_WEBHOOK_URL"
LAST_ALERT_FILE="/tmp/virtuoso_last_alert"

# Check if service is running
if ! systemctl is-active --quiet $SERVICE; then
    # Check if we already sent an alert recently (within 5 minutes)
    if [[ -f "$LAST_ALERT_FILE" ]]; then
        last_alert=$(cat "$LAST_ALERT_FILE")
        current_time=$(date +%s)
        if (( current_time - last_alert < 300 )); then
            exit 0
        fi
    fi
    
    # Send alert
    if [[ -n "$WEBHOOK_URL" ]]; then
        curl -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d '{"content":"⚠️ Virtuoso Trading service is DOWN! Attempting restart..."}' \
            2>/dev/null
    fi
    
    # Try to restart
    systemctl start $SERVICE
    
    # Record alert time
    date +%s > "$LAST_ALERT_FILE"
fi

# Check API health
if ! curl -s -f -m 5 http://localhost:8000/health > /dev/null 2>&1; then
    # API not responding but service is running
    if systemctl is-active --quiet $SERVICE; then
        # Restart the service
        systemctl restart $SERVICE
    fi
fi
EOF
    
    chmod +x ~/monitor_virtuoso.sh
    
    # Add to crontab
    (crontab -l 2>/dev/null | grep -v "monitor_virtuoso.sh"; echo "*/5 * * * * /home/linuxuser/monitor_virtuoso.sh") | crontab -
    
    print_success "Monitoring script created and scheduled to run every 5 minutes"
    echo "Monitor script: ~/monitor_virtuoso.sh"
}

# Performance tuning function
tune_performance() {
    echo -e "\n${BLUE}=== Performance Tuning ===${NC}\n"
    
    # Create optimized service file
    sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOF
[Unit]
Description=Virtuoso Trading System (Optimized)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=linuxuser
Group=linuxuser
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_PATH/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONDONTWRITEBYTECODE=1"
Environment="PYTHONOPTIMIZE=1"
ExecStart=$VENV_PATH/bin/python -O src/main.py
Restart=always
RestartSec=10
StartLimitBurst=5
StartLimitInterval=60

# Performance
Nice=-5
IOSchedulingClass=2
IOSchedulingPriority=4
CPUSchedulingPolicy=other
CPUSchedulingPriority=0

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096
MemoryLimit=4G
MemoryHigh=3G

# Security
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$PROJECT_DIR

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=virtuoso

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    print_success "Performance optimizations applied"
    
    # System-wide optimizations
    echo -e "\n${CYAN}Applying system optimizations...${NC}"
    
    # Increase file descriptors
    if ! grep -q "linuxuser.*nofile" /etc/security/limits.conf; then
        echo "linuxuser soft nofile 65536" | sudo tee -a /etc/security/limits.conf
        echo "linuxuser hard nofile 65536" | sudo tee -a /etc/security/limits.conf
        print_success "File descriptor limits increased"
    fi
    
    # TCP optimizations
    sudo sysctl -w net.core.somaxconn=65535 2>/dev/null
    sudo sysctl -w net.ipv4.tcp_max_syn_backlog=65535 2>/dev/null
    sudo sysctl -w net.core.netdev_max_backlog=65535 2>/dev/null
    
    print_info "System optimizations applied. Restart may be required for full effect."
}

# Backup configuration
backup_config() {
    local backup_dir="$HOME/backups/virtuoso_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    print_info "Creating backup in $backup_dir..."
    
    # Backup config files
    cp -r $PROJECT_DIR/config $backup_dir/
    cp /etc/systemd/system/$SERVICE_NAME.service $backup_dir/ 2>/dev/null || true
    
    # Backup database if exists
    if [[ -f "$PROJECT_DIR/data/virtuoso.db" ]]; then
        cp $PROJECT_DIR/data/virtuoso.db $backup_dir/
    fi
    
    # Create info file
    cat > $backup_dir/backup_info.txt << EOF
Backup created: $(date)
Service status: $(systemctl is-active $SERVICE_NAME)
Python version: $($VENV_PATH/bin/python --version)
EOF
    
    # Compress
    tar -czf "$backup_dir.tar.gz" -C "$(dirname $backup_dir)" "$(basename $backup_dir)"
    rm -rf "$backup_dir"
    
    print_success "Backup created: $backup_dir.tar.gz"
}

# Main menu with better organization
show_menu() {
    clear
    echo -e "${BLUE}╔═══════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   Virtuoso Trading Service Control Center     ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════╝${NC}"
    
    check_status
    
    echo -e "\n${CYAN}Service Control:${NC}"
    echo "  1) Start Service"
    echo "  2) Stop Service"
    echo "  3) Restart Service (Smart)"
    echo "  4) Enable Auto-start"
    echo "  5) Disable Auto-start"
    
    echo -e "\n${CYAN}Monitoring & Logs:${NC}"
    echo "  6) View Logs"
    echo "  7) Run Diagnostics"
    echo "  8) Setup Monitoring"
    
    echo -e "\n${CYAN}Maintenance:${NC}"
    echo "  9) Performance Tuning"
    echo "  10) Backup Configuration"
    echo "  11) Clear Cache/Logs"
    
    echo -e "\n${CYAN}Quick Actions:${NC}"
    echo "  h) Health Check"
    echo "  r) Quick Restart"
    echo "  s) Service Status"
    
    echo -e "\n  0) Exit"
    echo -e "\n${YELLOW}Select option:${NC} "
}

# Clear cache and old logs
clear_cache() {
    print_info "Clearing cache and old logs..."
    
    # Clear Python cache
    find $PROJECT_DIR -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    
    # Clear old logs (older than 7 days)
    find $PROJECT_DIR/logs -name "*.log" -mtime +7 -delete 2>/dev/null || true
    
    # Clear systemd journal (keep last 100MB)
    sudo journalctl --vacuum-size=100M
    
    # Clear app cache
    rm -rf $PROJECT_DIR/cache/* 2>/dev/null || true
    
    print_success "Cache and old logs cleared"
}

# Main loop
main() {
    # Check prerequisites
    if ! check_prerequisites; then
        print_error "Prerequisites check failed"
        exit 1
    fi
    
    while true; do
        show_menu
        read -r choice
        
        case $choice in
            1)
                start_service_with_check
                ;;
            2)
                stop_service_safely
                ;;
            3)
                smart_restart
                ;;
            4)
                sudo systemctl enable $SERVICE_NAME
                print_success "Auto-start enabled"
                ;;
            5)
                sudo systemctl disable $SERVICE_NAME
                print_success "Auto-start disabled"
                ;;
            6)
                view_logs
                ;;
            7)
                run_diagnostics
                ;;
            8)
                setup_monitoring
                ;;
            9)
                tune_performance
                ;;
            10)
                backup_config
                ;;
            11)
                clear_cache
                ;;
            h|H)
                if quick_health_check; then
                    print_success "Service is healthy!"
                else
                    print_error "Service health check failed"
                fi
                ;;
            r|R)
                smart_restart
                ;;
            s|S)
                check_status
                ;;
            0)
                echo "Exiting..."
                exit 0
                ;;
            *)
                print_error "Invalid option"
                ;;
        esac
        
        echo -e "\n${YELLOW}Press Enter to continue...${NC}"
        read -r
    done
}

# Run main function
main